import json
import os
import time, datetime

import requests
from secret_store_client.client import RPCError
from squid_py import ConfigProvider
from squid_py.agreements.service_agreement import ServiceAgreement
from squid_py.agreements.service_factory import ServiceTypes, ServiceDescriptor
from squid_py.did import id_to_did, did_to_id
from squid_py.keeper import Keeper, DIDRegistry
from squid_py.keeper.didregistry import DIDRegisterValues
from squid_py.keeper.web3_provider import Web3Provider
from squid_py.brizo import BrizoProvider

from ocean_cli.api.agreements import create_agreement


def make_metadata(name, author, files, price,
                  license='CC0: Public Domain',
                  type='dataset'):
    if isinstance(files, str):
        files = [{"url": files}]
    return {
      "base": {
        "name": name,
        "dateCreated": str(datetime.datetime.now()),
        "author": author,
        "license": license,
        "price": price,
        "files": files,
        "type": type
      }
    }


def create(metadata,
           secret_store=True,
           price=0,
           purchase_endpoint='https://marketplace.ocean',
           service_endpoint='/',
           timeout=3600,
           ocean=None):
    """
    Publish an asset from metadata
    """
    if not isinstance(metadata, dict):
        # Assume it is a path to metadata json file
        metadata = json.load(open(metadata, 'r'))
    service_descriptors = [
        ServiceDescriptor.access_service_descriptor(
            price,
            purchase_endpoint,
            service_endpoint,
            timeout,
            ocean.keeper.escrow_access_secretstore_template.address
        )
    ]
    ddo = ocean.assets.create(
        metadata,
        ocean.account,
        service_descriptors=service_descriptors,
        providers=[ocean.account.address],
        use_secret_store=secret_store
    )
    return ddo.did


def publish(name,
            secret,
            price=0,
            service_endpoint='/',
            ocean=None):
    return create(metadata=make_metadata(
                      name=name,
                      author=ocean.account.address,
                      files=secret,
                      price=price),
                  secret_store=True,
                  price=price,
                  service_endpoint=service_endpoint,
                  ocean=ocean)


def authorize(did, ocean=None, wait=5):
    from ocean_cli.api.conditions import check_permissions

    # order
    if not check_permissions(ocean, ocean.account, did):
        agreement_id = ocean.order(did)
    else:
        # TODO: get agreement id for did & consumer
        agreement_id = None

    # get credentials
    for _ in range(wait):
        service_endpoint, secret = credentials(ocean, did)
        if isinstance(secret, dict):
            return agreement_id, service_endpoint, secret
        print(secret)
        time.sleep(1)
    return agreement_id, None, None


def credentials(ocean, did):
    service_endpoint = get_service_endpoint(ocean, did)
    secret = ocean.decrypt(did)[0]
    return service_endpoint, secret
    
    
def consume(did,
            agreement_id,
            service_endpoint,
            secret,
            method='get',
            ocean=None):
    token = secret.get('token', None)
    url = secret.get('url', None)
    if method == 'brizo':
        return consume_brizo(ocean, ocean.account, did, agreement_id, token)
    elif method == 'get':
        return consume_get(url)
    elif method == 'api':
        return consume_api(ocean.account, did, service_endpoint, url, token)


def consume_agreement(ocean, agreement_id, method):
    agreement = ocean.agreements.get(agreement_id)
    did = id_to_did(agreement.did)
    service_endpoint, secret = credentials(ocean, did)
    return consume(did, agreement_id, service_endpoint, secret, method, ocean=ocean)


def consume_get(url):
    return requests.get(f'{url}')


def consume_api(account, did, service_endpoint, url, token):
    return requests.get(
        f'{service_endpoint}/{url}'
        f'?token={token}&did={did}&address={account.address}')


def consume_brizo(ocean, account, did, agreement_id, token):
    service_endpoint = get_service_endpoint(ocean, did)

    destination = ConfigProvider.get_config().downloads_path
    if not os.path.isabs(destination):
        destination = os.path.abspath(destination)
    if not os.path.exists(destination):
        os.mkdir(destination)

    asset_folder = os.path.join(destination, f'datafile.{did_to_id(did)}')
    if not os.path.exists(asset_folder):
        os.mkdir(asset_folder)

    BrizoProvider.get_brizo().consume_service(
        agreement_id,
        service_endpoint,
        account,
        token,
        asset_folder,
        None
    )
    files = os.listdir(asset_folder)

    return {
        'agreement': agreement_id,
        'path': asset_folder.split('tuna/')[-1] + '/',
        'files': files
    }


def get(did):
    register_values = Keeper.get_instance().did_registry.contract_concise\
        .getDIDRegister(did_to_id(did))
    response = []
    if register_values and len(register_values) == 5:
        response = DIDRegisterValues(*register_values)._asdict()
        response['last_checksum'] = Web3Provider.get_web3()\
            .toHex(response['last_checksum'])
    return response


def add_providers(account, did, provider):
    if provider == 'me':
        provider = account.address
    did_registry = Keeper.get_instance().did_registry
    return did_registry.add_provider(did_to_id(did), provider, account)


def search(text, pretty=False, ocean=None):
    """
    Search assets by keyword
    """
    result = ocean.assets.search(text, sort=None, offset=100, page=1)
    if pretty:
        response = []
        for ddo in result:
            response += [f"{ddo.metadata['base']['name']}"
                         f" - {ddo.metadata['base']['author']}"
                         f" - {ddo.metadata['base']['price']}"
                         f" - {ddo.metadata['base']['type']}"]
        return response
    return [ddo.did for ddo in result]


def order(did, ocean=None):
    from .agreements import get_agreement_from_did
    from .conditions import lock_reward
    sa = get_agreement_from_did(ocean, did)
    agreement_id = ocean.agreements.new()
    create_agreement(
        did,
        sa.service_definition_id,
        agreement_id,
        ocean.account.address,
        ocean=ocean
    )
    lock_reward(ocean, ocean.account, agreement_id)

    return agreement_id


def decrypt(did, ocean=None):
    ddo = ocean.assets.resolve(did)
    encrypted_files = ddo.metadata['base']['encryptedFiles']
    encrypted_files = (
        encrypted_files if isinstance(encrypted_files, str)
        else encrypted_files[0]
    )

    secret_store = ocean.assets._get_secret_store(ocean.account)
    if ddo.get_service('Authorization'):
        secret_store_service = ddo.get_service(
            service_type=ServiceTypes.AUTHORIZATION)
        secret_store_url = secret_store_service.endpoints.service
        secret_store.set_secret_store_url(secret_store_url)

    # decrypt the contentUrls
    try:
        decrypted_content_urls = json.loads(
            secret_store.decrypt_document(did_to_id(did), encrypted_files)
        )
    except RPCError:
        print('Not able to decrypt')
        decrypted_content_urls = encrypted_files

    if isinstance(decrypted_content_urls, str):
        decrypted_content_urls = [decrypted_content_urls]
    return decrypted_content_urls


def list_assets(address=None, ocean=None):
    did_registry = DIDRegistry.get_instance()
    did_registry_ids = did_registry.contract_concise.getDIDRegisterIds()
    did_list = [
         id_to_did(Web3Provider.get_web3().toHex(did)[2:])
         for did in did_registry_ids
    ]
    if address:
        if address == 'me':
            address = ocean.account.address
        result = []
        for did in did_list:
            try:
                asset_owner = ocean.assets.resolve(did).as_dictionary()['publicKey'][0]['owner']
                if asset_owner == address:
                    result += [did]
            except ValueError:
                pass
        return result
    return did_list


def get_service_endpoint(ocean, did):
    ddo = ocean.assets.resolve(did)
    service = ddo.get_service(service_type=ServiceTypes.ASSET_ACCESS)
    service_id = service.service_definition_id
    return ServiceAgreement.from_ddo(service_id, ddo).service_endpoint
