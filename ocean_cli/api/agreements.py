from squid_py.agreements.service_agreement import ServiceAgreement
from squid_py.agreements.service_factory import ServiceTypes
from squid_py.did import did_to_id_bytes, id_to_did, is_did_valid
from squid_py.keeper.agreements.agreement_manager import AgreementStoreManager
from squid_py.keeper.web3_provider import Web3Provider


def get_agreement_from_did(ocn, did):
    ddo = ocn.assets.resolve(did)
    service = ddo.get_service(service_type=ServiceTypes.ASSET_ACCESS)
    return ServiceAgreement.from_service_dict(service.as_dictionary())


def get_agreement_from_id(ocn, agreement_id):
    agreement = ocn.agreements.get(agreement_id)
    did = id_to_did(agreement.did)
    return get_agreement_from_did(ocn, did)


def list_agreements(did_or_address, ocean=None):
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
            did_or_address = ocean.account.address
        agreement_ids = []
        for did in ocean.assets.list(did_or_address):
            try:
                agreement_ids += list_agreements(did, ocean)
            except ValueError as e:
                pass
    return agreement_ids


def create(ocean, account, did, service_id):
    agreement_id, signature = ocean.agreements.prepare(
        did, service_id, account
    )
    result = create_agreement(did,
                              service_id,
                              agreement_id,
                              account.address,
                              ocean=ocean)
    return {
        'agreement': agreement_id,
        'signature': signature,
        'result': result
    }


def create_agreement(did,
                     service_definition_id,
                     agreement_id,
                     consumer_address,
                     ocean=None):
    assert consumer_address and Web3Provider.get_web3().isChecksumAddress(
        consumer_address), f'Invalid consumer address {consumer_address}'

    asset = ocean.assets.resolve(did)
    asset_id = asset.asset_id
    service_agreement = ServiceAgreement.from_ddo(service_definition_id, asset)
    agreement_template = ocean.keeper.escrow_access_secretstore_template.get_instance()

    publisher_address = Web3Provider.get_web3().toChecksumAddress(asset.publisher)
    condition_ids = service_agreement\
        .generate_agreement_condition_ids(
            agreement_id,
            asset_id,
            consumer_address,
            publisher_address,
            ocean.keeper
        )
    time_locks = service_agreement.conditions_timelocks
    time_outs = service_agreement.conditions_timeouts
    return agreement_template.create_agreement(
        agreement_id,
        asset_id,
        condition_ids,
        time_locks,
        time_outs,
        consumer_address,
        ocean.account
    )
