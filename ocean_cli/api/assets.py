import json
import os
import time

from squid_py import ConfigProvider
from squid_py.agreements.service_agreement import ServiceAgreement
from squid_py.agreements.service_factory import ServiceTypes, ServiceDescriptor
from squid_py.did import id_to_did, did_to_id
from squid_py.keeper import Keeper, DIDRegistry
from squid_py.keeper.didregistry import DIDRegisterValues
from squid_py.keeper.web3_provider import Web3Provider


def create(ocn, account, metadata, secret_store):
    """
    Publish an asset from metadata
    """
    if not isinstance(metadata, dict):
        # Assume it is a path to metadata json file
        metadata = json.load(open(metadata, 'r'))
    service_descriptors = [
        ServiceDescriptor.access_service_descriptor(
            10,
            'http://purchase',
            'http://localhost:8888',
            3600,
            ocn._keeper.escrow_access_secretstore_template.address
        )
    ]
    ddo = ocn.assets.create(
        metadata,
        account,
        service_descriptors=service_descriptors,
        providers=[account.address],
        use_secret_store=secret_store
    )
    did_registry = Keeper.get_instance().did_registry
    provider = did_registry.to_checksum_address(account.address)
    time.sleep(10)
    try:
        did_registry.add_provider(ddo.asset_id, provider, account)
    except ValueError as e:
        print('ValueError', e)
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


def search(ocn, text):
    """
    Search assets by keyword
    """
    result = ocn.assets.search(text, sort=None, offset=100, page=1)
    return [ddo.did for ddo in result]


def order(ocn, account, did):
    from .agreements import get_agreement_from_did
    from .conditions import lock_reward
    sa = get_agreement_from_did(ocn, did)
    agreement_id = ocn.assets\
        .order(did, sa.service_definition_id, account, True)
    lock_reward(ocn, account, agreement_id)

    return agreement_id


def consume(ocn, account, agreement_id):
    agreement = ocn.agreements.get(agreement_id)
    did = id_to_did(agreement.did)

    service_id = ocn.assets.resolve(did).\
        get_service(service_type=ServiceTypes.ASSET_ACCESS)\
        .service_definition_id

    path = ocn.assets.consume(agreement_id, did, service_id, account,
                              ConfigProvider.get_config().downloads_path)
    files = os.listdir(path)

    return {
        'agreement': agreement_id,
        'path': path.split('tuna/')[-1] + '/',
        'files': files
    }


def decrypt(ocn, account, did):
    ddo = ocn.assets.resolve(did)
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
            'Consume asset failed, '
            'service definition is missing the "serviceEndpoint".')

    secret_store = ocn.assets._get_secret_store(account)
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
