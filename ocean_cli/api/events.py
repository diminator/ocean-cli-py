import time

from squid_py.did import id_to_did
from squid_py.keeper.web3_provider import Web3Provider
from ocean_cli.api.conditions import release_reward
from squid_py.ocean.ocean_conditions import OceanConditions

from squid_py.keeper import Keeper

# global: bad practice
agreements = {}


def handle_agreement_created(event=None, agreement_id=None, ocean=None,
                             *args, **kwargs):
    time.sleep(3)
    consumer = event['args'].get('_accessConsumer', None)
    provider = event['args'].get('_accessProvider', None)
    if provider == ocean.account.address:
        did = id_to_did(ocean.agreements.get(agreement_id).did)
        return {
            'did': did,
            'consumer': consumer,
            'provider': provider
        }


def handle_lock_reward(agreement_id=None, agreement=None, ocean=None,
                       *args, **kwargs):
    ocean_conditions = OceanConditions(Keeper.get_instance())
    consumer = agreement['consumer']
    did = agreement['did']
    print(
        f'Access: {agreement_id} for {consumer}',
        ocean_conditions.grant_access(agreement_id,
                                      did,
                                      consumer,
                                      ocean.account))
    print(
        f'Release: {agreement_id}',
        release_reward(agreement_id, ocean=ocean)
    )


def listen_lock_reward(callback_agreement_created=handle_agreement_created,
                       callback_lock_reward=handle_lock_reward,
                       ocean=None):
    template = ocean.keeper.escrow_access_secretstore_template.get_instance()
    lock_reward = ocean.keeper.lock_reward_condition.get_instance()
    filters = [
        template.events.AgreementCreated.createFilter(fromBlock='latest'),
        lock_reward.events.Fulfilled.createFilter(fromBlock='latest'),
    ]

    while True:
        for _filter in filters:
            try:
                for event in _filter.get_new_entries():
                    print(f"\n\n{'*'*30}\nEVENT: {event['event']}\n{'*'*30}\n\n", event)
                    agreement_id = Web3Provider.get_web3().toHex(
                        event['args'].get('_agreementId', None)
                    )

                    print(ocean.agreements.status(agreement_id))

                    if event['event'] == 'AgreementCreated':
                        agreements[agreement_id] = \
                            callback_agreement_created(event=event,
                                                       agreement_id=agreement_id,
                                                       ocean=ocean)
                    elif event['event'] == 'Fulfilled':
                        if agreement_id in agreements:
                            agreement = agreements[agreement_id]
                            callback_lock_reward(event=event,
                                                 agreement_id=agreement_id,
                                                 agreement=agreement,
                                                 ocean=ocean)
                            del agreements[agreement_id]
                        else:
                            # todo clean error handling
                            print(f'error: agreement {agreement_id} '
                                  f'not in {agreements}')
                    print(ocean.agreements.status(agreement_id))
            except ValueError as e:
                print('error', e)
                # avoid hangup, refresh filters
                filters = [
                    template.events.AgreementCreated.createFilter(
                        fromBlock='latest'),
                    lock_reward.events.Fulfilled.createFilter(
                        fromBlock='latest'),
                ]
        time.sleep(0.1)
