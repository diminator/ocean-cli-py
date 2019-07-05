import React from 'react'
import Dotdotdot from 'react-dotdotdot'
import styles from './Account.module.scss'

const Account = ({ account }) => {
    return account ? (
        <div className={styles.account}>
            <Dotdotdot clamp={2}>{account}</Dotdotdot>
        </div>
    ) : (
        <em>No account selected</em>
    )
}

export default Account
