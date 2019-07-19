import { Ocean, Logger } from '@oceanprotocol/squid'

import {
    aquariusUri,
    brizoUri,
    brizoAddress,
    faucetUri,
    nodeUri,
    secretStoreUri,
    verbose
} from './config'

export async function provideOcean(web3Provider) {
    const config = {
        web3Provider,
        nodeUri,
        aquariusUri,
        brizoUri,
        brizoAddress,
        secretStoreUri,
        verbose
    }

    const ocean = await Ocean.getInstance(config)
    return { ocean }
}


export async function requestFromFaucet(account, amount = 0.05) {
    try {
        const url = `${faucetUri}/faucet`
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                address: account,
                agent: 'commons'
            })
        })
        return response.json()
    } catch (error) {
        Logger.error('requestFromFaucet', error.message)
    }
}

export async function requestOcean(ocean, amount = 1) {
    return ocean.tokens.request((await ocean.accounts.list())[0], parseInt(amount))
}
