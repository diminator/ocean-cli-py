import click
import json
import logging
import re
import time

from squid_py import ConfigProvider
from squid_py.accounts.account import Account
from squid_py.config import Config
from squid_py.did import did_to_id_bytes, id_to_did, did_to_id, DID
from squid_py.keeper import Keeper, Token
from squid_py.keeper.web3_provider import Web3Provider
from squid_py.ocean.ocean import Ocean


def get_default_account(config):
    account_address = config.get('keeper-contracts', 'account.address')
    account_password = config.get('keeper-contracts', 'account.password')
    account = Account(
        Web3Provider.get_web3().toChecksumAddress(account_address),
        account_password)
    return account


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
    from .api.assets import create
    response = create(ctx.obj['ocean'], ctx.obj['account'],
                      metadata,
                      secret_store)
    echo([response])


@assets.command('add-providers')
@click.argument('did')
@click.argument('provider', default=None)
@click.pass_context
def assets_add_providers(ctx, did, provider):
    from .api.assets import add_providers
    response = add_providers(ctx.obj['account'],
                             did,
                             provider)
    echo(f"{response}")


@assets.command('get-providers')
@click.argument('did')
def assets_get_providers(did):
    response = Keeper.get_instance().did_registry\
        .get_did_providers(did_to_id(did))
    echo(response)


@assets.command('get-owner')
@click.argument('did')
def assets_get_owner(did):
    response = Keeper.get_instance().did_registry\
        .get_did_owner(did_to_id(did))
    echo(response)


@assets.command('get')
@click.argument('did')
def assets_get(did):
    from .api.assets import get
    response = get(did)
    echo(response)


@assets.command('search')
@click.argument('text')
@click.pass_context
def assets_search(ctx, text):
    """
    Search assets by keyword
    """
    from .api.assets import search
    response = search(ctx.obj['ocean'], text)
    echo(response)


@assets.command('order')
@click.argument('did')
@click.pass_context
def assets_order(ctx, did):
    """
    Order asset: create Service Agreement and lock reward
    """
    from .api.assets import order
    response = order(ctx.obj['ocean'], ctx.obj['account'], did)
    echo([response])


@assets.command('consume')
@click.argument('did')
@click.option('--wait', '-w', default=30, show_default=True)
@click.pass_context
def assets_consume(ctx, did, wait):
    """
    Consume asset: create Service Agreement, lock reward, [wait], decrypt & download
    """
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    from ocean_cli.api.assets import order
    agreement_id = order(ocean, account, did)
    i = 0
    while ocean.agreements\
            .is_access_granted(agreement_id, did, account.address) \
            is not True \
            and i < wait:
        time.sleep(1)
        i += 1
    from ocean_cli.api.assets import consume
    response = consume(ocean, account, agreement_id)
    echo(response)


@assets.command('decrypt')
@click.argument('did')
@click.pass_context
def assets_decrypt(ctx, did):
    """
    Decrypt asset service
    """
    from .api.assets import decrypt
    response = decrypt(ctx.obj['ocean'], ctx.obj['account'], did)
    echo(response)


@assets.command('consume-agreement')
@click.argument('agreement_id')
@click.pass_context
def assets_consume_agreement(ctx, agreement_id):
    """
    Consume agreement: decrypt and download
    """
    from .api.assets import consume
    response = consume(ctx.obj['ocean'], ctx.obj['account'], agreement_id)
    echo(response)


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


@assets.command('list')
@click.option('-a', '--address')
@click.pass_context
def assets_list(ctx, address):
    """
    List assets on-chain
    """
    from .api.assets import list_assets
    response = list_assets(ctx.obj['ocean'], ctx.obj['account'], address)
    echo(response)


@ocean.group()
def agreements():
    """
    Create and list agreements
    """
    pass


@agreements.command('list')
@click.argument('did_or_address')
@click.pass_context
def agreements_list(ctx, did_or_address):
    from .api.agreements import list_agreements
    response = list_agreements(ctx.obj['ocean'], ctx.obj['account'],
                               did_or_address)
    echo(response)


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
    from .api.agreements import create
    response = create(ctx.obj['ocean'], ctx.obj['account'], did, service_id)
    echo(response)


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


@conditions.command('lock-reward')
@click.argument('agreement_id')
@click.argument('amount')
@click.pass_context
def conditions_lock_reward(ctx, agreement_id):
    from .api.conditions import lock_reward
    response = lock_reward(ctx.obj['ocean'], ctx.obj['account'], agreement_id)
    echo({
        "response": response
    })


@conditions.command('access')
@click.argument('agreement_id')
@click.argument('consumer')
@click.pass_context
def conditions_access(ctx, agreement_id, consumer):
    from .api.conditions import access
    response = access(ctx.obj['ocean'], ctx.obj['account'],
                      agreement_id, consumer)
    echo({
        "response": response
    })


@conditions.command('release-reward')
@click.argument('agreement_id')
@click.pass_context
def conditions_release_reward(ctx, agreement_id):
    from .api.conditions import release_reward
    response = release_reward(ctx.obj['ocean'], ctx.obj['account'],
                              agreement_id)
    echo({
        "response": response
    })


@conditions.command('check-permissions')
@click.argument('did')
@click.pass_context
def conditions_check_permissions(ctx, did):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    access_ = ocean.keeper.access_secret_store_condition.get_instance()
    response = access_.check_permissions(did_to_id_bytes(did), account.address)
    echo({
        "response": response
    })


@ocean.group()
def events():
    """
    Listen to events
    """
    pass


def print_event(event, *_):
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
                print_event(event)
            time.sleep(0.5)


@events.command('access')
@click.pass_context
def access(ctx):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    template = ocean.keeper.escrow_access_secretstore_template.get_instance()
    filter = template.events.AgreementCreated.createFilter(fromBlock='latest')
    while True:
        for event in filter.get_new_entries():
            access_provider = event['args']['_accessProvider']
            if access_provider == account.address:
                agreement_id = Web3Provider.get_web3().toHex(
                    event['args']['_agreementId'])
                access_consumer = event['args']['_accessConsumer']
                from .api.conditions import access_release
                access_release(ocean, account, agreement_id, access_consumer)
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


