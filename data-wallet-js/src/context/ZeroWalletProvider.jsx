import Web3 from 'web3'
import { nodeUri } from '../config'
import bip39 from 'bip39'


const HDWalletProvider = require('truffle-hdwallet-provider')

export class ZeroWalletProvider {
    web3

    constructor() {
        // Default
        this.web3 = null
    }

    async isLogged() {
        if (localStorage.getItem('seedphrase') !== null) {
            return true
        }
        return false
    }

    async restoreStoredLogin() {
        const mnemonic = localStorage.getItem('seedphrase')
        localStorage.setItem('seedphrase', mnemonic)
        const provider = new HDWalletProvider(mnemonic, nodeUri, 0, 1);
        this.web3 = new Web3(provider)
    }

    async createLogin() {
        const mnemonic = bip39.generateMnemonic()
        localStorage.setItem('seedphrase', mnemonic)
        const provider = new HDWalletProvider(mnemonic, nodeUri, 0, 1);
        this.web3 = new Web3(provider)
    }

    async restoreLogin(mnemonic) {
        localStorage.setItem('seedphrase', mnemonic)
        const provider = new HDWalletProvider(mnemonic, nodeUri, 0, 1);
        this.web3 = new Web3(provider)
    }

    getProvider() {
        return this.web3
    }
}