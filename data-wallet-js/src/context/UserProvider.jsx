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
        await this.loadOcean(metamaskProvider)
    }

    loginZeroWallet = async () => {
        const zerowalletProvider = new ZeroWalletProvider()
        await zerowalletProvider.createLogin()
        localStorage.setItem('logType', 'ZeroWallet')
        await this.loadOcean(zerowalletProvider)
    }

    loadOcean = async (provider) => {
        const { ocean } = await provideOcean(provider.getProvider())
        console.log(await ocean.accounts.list())
        this.setState({ocean})
        const web3 = provider.getProvider()
        this.setState(
        {
            isLogged: true,
            isWeb3: true,
            web3
        })
        this.setState({isLoading: true})
        this.initNetworkPoll()
        this.initAccountsPoll()
        await this.fetchNetwork()
        await this.fetchAccounts()
        this.setState({isLoading: false})
    }

    bootstrap = async () => {
        const logType = localStorage.getItem('logType')
        switch (logType) {
            case 'Metamask':
                const metamaskProvider = new MetamaskProvider()
                if (
                    (await metamaskProvider.isAvaliable()) &&
                    (await metamaskProvider.isLogged())
                ) {
                    await this.loadOcean(metamaskProvider)
                } else {
                    console.log('metamaske not available or logged in')
                }
                break
            case 'ZeroWallet':
                const zerowalletProvider = new ZeroWalletProvider()
                if (await zerowalletProvider.isLogged()) {
                    await zerowalletProvider.restoreStoredLogin()
                    await this.loadOcean(zerowalletProvider)
                } else {
                    console.log('zerowallet not available or logged in')
                }
                break
            default:
                break
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
