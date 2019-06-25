import time

from squid_py.did import id_to_did
from squid_py.keeper.web3_provider import Web3Provider
from ocean_cli.api.conditions import release_reward
from squid_py.ocean.ocean_conditions import OceanConditions

from squid_py.keeper import Keeper


def handle_access(event, agreement_id, ocean=None):
    access_consumer = event['args'].get('_accessConsumer', None)
    access_provider = event['args'].get('_accessProvider', None)
    if access_provider == ocean.account.address:
        did = id_to_did(ocean.agreements.get(agreement_id).did)
        ocean_conditions = OceanConditions(Keeper.get_instance())
        ocean_conditions.grant_access(agreement_id,
                                      did,
                                      access_consumer,
                                      ocean.account)


def listen_lock_reward(ocean=None):
    template = ocean.keeper.escrow_access_secretstore_template.get_instance()
    lock_reward = ocean.keeper.lock_reward_condition.get_instance()

    filters = [
        template.events.AgreementCreated.createFilter(fromBlock='latest'),
        lock_reward.events.Fulfilled.createFilter(fromBlock='latest'),
    ]

    while True:
        for _filter in filters:
            for event in _filter.get_new_entries():
                print(f"\n\n{'*'*30}\n{event['event']}\n{'*'*30}\n\n", event)
                agreement_id = event['args'].get('_agreementId', None)
                if agreement_id:
                    agreement_id = Web3Provider.get_web3().toHex(agreement_id)
                    print('\n', ocean.agreements.get(agreement_id),
                          '\n', ocean.agreements.status(agreement_id))

                if event['event'] == 'AgreementCreated':
                        time.sleep(3)
                        print(
                            f'Access: {agreement_id}',
                            handle_access(event, agreement_id, ocean=ocean)
                        )
                elif event['event'] == 'Fulfilled':
                    print(
                        f'Release: {agreement_id}',
                        release_reward(ocean, ocean.account, agreement_id)
                    )
                print(ocean.agreements.status(agreement_id))
        time.sleep(0.1)
