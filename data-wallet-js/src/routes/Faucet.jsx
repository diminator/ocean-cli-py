import React, { PureComponent } from 'react'
import Route from '../components/templates/Route'
import Button from '../components/atoms/Button'
import Spinner from '../components/atoms/Spinner'
import { User } from '../context'
import Web3message from '../components/organisms/Web3message'
import styles from './Faucet.module.scss'
import Content from '../components/atoms/Content'


class Web3Action extends PureComponent {
    static contextType = User

    state = {
        isLoading: false,
        success: undefined,
        error: undefined,
        trxHash: undefined
    }

    getTokens = async (
        requestFromFaucet
    ) => {
        this.setState({ isLoading: true })

        try {
            const response = await requestFromFaucet()

            if (!response.success) {
                this.setState({
                    isLoading: false,
                    error: response.message
                })
                return
            }

            const { trxHash } = response

            this.setState({
                isLoading: false,
                success: response.message,
                trxHash
            })
        } catch (error) {
            this.setState({ isLoading: false, error: error.message })
        }
    }

    reset = () => {
        this.setState({
            error: undefined,
            success: undefined,
            isLoading: false
        })
    }

    Success = () => {
        const { network } = this.context
        const { trxHash } = this.state

        const submarineLink = `https://submarine${
            network === 'Duero'
                ? '.duero'
                : network === 'Nile'
                ? '.nile'
                : network === 'Pacific'
                ? '.pacific'
                : ''
        }.dev-ocean.com/tx/${trxHash}`

        return (
            <div className={styles.success}>
                <strong>{this.state.success}</strong>
                <p>
                    <strong>Your Transaction Hash</strong>

                    <a href={submarineLink} target="_blank">
                        <code>{trxHash}</code>
                    </a>
                </p>
            </div>
        )
    }

    Error = () => (
        <div className={styles.error}>
            <p>{this.state.error}</p>
            <Button onClick={() => this.reset()}>Try again</Button>
        </div>
    )
}

class EtherFaucet extends Web3Action {
    Action = () => (
        <>
            <Button
                primary
                onClick={() => this.getTokens(this.context.requestFromFaucet)}
                disabled={
                    !this.context.isLogged || !this.context.isOceanNetwork
                }
            >
                Request Ether
            </Button>
            <p>
                You can only request Ether once every 24 hours for your address.
            </p>
        </>
    )

    render() {
        const { isWeb3 } = this.context
        const { isLoading, error, success } = this.state

        return (
            <div className={styles.action}>
                {isLoading ? (
                    <Spinner message="Getting Ether..." />
                ) : error ? (
                    <this.Error />
                ) : success ? (
                    <this.Success />
                ) : (
                    isWeb3 && <this.Action />
                )}
            </div>
        )
    }
}


class OceanFaucet extends Web3Action {
    Action = () => (
        <>
            <Button
                primary
                onClick={() => this.getTokens(this.context.requestOcean)}
                disabled={
                    !this.context.isLogged || !this.context.isOceanNetwork
                }
            >
                Request OCEAN
            </Button>
            <p>
                You can request as many OCEAN as you want.
            </p>
        </>
    )

    render() {
        const { isWeb3 } = this.context
        const { isLoading, error, success } = this.state

        return (
            <div className={styles.action}>
                {isLoading ? (
                    <Spinner message="Getting OCEAN..." />
                ) : error ? (
                    <this.Error />
                ) : success ? (
                    <this.Success />
                ) : (
                    isWeb3 && <this.Action />
                )}
            </div>
        )
    }
}

export default class Faucet extends PureComponent{
    render() {
        return (
            <Route
                title="Faucet"
                description="Shower yourself with some Ether for Ocean's Pacific network."
            >
                <Content>
                    <Web3message />

                    <EtherFaucet />
                    <OceanFaucet />

                </Content>
            </Route>
        )
    }
}
