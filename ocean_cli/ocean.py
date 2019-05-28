import click
import json
import logging
import os
import re
import time

from squid_py import ConfigProvider
from squid_py.accounts.account import Account
from squid_py.agreements.service_agreement import ServiceAgreement
from squid_py.agreements.service_factory import ServiceTypes, ServiceDescriptor
from squid_py.config import Config
from squid_py.did import did_to_id_bytes, id_to_did, did_to_id, DID, \
    is_did_valid
from squid_py.keeper import Keeper, Token, DIDRegistry
from squid_py.keeper.agreements.agreement_manager import AgreementStoreManager
from squid_py.keeper.web3_provider import Web3Provider
from squid_py.ocean.ocean import Ocean
from squid_py.ocean.ocean_conditions import OceanConditions

from squid_py.keeper.didregistry import DIDRegisterValues


def get_default_account(config):
    account_address = config.get('keeper-contracts', 'account.address')
    account_password = config.get('keeper-contracts', 'account.password')
    account = Account(
        Web3Provider.get_web3().toChecksumAddress(account_address),
        account_password)
    return account


@click.pass_context
def get_service_agreement_from_did(ctx, did):
    ocean = ctx.obj['ocean']
    ddo = ocean.assets.resolve(did)
    service = ddo.get_service(service_type=ServiceTypes.ASSET_ACCESS)
    return ServiceAgreement.from_service_dict(service.as_dictionary())


@click.pass_context
def get_service_agreement_from_id(ctx, agreement_id):
    ocean = ctx.obj['ocean']
    agreement = ocean.agreements.get(agreement_id)
    did = id_to_did(agreement.did)
    return get_service_agreement_from_did(did)


@click.pass_context
def format_dict(ctx, response_dict):
    response = json.dumps(response_dict, indent=2, sort_keys=True)
    if ctx.obj['json']:
        pass
    else:
        response = re.sub(r'\n\s*\n', '\n',
                          re.sub(r'[\",{}\[\]]', '', response))
    return response


def echo(response):
    click.echo(format_dict(response))


@click.group()
@click.option('--config-file', '-c',
              type=click.Path(),
              default='./config.ini', show_default=True)
@click.option('--as-json', '-j', is_flag=True)
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def ocean(ctx, config_file, as_json, verbose):
    """
    Simple CLI for registering and consuming assets in Ocean Protocol

    \b
                                               O           ,
                                                       .</       ,
  ____                      _______   ____          ,aT&/t    ,</
 / __ \_______ ___ ____    / ___/ /  /  _/     o   o:\:::::95/b/
/ /_/ / __/ -_) _ `/ _ \  / /__/ /___/ /        ' >::7:::::U2/)(
\____/\__/\__/\_,_/_//_/  \___/____/___/           '*qf/P    '</
                                                     '<)       '
    """
    if not verbose:
        logging.getLogger().setLevel(logging.ERROR)

    ocean = Ocean(Config(filename=config_file))
    account = get_default_account(ConfigProvider.get_config())
    ctx.obj = {
        'account': account,
        'ocean': ocean,
        'json': as_json
    }


@ocean.group()
def accounts():
    """
    List active accounts and balance
    """
    pass


@accounts.command('get')
@click.pass_context
def accounts_get(ctx):
    account = ctx.obj['account']
    echo({
        'address': account.address
    })


@accounts.command('balance')
@click.option('-a', '--address')
@click.pass_context
def accounts_balance(ctx, address):
    balance_account = ctx.obj['account']
    if address:
        balance_account = Account(address, address)
    balance = ctx.obj['ocean'].accounts.balance(balance_account)
    echo({
        'address': balance_account.address,
        'eth': balance.eth,
        'ocean': balance.ocn,
    })


@accounts.command('list')
@click.pass_context
def accounts_list(ctx):
    echo([
        acc.address for acc in ctx.obj['ocean'].accounts.list()
    ])


@ocean.group()
def tokens():
    """
    Transfer and request OCEAN token
    """
    pass


@tokens.command('request')
@click.argument('amount')
@click.pass_context
def token_request(ctx, amount):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    result = ocean.tokens.request(account, int(amount))
    balance = Token.get_instance()\
        .get_token_balance(account.address)
    echo({
        'address': account.address,
        'balance': balance,
        'result': result
    })


@tokens.command('transfer')
@click.argument('amount')
@click.argument('to')
@click.pass_context
def token_transfer(ctx, amount, to):
    """
    Transfer OCEAN token to address
    """
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    ocean.tokens.transfer(to, int(amount), account)
    echo({
        'from': {
            'address': account.address,
            'balance': Token.get_instance().get_token_balance(account.address),
        },
        'to': {
            'address': to,
            'balance': Token.get_instance().get_token_balance(to),
        }
    })


@ocean.group()
def assets():
    """
    Create, discover and consume assets
    """
    pass


@assets.command('create')
@click.argument('metadata', type=click.Path())
@click.option('--secret-store', '-s', is_flag=True)
@click.pass_context
def assets_create(ctx, metadata, secret_store):
    """
    Publish an asset from metadata
    """
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    if not isinstance(metadata, dict):
        # Assume it is a path to metadata json file
        metadata = json.load(open(metadata, 'r'))
    service_descriptors = [
        ServiceDescriptor.access_service_descriptor(
            10,
            'http://purchase',
            'http://localhost:8888',
            3600,
            ocean._keeper.escrow_access_secretstore_template.address
        )
    ]
    ddo = ocean.assets.create(
        metadata,
        account,
        service_descriptors=service_descriptors,
        providers=[account.address],
        use_secret_store=secret_store
    )
    did_registry = Keeper.get_instance().did_registry
    provider = did_registry.to_checksum_address(account.address)
    time.sleep(20)
    try:
        did_registry.add_provider(ddo.asset_id, provider, account)
    except ValueError as e:
        print('ValueError', e)
    echo([ddo.did])


@assets.command('add-providers')
@click.argument('did')
@click.argument('provider', default=None)
@click.pass_context
def assets_create(ctx, did, provider):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    if provider == 'me':
        provider = account.address
    did_registry = Keeper.get_instance().did_registry
    response = did_registry.add_provider(did_to_id(did), provider, account)
    echo(f"{response}")


@assets.command('get-providers')
@click.argument('did')
@click.pass_context
def assets_create(ctx, did):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    did_registry = Keeper.get_instance().did_registry
    response = did_registry.get_did_providers(did_to_id(did))
    echo(f"{response}")


@assets.command('get-owner')
@click.argument('did')
@click.pass_context
def assets_create(ctx, did):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    did_registry = Keeper.get_instance().did_registry
    response = did_registry.get_did_owner(did_to_id(did))
    echo(f"{response}")


@assets.command('get')
@click.argument('did')
@click.pass_context
def assets_create(ctx, did):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    did_registry = Keeper.get_instance().did_registry
    register_values = did_registry.contract_concise.getDIDRegister(did_to_id(did))
    response = []
    if register_values and len(register_values) == 5:
        response = DIDRegisterValues(*register_values)._asdict()
        response['last_checksum'] = Web3Provider.get_web3().toHex(response['last_checksum'])
    echo(response)


@assets.command('search')
@click.argument('text')
@click.pass_context
def assets_search(ctx, text):
    """
    Search assets by keyword
    """
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    result = ocean.assets.search(text, sort=None, offset=100, page=1)
    echo([ddo.did for ddo in result])


def _assets_order(ctx, did):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    sa = get_service_agreement_from_did(did)
    agreement_id = ocean.assets.order(did, sa.service_definition_id, account, True)
    _conditions_lock_reward(ctx, agreement_id)

    return [agreement_id]


@assets.command('order')
@click.argument('did')
@click.pass_context
def assets_order(ctx, did):
    """
    Order asset: create Service Agreement and lock reward
    """
    echo(_assets_order(ctx, did))


def _assets_consume(ctx, agreement_id, service_id):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    agreement = ocean.agreements.get(agreement_id)
    did = id_to_did(agreement.did)
    path = ocean.assets.consume(agreement_id, did, service_id, account,
                                ConfigProvider.get_config().downloads_path)
    files = os.listdir(path)

    return {
        'agreement': agreement_id,
        'path': path.split('tuna/')[-1] + '/',
        'files': files
    }


@assets.command('consume')
@click.argument('did')
@click.option('--wait', '-w', default=30, show_default=True)
@click.pass_context
def assets_consume(ctx, did, wait):
    """
    Consume asset: create Service Agreement, lock reward, [wait], decrypt & download
    """
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    response = _assets_order(ctx, did)
    i = 0
    while ocean.agreements.is_access_granted(
            response['agreement'], did,
            account.address) is not True and i < wait:
        time.sleep(1)
        i += 1
    echo(_assets_consume(ctx, response['agreement'], response['service']))


def _assets_decrypt(ctx, did):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    ddo = ocean.assets.resolve(did)
    encrypted_files = ddo.metadata['base']['encryptedFiles']
    encrypted_files = (
        encrypted_files if isinstance(encrypted_files, str)
        else encrypted_files[0]
    )
    sa = ServiceAgreement.from_service_dict(
        ddo.get_service(service_type=ServiceTypes.ASSET_ACCESS).as_dictionary()
    )
    consume_url = sa.service_endpoint
    if not consume_url:
        raise AssertionError(
            'Consume asset failed, service definition is missing the "serviceEndpoint".')

    secret_store = ocean.assets._get_secret_store(account)
    if ddo.get_service('Authorization'):
        secret_store_service = ddo.get_service(
            service_type=ServiceTypes.AUTHORIZATION)
        secret_store_url = secret_store_service.endpoints.service
        secret_store.set_secret_store_url(secret_store_url)

    # decrypt the contentUrls
    decrypted_content_urls = json.loads(
        secret_store.decrypt_document(did_to_id(did), encrypted_files)
    )

    if isinstance(decrypted_content_urls, str):
        decrypted_content_urls = [decrypted_content_urls]
    return decrypted_content_urls


@assets.command('decrypt')
@click.argument('did')
@click.pass_context
def assets_decrypt(ctx, did):
    """
    Decrypt asset service
    """
    echo(_assets_decrypt(ctx, did))


@assets.command('consume-agreement')
@click.argument('agreement_id')
@click.argument('service_id', default=1)
@click.pass_context
def assets_consume_agreement(ctx, agreement_id, service_id):
    """
    Consume agreement: decrypt and download
    """
    echo(_assets_consume(ctx, agreement_id, service_id))


@assets.command('resolve')
@click.argument('did')
@click.pass_context
def assets_resolve(ctx, did):
    """
    Resolve DID to DID Document
    """
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    asset = ocean.assets.resolve(did)
    echo(asset.as_dictionary())


@click.pass_context
def _assets_list(ctx, address):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']

    did_registry = DIDRegistry.get_instance()
    did_registry_ids = did_registry.contract_concise.getDIDRegisterIds()
    asset_list = [
         id_to_did(Web3Provider.get_web3().toHex(did)[2:])
         for did in did_registry_ids
    ]
    if address:
        if address == 'me':
            address = account.address
        return [
            asset
            for asset in asset_list
            if ocean.assets
                   .resolve(asset)
                   .as_dictionary()['publicKey'][0]['owner'] == address
        ]
    return asset_list


@assets.command('list')
@click.option('-a', '--address')
def assets_list(address):
    """
    List assets on-chain
    """
    echo(_assets_list(address))


@ocean.group()
def agreements():
    """
    Create and list agreements
    """
    pass


@click.pass_context
def _agreements_list(ctx, did_or_address):
    try:
        assert(is_did_valid(did_or_address), True)
        agreement_store = AgreementStoreManager.get_instance()
        agreement_ids = [
            Web3Provider.get_web3().toHex(_id)
            for _id in agreement_store.contract_concise \
                .getAgreementIdsForDID(did_to_id_bytes(did_or_address))
        ]
    except Exception as e:
        if did_or_address == 'me':
            did_or_address = ctx.obj['account'].address
        agreement_ids = []
        for did in _assets_list(did_or_address):
            agreement_ids += _agreements_list(did)
    return agreement_ids


@agreements.command('list')
@click.argument('did_or_address')
def agreements_list(did_or_address):
    echo(_agreements_list(did_or_address))


@agreements.command('get')
@click.argument('agreement_id')
@click.pass_context
def agreements_get(ctx, agreement_id):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    agreement = ocean.agreements.get(agreement_id)
    echo(agreement._asdict())


@agreements.command('status')
@click.argument('agreement_id')
@click.pass_context
def agreements_status(ctx, agreement_id):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    status = ocean.agreements.status(agreement_id)
    echo(status)


@agreements.command('prepare')
@click.argument('did')
@click.argument('service_id', default=1)
@click.pass_context
def agreements_prepare(ctx, did, service_id):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    agreement_id, signature = ocean.agreements.prepare(
        did, service_id, account
    )
    echo({
        'agreement': agreement_id,
        'signature': signature
    })


@agreements.command('create-prepared')
@click.argument('agreement_id')
@click.argument('service_id', default=1)
@click.argument('signature', default='')
@click.pass_context
def agreements_create_prepared(ctx, agreement_id, service_id, signature):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    agreement = ocean.agreements.get(agreement_id)
    result = ocean.agreements.create(id_to_did(agreement.did),
                                     service_id, agreement_id,
                                     signature, account.address, account)
    echo({
        "result": result
    })


@agreements.command('create')
@click.argument('did')
@click.argument('service_id', default=1)
@click.pass_context
def agreements_create(ctx, did, service_id):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    agreement_id, signature = ocean.agreements.prepare(
        did, service_id, account
    )
    result = ocean.agreements.create(did, service_id, agreement_id,
                                     signature, account.address, account)
    echo({
        'agreement': agreement_id,
        'signature': signature,
        'result': result
    })


@agreements.command('send')
@click.argument('did')
@click.argument('service_id')
@click.argument('agreement_id')
@click.argument('signature')
@click.pass_context
def agreements_send(ctx, did, agreement_id, service_id, signature):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    result = ocean.agreements.send(
        did, agreement_id, service_id, signature, account
    )
    echo({
        "result": result
    })


@ocean.group()
def conditions():
    """
    List and fulfill conditions
    """
    pass


def _conditions_lock_reward(ctx, agreement_id):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    keeper = Keeper.get_instance()
    ocean_conditions = OceanConditions(keeper)
    amount = int(get_service_agreement_from_id(agreement_id).get_price())
    keeper.token.token_approve(keeper.lock_reward_condition.address,
                               amount,
                               account)
    return ocean_conditions.lock_reward(agreement_id, amount, account)


@conditions.command('lock-reward')
@click.argument('agreement_id')
@click.argument('amount')
def conditions_lock_reward(agreement_id):
    response = _conditions_lock_reward(agreement_id)
    echo({
        "response": response
    })


@click.pass_context
def _conditions_access(ctx, agreement_id, consumer):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    if agreement_id == 'all':
        response = False
        for _agreement_id in _agreements_list(account.address):
            try:
                response = _conditions_access(_agreement_id, consumer)
            except Exception as e:
                pass
        return response
    ocean_conditions = OceanConditions(Keeper.get_instance())
    agreement = ocean.agreements.get(agreement_id)
    return ocean_conditions.grant_access(agreement_id,
                                         id_to_did(agreement.did),
                                         consumer, account)


@conditions.command('access')
@click.argument('agreement_id')
@click.argument('consumer')
def conditions_access(agreement_id, consumer):
    response = _conditions_access(agreement_id, consumer)
    echo({
        "response": response
    })


@click.pass_context
def _conditions_release_reward(ctx, agreement_id):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    if agreement_id == 'all':
        response = False
        for _agreement_id in _agreements_list(account.address):
            try:
                response = _conditions_release_reward(_agreement_id)
            except Exception as e:
                pass
        return response
    amount = int(get_service_agreement_from_id(agreement_id).get_price())
    ocean_conditions = OceanConditions(Keeper.get_instance())
    return ocean_conditions.release_reward(
        agreement_id,
        amount,
        account
    )


@conditions.command('release-reward')
@click.argument('agreement_id')
def conditions_release_reward(agreement_id):
    response = _conditions_release_reward(agreement_id)
    echo({
        "response": response
    })


@conditions.command('check-permissions')
@click.argument('did')
@click.pass_context
def conditions_check_permissions(ctx, did):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    access = ocean.keeper.access_secret_store_condition.get_instance()
    response = access.check_permissions(did_to_id_bytes(did), account.address)
    echo({
        "response": response
    })


@ocean.group()
def events():
    """
    Listen to events
    """
    pass


def handle_event(event, *_):
    print(f"\n{'*'*20}"
          f"\n{event['blockNumber']}: {event['event']}"
          f"\n{event}"
          f"\n{'*'*20}")


@events.command('listen')
@click.pass_context
def listen(ctx):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    did = ocean.keeper.did_registry.get_instance()
    template = ocean.keeper.escrow_access_secretstore_template.get_instance()
    lockreward = ocean.keeper.lock_reward_condition.get_instance()
    conditions = ocean.keeper.condition_manager.get_instance()
    filters = [
        did.events.DIDAttributeRegistered.createFilter(fromBlock='latest'),
        template.events.AgreementCreated.createFilter(fromBlock='latest'),
        lockreward.events.Fulfilled.createFilter(fromBlock='latest'),
        conditions.events.ConditionUpdated.createFilter(fromBlock='latest')
    ]
    while True:
        for filter in filters:
            for event in filter.get_new_entries():
                handle_event(event)
            time.sleep(0.5)


@click.pass_context
def handle_event_access(ctx, event, *_):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    agreement_id = Web3Provider.get_web3().toHex(event['args']['_agreementId'])
    is_provider = event['args']['_accessProvider'] == account.address
    if is_provider:
        consumer = event['args']['_accessConsumer']
        time.sleep(5)
        print(
            f"Access:{agreement_id}-{consumer}",
            _conditions_access(agreement_id, consumer))
        handle_event(event)
        time.sleep(5)
        print(
            f"Release:{agreement_id}",
            _conditions_release_reward(agreement_id))


@events.command('access')
@click.pass_context
def access(ctx):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    template = ocean.keeper.escrow_access_secretstore_template.get_instance()
    filter = template.events.AgreementCreated.createFilter(fromBlock='latest')
    while True:
        for event in filter.get_new_entries():
            handle_event_access(event)
        time.sleep(0.5)


@ocean.group()
def secretstore():
    """
    Encrypt and decrypt with Parity SecretStore
    """
    pass


@secretstore.command('encrypt')
@click.argument('plain_text')
@click.pass_context
def encrypt(ctx, plain_text):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    doc_id = did_to_id(DID.did())
    encrypted_document = ocean.secret_store.encrypt(doc_id, plain_text, account)
    echo({
        'docId': doc_id,
        'encryptedDocument': encrypted_document
    })


@secretstore.command('decrypt')
@click.argument('doc_id')
@click.argument('cipher_text')
@click.pass_context
def decrypt(ctx, doc_id, cipher_text):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    decrypted_document = ocean.secret_store.decrypt(doc_id, cipher_text, account)

    echo({
        'decryptedDocument': decrypted_document
    })


if __name__ == "__main__":
    ocean()


