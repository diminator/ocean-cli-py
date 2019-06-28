import os
import click
import json
import logging
import re
import time
from functools import partial

from squid_py import ConfigProvider
from squid_py.accounts.account import Account
from squid_py.config import Config
from squid_py.did import id_to_did, did_to_id, DID
from squid_py.keeper import Keeper, Token
from squid_py.keeper.web3_provider import Web3Provider
from squid_py.ocean.ocean import Ocean


def get_ocean(config_file):
    ConfigProvider.set_config(Config(filename=config_file))
    ocn = Ocean()
    ocn.account = get_default_account(ConfigProvider.get_config())
    ocn.balance = partial(ocn.accounts.balance, ocn.account)
    from ocean_cli.api.assets import (
        authorize,
        consume,
        decrypt,
        list_assets,
        order,
        publish,
        search
    )
    ocn.authorize = partial(authorize, ocean=ocn)
    ocn.consume = partial(consume, ocean=ocn)
    ocn.decrypt = partial(decrypt, ocean=ocn)
    ocn.order = partial(order, ocean=ocn)
    ocn.assets.list = partial(list_assets, ocean=ocn)
    ocn.publish = partial(publish, ocean=ocn)
    ocn.search = partial(search, ocean=ocn)
    from ocean_cli.api.conditions import (
        check_permissions
    )
    ocn.check_permissions = partial(check_permissions, ocean=ocn)
    return ocn


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
    if isinstance(response, list):
        response = {
            'items': response,
            'total': len(response)
        }
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

    ctx.obj = {
        'ocean': get_ocean(config_file),
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
    account = ctx.obj['ocean'].account
    echo({
        'address': account.address
    })


@accounts.command('balance')
@click.option('-a', '--address')
@click.pass_context
def accounts_balance(ctx, address):
    ocean = ctx.obj['ocean']
    balance_account = ocean.account
    if address:
        balance_account = Account(address, address)
    balance = ocean.accounts.balance(balance_account)
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
    ocean = ctx.obj['ocean']
    account = ocean.account
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
    ocean = ctx.obj['ocean']
    account = ocean.account
    ocean.tokens.transfer(to, int(amount), account)
    echo({
        'amount': amount,
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


@assets.command('publish')
@click.argument('metadata', type=click.Path())
@click.option('--brizo', '-b', is_flag=True)
@click.option('--price', '-p', default=0)
@click.option('--service-endpoint', '-s', default='http://localhost:8000')
@click.option('--timeout', '-t', default=3600)
@click.pass_context
def assets_publish(ctx, metadata, brizo, price, service_endpoint, timeout):
    """
    Publish an asset from metadata
    """
    from .api.assets import create
    response = create(metadata,
                      secret_store=not brizo,
                      price=price,
                      service_endpoint=service_endpoint,
                      timeout=timeout,
                      ocean=ctx.obj['ocean'])
    echo(response)


@assets.command('consume')
@click.argument('did')
@click.option('--method', '-m', default='get', show_default=True,
              type=click.Choice(['get', 'api', 'brizo']))
@click.pass_context
def assets_consume(ctx, did, method):
    """
    Consume asset: create Service Agreement, lock reward, [wait], decrypt & download
    """
    ocean = ctx.obj['ocean']
    response = ocean.consume(did,
                             *ocean.authorize(did),
                             method=method)
    if method in ['get', 'api']:
        try:
            response = response.json()
        except json.decoder.JSONDecodeError:
            response = response.text
    echo(response)


@assets.command('push')
@click.argument('metadata', type=click.Path())
@click.option('--dir', '-d', default='.')
@click.option('--brizo', '-b', is_flag=True)
@click.option('--price', '-p', default=0)
@click.option('--service-endpoint', '-s', default='http://localhost:8000')
@click.option('--timeout', '-t', default=3600)
@click.pass_context
def assets_push(ctx, metadata, dir, brizo, price, service_endpoint, timeout):
    """
    Publish all files in current directory
    """
    try:
        files = [f for f in os.listdir(dir) if os.path.isfile(dir+'/'+f)]
    except NotADirectoryError:
        files = [dir]

    response = []
    metadata = json.load(open(metadata, 'r'))

    for f in files:
        metadata['base']['files'][0]['url'] = f
        response += [ctx.invoke(assets_publish,
                                metadata=metadata,
                                brizo=brizo,
                                price=price,
                                service_endpoint=service_endpoint,
                                timeout=timeout)]


@assets.command('pull')
@click.argument('text')
@click.option('--method', '-m', default='get', show_default=True)
@click.pass_context
def assets_pull(ctx, text, method):
    """
    Consume all assets on TEXT search
    """
    ocean = ctx.obj['ocean']
    response = []
    for did in ocean.search(text):
        print('pulling:', did)
        response += [ctx.invoke(assets_consume,
                                did=did,
                                method=method)]


@assets.command('add-providers')
@click.argument('did')
@click.argument('provider', default=None)
@click.pass_context
def assets_add_providers(ctx, did, provider):
    from .api.assets import add_providers
    response = add_providers(ctx.obj['ocean'].account,
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
@click.option('--pretty', '-p', is_flag=True)
@click.pass_context
def assets_search(ctx, text, pretty):
    """
    Search assets by keyword
    """
    ocean = ctx.obj['ocean']
    response = ocean.search(text, pretty)
    echo(response)


@assets.command('order')
@click.argument('did')
@click.pass_context
def assets_order(ctx, did):
    """
    Order asset: create Service Agreement and lock reward
    """
    response = ctx.obj['ocean'].order(did)
    echo([response])


@assets.command('decrypt')
@click.argument('did')
@click.pass_context
def assets_decrypt(ctx, did):
    """
    Decrypt asset service
    """
    response = ctx.obj['ocean'].decrypt(did)
    echo(response)


@assets.command('consume-agreement')
@click.argument('agreement_id')
@click.option('--method', '-m', default='get', show_default=True)
@click.pass_context
def assets_consume_agreement(ctx, agreement_id, method):
    """
    Consume agreement: decrypt and download
    """
    from .api.assets import consume_agreement
    response = consume_agreement(ctx.obj['ocean'], agreement_id, method)
    if method in ['get', 'api']:
        try:
            response = response.json()
        except json.decoder.JSONDecodeError:
            response = response.text
    echo(response)


@assets.command('resolve')
@click.argument('did')
@click.pass_context
def assets_resolve(ctx, did):
    """
    Resolve DID to DID Document
    """
    ddo = ctx.obj['ocean'].assets.resolve(did)
    echo(ddo.as_dictionary())


@assets.command('list')
@click.option('-a', '--address')
@click.pass_context
def assets_list(ctx, address):
    """
    List assets on-chain
    """
    response = ctx.obj['ocean'].assets.list(address)
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
    from ocean_cli.api.agreements import list_agreements
    response = list_agreements(did_or_address, ctx.obj['ocean'])
    echo(response)


@agreements.command('get')
@click.argument('agreement_id')
@click.pass_context
def agreements_get(ctx, agreement_id):
    agreement = ctx.obj['ocean'].agreements.get(agreement_id)
    echo(agreement._asdict())


@agreements.command('status')
@click.argument('agreement_id')
@click.pass_context
def agreements_status(ctx, agreement_id):
    status = ctx.obj['ocean'].agreements.status(agreement_id)
    echo(status)


@agreements.command('prepare')
@click.argument('did')
@click.argument('service_id', default=1)
@click.pass_context
def agreements_prepare(ctx, did, service_id):
    ocean = ctx.obj['ocean']
    agreement_id, signature = ocean.agreements.prepare(
        did, service_id, ocean.account
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
    ocean = ctx.obj['ocean']
    agreement = ocean.agreements.get(agreement_id)
    result = ocean.agreements.create(id_to_did(agreement.did),
                                     service_id,
                                     agreement_id,
                                     signature,
                                     ocean.account.address,
                                     ocean.account)
    echo({
        "result": result
    })


@agreements.command('create')
@click.argument('did')
@click.argument('service_id', default=1)
@click.pass_context
def agreements_create(ctx, did, service_id):
    from .api.agreements import create
    ocean = ctx.obj['ocean']
    response = create(ocean, ocean.account, did, service_id)
    echo(response)


@agreements.command('send')
@click.argument('did')
@click.argument('service_id')
@click.argument('agreement_id')
@click.argument('signature')
@click.pass_context
def agreements_send(ctx, did, agreement_id, service_id, signature):
    ocean = ctx.obj['ocean']
    result = ocean.agreements.send(did,
                                   agreement_id,
                                   service_id,
                                   signature,
                                   ocean.account)
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
    ocean = ctx.obj['ocean']
    response = lock_reward(ocean, ocean.account,
                           agreement_id)
    echo({
        "response": response
    })


@conditions.command('access')
@click.argument('agreement_id')
@click.argument('consumer')
@click.pass_context
def conditions_access(ctx, agreement_id, consumer):
    from .api.conditions import access
    ocean = ctx.obj['ocean']
    response = access(ocean, ocean.account,
                      agreement_id,
                      consumer)
    echo({
        "response": response
    })


@conditions.command('release-reward')
@click.argument('agreement_id')
@click.pass_context
def conditions_release_reward(ctx, agreement_id):
    from .api.conditions import release_reward
    ocean = ctx.obj['ocean']
    response = release_reward(agreement_id, ocean=ocean)
    echo({
        "response": response
    })


@conditions.command('check-permissions')
@click.argument('did')
@click.pass_context
def conditions_check_permissions(ctx, did):
    from .api.conditions import check_permissions
    response = check_permissions(did, ocean=ctx.obj['ocean'])
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
    ocean = ctx.obj['ocean']
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
    from ocean_cli.api.events import listen_lock_reward
    listen_lock_reward(ocean=ctx.obj['ocean'])


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


@ocean.group()
def notebook():
    """
    Convert DIDs into python notebooks
    """
    pass


@notebook.command('create')
@click.argument('did')
def create(did):
    from ocean_cli.api.notebook import create_notebook
    response = create_notebook(did, did)
    echo(response)


if __name__ == "__main__":
    ocean()


