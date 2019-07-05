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

export async function provideOcean(web3provider) {
    const config = {
        web3provider,
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


export async function requestFromFaucet(account) {
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
