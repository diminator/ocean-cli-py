import React from 'react'

export const User = React.createContext({
    isLogged: false,
    isLoading: false,
    isWeb3: false,
    isOceanNetwork: false,
    account: '',
    web3: {},
    ocean: {},
    did: null,
    ddo: {},
    balance: {
        eth: 0,
        ocn: 0
    },
    network: '',
    requestFromFaucet: () => {
        /* empty */
    },
    unlockAccounts: () => {
        /* empty */
    },
    loginMetamask: () => {
        /* empty */
    },
    loginZeroWallet: () => {
        /* empty */
    },
    message: ''
})
