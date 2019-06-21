import time

from ocean_cli.api.agreements import get_agreement_from_id, list_agreements
from squid_py.did import id_to_did, did_to_id_bytes
from squid_py.keeper import Keeper
from squid_py.ocean.ocean_conditions import OceanConditions


def lock_reward(ocean, account, agreement_id):
    keeper = Keeper.get_instance()
    ocean_conditions = OceanConditions(keeper)
    amount = int(get_agreement_from_id(ocean, agreement_id).get_price())
    keeper.token.token_approve(keeper.lock_reward_condition.address,
                               amount,
                               account)
    return ocean_conditions.lock_reward(agreement_id, amount, account)


def access(ocn, account, agreement_id, consumer):
    if agreement_id == 'all':
        response = False
        for _agreement_id in list_agreements(ocn, account, account.address):
            try:
                response = access(ocn, account, _agreement_id, consumer)
            except Exception as e:
                print(e)
        return response
    ocean_conditions = OceanConditions(Keeper.get_instance())
    agreement = ocn.agreements.get(agreement_id)
    return ocean_conditions.grant_access(agreement_id,
                                         id_to_did(agreement.did),
                                         consumer, account)


def check_permissions(ocn, account, did, address=None):
    address = address or account.address
    access_ = ocn.keeper.access_secret_store_condition.get_instance()
    return access_.check_permissions(did_to_id_bytes(did), address)


def release_reward(ocn, account, agreement_id):
    if agreement_id == 'all':
        response = False
        for _agreement_id in list_agreements(ocn, account, account.address):
            try:
                response = release_reward(ocn, account, _agreement_id)
            except Exception as e:
                print(e)
        return response
    amount = int(get_agreement_from_id(ocn, agreement_id).get_price())
    ocean_conditions = OceanConditions(Keeper.get_instance())
    return ocean_conditions.release_reward(
        agreement_id,
        amount,
        account
    )


def access_release(ocn, account, agreement_id, consumer):
    time.sleep(4)
    print(
        f"Access:{agreement_id}-{consumer}",
        access(ocn, account, agreement_id, consumer))
    time.sleep(2)
    print(
        f"Release:{agreement_id}",
        release_reward(ocn, account, agreement_id))
