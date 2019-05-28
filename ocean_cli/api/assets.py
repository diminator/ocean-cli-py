import json
import os
import time

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


def create(ocn, account, metadata, secret_store,
           price=0,
           purchase_endpoint='https://marketplace.ocean',
           service_endpoint='http://localhost:8000',
           timeout=3600):
    """
    Publish an asset from metadata
    """
    if not isinstance(metadata, dict):
        # Assume it is a path to metadata json file
        metadata = json.load(open(metadata, 'r'))
    metadata['base']['price'] = price
    service_descriptors = [
        ServiceDescriptor.access_service_descriptor(
            price,
            purchase_endpoint,
            service_endpoint,
            timeout,
            ocn.keeper.escrow_access_secretstore_template.address
        )
    ]
    ddo = ocn.assets.create(
        metadata,
        account,
        service_descriptors=service_descriptors,
        providers=[account.address],
        use_secret_store=secret_store
    )
    return ddo.did


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


def search(ocn, text, pretty=False):
    """
    Search assets by keyword
    """
    result = ocn.assets.search(text, sort=None, offset=100, page=1)
    if pretty:
        response = []
        for ddo in result:
            response += [f"{ddo.metadata['base']['name']}"
                         f" - {ddo.metadata['base']['author']}"
                         f" - {ddo.metadata['base']['price']}"
                         f" - {ddo.metadata['base']['type']}"]
        return response
    return [ddo.did for ddo in result]


def order(ocn, account, did):
    from .agreements import get_agreement_from_did
    from .conditions import lock_reward
    sa = get_agreement_from_did(ocn, did)
    agreement_id = ocn.assets\
        .order(did, sa.service_definition_id, account, True)
    lock_reward(ocn, account, agreement_id)

    return agreement_id


def consume(ocn, account, agreement_id, method='download'):
    agreement = ocn.agreements.get(agreement_id)
    did = id_to_did(agreement.did)
    token = decrypt(ocn, account, did)
    if method == 'download':
        return consume_download(ocn, account, did, agreement_id, token)
    elif method == 'get':
        return consume_get(ocn, did, token)


def consume_get(ocn, did, token):
    service_endpoint = get_service_endpoint(ocn, did)
    url = ''
    if len(token) and token[0]['url']:
        url = token[0]['url']
    response = requests.get(service_endpoint + "/" + url)
    return response.text


def consume_download(ocn, account, did, agreement_id, token):
    service_endpoint = get_service_endpoint(ocn, did)

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


def order_consume(ocn, account, did,
                  method='download',
                  wait=20):
    agreement_id = order(ocn, account, did)
    i = 0
    while ocn.agreements.is_access_granted(agreement_id, did, account.address) \
            is not True and i < wait:
        time.sleep(1)
        i += 1
    return consume(ocn, account, agreement_id, method)


def decrypt(ocn, account, did):
    ddo = ocn.assets.resolve(did)
    encrypted_files = ddo.metadata['base']['encryptedFiles']
    encrypted_files = (
        encrypted_files if isinstance(encrypted_files, str)
        else encrypted_files[0]
    )

    secret_store = ocn.assets._get_secret_store(account)
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
        decrypted_content_urls = encrypted_files

    if isinstance(decrypted_content_urls, str):
        decrypted_content_urls = [decrypted_content_urls]
    return decrypted_content_urls


def list_assets(ocn, account, address):
    did_registry = DIDRegistry.get_instance()
    did_registry_ids = did_registry.contract_concise.getDIDRegisterIds()
    did_list = [
         id_to_did(Web3Provider.get_web3().toHex(did)[2:])
         for did in did_registry_ids
    ]
    if address:
        if address == 'me':
            address = account.address
        result = []
        for did in did_list:
            try:
                asset_owner = ocn.assets.resolve(did).as_dictionary()['publicKey'][0]['owner']
                if asset_owner == address:
                    result += [did]
            except ValueError:
                pass
        return result
    return did_list


def get_service_endpoint(ocn, did):
    ddo = ocn.assets.resolve(did)
    service = ddo.get_service(service_type=ServiceTypes.ASSET_ACCESS)
    service_id = service.service_definition_id
    return ServiceAgreement.from_ddo(service_id, ddo).service_endpoint
