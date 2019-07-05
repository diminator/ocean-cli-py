import React, { PureComponent } from 'react'
import Account from '../../atoms/Account'
import { User } from '../../../context'
import styles from './Popover.module.scss'

export default class Popover extends PureComponent {
    render() {
        const {
            account,
            balance,
            network,
            isWeb3,
            isOceanNetwork
        } = this.context

        return (
            <div
                className={styles.popover}
                ref={this.props.forwardedRef}
                style={this.props.style}
            >
                {!isWeb3 ? (
                    <div className={styles.popoverInfoline}>
                        No Web3 detected. Use a browser with MetaMask installed
                        to publish assets.
                    </div>
                ) : (
                    <>
                        <div className={styles.popoverInfoline}>
                            <Account account={account} />
                        </div>

                        {account && balance && (
                            <div className={styles.popoverInfoline}>
                                <span
                                    className={styles.balance}
                                    title={(balance.eth / 1e18).toFixed(10)}
                                >
                                    <strong>
                                        {(balance.eth / 1e18)
                                            .toFixed(3)
                                            .slice(0, -1)}
                                    </strong>{' '}
                                    ETH
                                </span>
                                <span className={styles.balance}>
                                    <strong>{balance.ocn}</strong> OCEAN
                                </span>
                            </div>
                        )}

                        <div className={styles.popoverInfoline}>
                            {network && !isOceanNetwork
                                ? 'Please connect to Custom RPC\n https://pacific.oceanprotocol.com'
                                : network && `Connected to ${network} network`}
                        </div>
                    </>
                )}
            </div>
        )
    }
}

Popover.contextType = User
