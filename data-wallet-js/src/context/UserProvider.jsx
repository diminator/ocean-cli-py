import React, { PureComponent } from 'react'
import Web3 from 'web3'
import { Logger } from '@oceanprotocol/squid'
import { User } from '.'
import { provideOcean, requestFromFaucet } from '../ocean'
import { MetamaskProvider } from './MetamaskProvider'
import { ZeroWalletProvider } from './ZeroWalletProvider'
import { nodeUri } from '../config'

const POLL_ACCOUNTS = 1000 // every 1s
const POLL_NETWORK = POLL_ACCOUNTS * 60 // every 1 min

export default class UserProvider extends PureComponent {
    unlockAccounts = async () => {
        try {
            await window.ethereum.enable()
        } catch (error) {
            // User denied account access...
            return null
        }
    }

    state = {
        isLogged: false,
        isLoading: true,
        isWeb3: false,
        isOceanNetwork: false,
        balance: {
            eth: 0,
            ocn: 0
        },
        network: '',
        web3: new Web3(new Web3.providers.HttpProvider(nodeUri)),
        account: '',
        ocean: {},
        requestFromFaucet: () => requestFromFaucet(''),
        unlockAccounts: () => this.unlockAccounts(),
        loginMetamask: () => this.loginMetamask(),
        loginZeroWallet: () => this.loginZeroWallet(),
        message: 'Connecting to Ocean...'
    }

    accountsInterval = null
    networkInterval = null

    async componentDidMount() {
        await this.bootstrap()

        this.initAccountsPoll()
        this.initNetworkPoll()
    }

    initAccountsPoll() {
        if (!this.accountsInterval) {
            this.accountsInterval = setInterval(
                this.fetchAccounts,
                POLL_ACCOUNTS
            )
        }
    }

    initNetworkPoll() {
        if (!this.networkInterval) {
            this.networkInterval = setInterval(this.fetchNetwork, POLL_NETWORK)
        }
    }

    getWeb3 = () => {
        // Modern dapp browsers
        if (window.ethereum) {
            window.web3 = new Web3(window.ethereum)
            return window.web3
        }
        // Legacy dapp browsers
        else if (window.web3) {
            window.web3 = new Web3(window.web3.currentProvider)
            return window.web3
        }
        // Non-dapp browsers
        else {
            return null
        }
    }

    loginMetamask = async () => {
        const metamaskProvider = new MetamaskProvider()
        await metamaskProvider.startLogin()
        localStorage.setItem('logType', 'Metamask')
        const web3 = metamaskProvider.getProvider()
        this.setState(
            {
                isLogged: true,
                web3
            },
            () => {
                this.loadOcean()
            }
        )
    }

    loginZeroWallet = async () => {
        const zerowalletProvider = new ZeroWalletProvider()
        await zerowalletProvider.createLogin()
        localStorage.setItem('logType', 'ZeroWallet')
        const web3 = zerowalletProvider.getProvider()
        this.setState(
            {
                isLogged: true,
                web3
            },
            () => {
                this.loadOcean()
            }
        )
    }

    bootstrap = async () => {
        try {
            //
            // Start with Web3 detection only
            //
            this.setState({ message: 'Setting up Web3...' })
            let web3 = await this.getWeb3()

            web3
                ? this.setState({ isWeb3: true })
                : this.setState({ isWeb3: false })

            // Modern & legacy dapp browsers
            if (web3 && this.state.isWeb3) {
                //
                // Detecting network with window.web3
                //
                let isOceanNetwork

                await window.web3.eth.net.getId((err, netId) => {
                    if (err) return

                    const isPacific = netId === 0xcea11
                    const isNile = netId === 8995
                    const isDuero = netId === 2199
                    const isSpree = netId === 8996

                    isOceanNetwork = isPacific || isNile || isDuero || isSpree

                    const network = isPacific
                        ? 'Pacific'
                        : isNile
                        ? 'Nile'
                        : isDuero
                        ? 'Duero'
                        : isSpree
                        ? 'Spree'
                        : netId.toString()

                    if (
                        isOceanNetwork !== this.state.isOceanNetwork ||
                        network !== this.state.network
                    ) {
                        this.setState({
                            isOceanNetwork,
                            network,
                            message: `Network ${network} detected...`
                        })
                    }
                })

                if (!isOceanNetwork) {
                    web3 = this.state.web3 // eslint-disable-line
                }

                //
                // Provide the Ocean
                //
                this.setState({ message: 'Connecting to Ocean...' })

                const { ocean } = await provideOcean(web3)
                this.setState({ ocean, message: 'Getting accounts...' })

                // Get accounts
                await this.fetchAccounts()

                this.setState({ isLoading: false, message: '' })
            }
            // Non-dapp browsers
            else {
                this.setState({ message: 'Connecting to Ocean...' })
                const { ocean } = await provideOcean(this.state.web3)
                this.setState({ ocean, isLoading: false })

                this.fetchNetwork()
            }
        } catch (e) {
            // error in bootstrap process
            // show error connecting to ocean
            Logger.error('web3 error', e.message)
            this.setState({ isLoading: false })
        }
    }

    fetchAccounts = async () => {
        const { ocean, isWeb3, isLogged, isOceanNetwork } = this.state

        if (isWeb3) {
            let accounts

            // Modern dapp browsers
            if (window.ethereum && !isLogged && isOceanNetwork) {
                // simply set to empty, and have user click a button somewhere
                // to initiate account unlocking
                accounts = []

                // alternatively, automatically prompt for account unlocking
                // await this.unlockAccounts()
            }

            accounts = await ocean.accounts.list()

            if (accounts.length > 0) {
                const account = await accounts[0].getId()

                if (account !== this.state.account) {
                    this.setState({
                        account,
                        isLogged: true,
                        requestFromFaucet: () => requestFromFaucet(account)
                    })

                    await this.fetchBalance(accounts[0])
                }
            } else {
                !isLogged && this.setState({ isLogged: false, account: '' })
            }
        }
    }

    fetchBalance = async (account) => {
        const balance = await account.getBalance()
        const { eth, ocn } = balance
        if (eth !== this.state.balance.eth || ocn !== this.state.balance.ocn) {
            this.setState({ balance: { eth, ocn } })
        }
    }

    fetchNetwork = async () => {
        const { ocean, isWeb3 } = this.state

        if (isWeb3) {
            const network = await ocean.keeper.getNetworkName()
            const isPacific = network === 'Pacific'
            const isNile = network === 'Nile'
            const isDuero = network === 'Duero'
            const isSpree = network === 'Spree'
            const isOceanNetwork = isPacific || isNile || isDuero || isSpree

            network !== this.state.network &&
                this.setState({ isOceanNetwork, network })
        }
    }

    render() {
        return (
            <User.Provider value={this.state}>
                {this.props.children}
            </User.Provider>
        )
    }
}
