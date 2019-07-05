//
// commons-server connection
//
export const serviceUri =
    process.env.REACT_APP_SERVICE_URI || 'http://localhost:4000'

//
// OCEAN REMOTE CONNECTIONS
//
export const nodeUri =
    process.env.REACT_APP_NODE_URI || 'http://127.0.0.1:8545'
export const aquariusUri =
    process.env.REACT_APP_AQUARIUS_URI || 'http://localhost:5000'
export const brizoUri =
    process.env.REACT_APP_BRIZO_URI || 'http://localhost:8030'
export const brizoAddress =
    process.env.REACT_APP_BRIZO_ADDRESS ||
    '0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e'
export const secretStoreUri =
    process.env.REACT_APP_SECRET_STORE_URI ||
    'http://127.0.0.1:12001'
export const faucetUri =
    process.env.REACT_APP_FAUCET_URI || 'https://faucet.nile.dev-ocean.com'

//
// APP CONFIG
//
export const verbose = true
