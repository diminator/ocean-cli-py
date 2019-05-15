import click
import json
import logging
import os
import re
import time

from squid_py import ConfigProvider
from squid_py.accounts.account import Account
from squid_py.agreements.service_agreement import ServiceAgreement
from squid_py.agreements.service_factory import ServiceTypes
from squid_py.config import Config
from squid_py.did import did_to_id_bytes, id_to_did
from squid_py.keeper import Keeper, Token, DIDRegistry
from squid_py.keeper.agreements.agreement_manager import AgreementStoreManager
from squid_py.keeper.web3_provider import Web3Provider
from squid_py.ocean.ocean import Ocean
from squid_py.ocean.ocean_conditions import OceanConditions

logging.getLogger().setLevel(logging.ERROR)


def get_default_account(config):
    account_address = config.get('keeper-contracts', 'account.address')
    account_password = config.get('keeper-contracts', 'account.password')
    account = Account(
        Web3Provider.get_web3().toChecksumAddress(account_address),
        account_password)
    return account


@click.pass_context
def echo(ctx, response):
    response = json.dumps(response, indent=2, sort_keys=True)
    if ctx.obj['json']:
        pass
    else:
        response = re.sub(r'\n\s*\n', '\n',
            re.sub(r'[\",{}\[\]]', '', response))
    click.echo(response)


@click.group()
@click.option('--config-file', '-c',
              type=click.Path(),
              default='./config.ini', show_default=True)
@click.option('--as-json', '-j',
              is_flag=True)
@click.pass_context
def ocean(ctx, config_file, as_json):
    """
    Simple CLI for registering and consuming assets in Ocean Protocol
    """
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
@click.pass_context
def assets_create(ctx, metadata):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    if not isinstance(metadata, dict):
        # Assume it is a path to metadata json file
        metadata = json.load(open(metadata, 'r'))

    ddo = ocean.assets.create(
        metadata,
        account,
        providers=[account.address],
        use_secret_store=False
    )
    did_registry = Keeper.get_instance().did_registry
    provider = did_registry.to_checksum_address(account.address)
    did_registry.add_provider(ddo.asset_id, provider, account)
    echo({
        'did': ddo.did,
    })


@assets.command('search')
@click.argument('text')
@click.pass_context
def assets_search(ctx, text):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    result = ocean.assets.search(text, sort=None, offset=100, page=1)
    echo([ddo.did for ddo in result])


def _assets_order(ctx, did):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    ddo = ocean.assets.resolve(did)
    service = ddo.get_service(service_type=ServiceTypes.ASSET_ACCESS)
    sa = ServiceAgreement.from_service_dict(service.as_dictionary())

    service_agreement_id = ocean.assets.order(did, sa.service_definition_id,
                                              account, True)

    i = 0
    while ocean.agreements.is_access_granted(
            service_agreement_id, ddo.did,
            account.address) is not True and i < 30:
        time.sleep(1)
        i += 1
    return {
        'service': sa.service_definition_id,
        'agreement': service_agreement_id
    }


@assets.command('order')
@click.argument('did')
@click.pass_context
def assets_order(ctx, did):
    echo(_assets_order(ctx, did))


def _assets_consume(ctx, agreement_id, service_id):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    agreement = ocean.agreements.get(agreement_id)
    path = ocean.assets.consume(agreement_id,
                                id_to_did(agreement.did), service_id, account,
                                ConfigProvider.get_config().downloads_path)
    files = os.listdir(path)

    return {
        'path': path.split('tuna/')[-1] + '/',
        'files': files
    }


@assets.command('consume')
@click.argument('did')
@click.pass_context
def assets_consume(ctx, did):
    response = _assets_order(ctx, did)
    echo(_assets_consume(ctx, response['agreement'], response['service']))


@assets.command('consume-agreement')
@click.argument('agreement_id')
@click.argument('service_id', default=1)
@click.pass_context
def assets_consume_agreement(ctx, agreement_id, service_id):
    echo(_assets_consume(ctx, agreement_id, service_id))


@assets.command('resolve')
@click.argument('did')
@click.pass_context
def assets_resolve(ctx, did):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    asset = ocean.assets.resolve(did)
    echo(asset.as_dictionary())


@assets.command('list')
def assets_list():
    did_registry = DIDRegistry.get_instance()
    did_registry_ids = did_registry.contract_concise.getDIDRegisterIds()
    echo([
        id_to_did(Web3Provider.get_web3().toHex(did)[2:])
        for did in did_registry_ids
    ])


@ocean.group()
def agreements():
    """
    Create and list agreements
    """
    pass


@agreements.command('list')
@click.argument('did')
def agreements_list(did):
    agreement_store = AgreementStoreManager.get_instance()
    agreement_ids = agreement_store.contract_concise\
        .getAgreementIdsForDID(did_to_id_bytes(did))
    echo([
        Web3Provider.get_web3().toHex(_id) for _id in agreement_ids
    ])


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


@conditions.command('lock-reward')
@click.argument('agreement_id')
@click.argument('amount')
@click.pass_context
def conditions_lock_reward(ctx, agreement_id, amount):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    keeper = Keeper.get_instance()
    ocean_conditions = OceanConditions(keeper)
    keeper.token.token_approve(keeper.lock_reward_condition.address,
                               int(amount),
                               account)
    response = ocean_conditions.lock_reward(agreement_id, int(amount), account)
    echo({
        "response": response
    })


@conditions.command('access')
@click.argument('agreement_id')
@click.argument('consumer')
@click.pass_context
def conditions_access(ctx, agreement_id, consumer):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    ocean_conditions = OceanConditions(Keeper.get_instance())
    agreement = ocean.agreements.get(agreement_id)
    response = ocean_conditions.grant_access(agreement_id,
                                             id_to_did(agreement.did),
                                             consumer, account)
    echo({
        "response": response
    })


@conditions.command('release-reward')
@click.argument('agreement_id')
@click.argument('amount')
@click.pass_context
def conditions_release_reward(ctx, agreement_id, amount):
    ocean, account = ctx.obj['ocean'], ctx.obj['account']
    ocean_conditions = OceanConditions(Keeper.get_instance())
    response = ocean_conditions.release_reward(agreement_id, int(amount),
                                               account)
    echo({
        "response": response
    })


if __name__ == "__main__":
    ocean()
