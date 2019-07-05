import React, { PureComponent } from 'react'
import Account from '../atoms/Account'
import Button from '../atoms/Button'
import AccountStatus from '../molecules/AccountStatus'
import styles from './Web3message.module.scss'
import { User } from '../../context'
import content from '../../data/web3message.json'

export default class Web3message extends PureComponent {
    message = (
        message,
        account,
        unlockAccounts
    ) => (
        <div className={styles.message}>
            {account ? (
                <Account account={account} />
            ) : (
                <div className={styles.warnings}>
                    <AccountStatus className={styles.status} />
                    <span dangerouslySetInnerHTML={{ __html: message }} />{' '}
                    {unlockAccounts && (
                        <Button onClick={() => unlockAccounts()} link>
                            Unlock Account
                        </Button>
                    )}
                </div>
            )}
        </div>
    )

    render() {
        const {
            isWeb3,
            isOceanNetwork,
            isLogged,
            account,
            unlockAccounts
        } = this.context

        return !isWeb3
            ? this.message(content.noweb3)
            : !isOceanNetwork
            ? this.message(content.wrongNetwork)
            : !isLogged
            ? this.message(content.noAccount, '', unlockAccounts)
            : isLogged
            ? this.message(content.hasAccount, account)
            : null
    }
}

Web3message.contextType = User
