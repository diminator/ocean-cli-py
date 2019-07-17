import React, { PureComponent } from 'react'
import { Account } from '@oceanprotocol/squid'
import save from "save-file"
import queryString from "querystring"
import Button from '../components/atoms/Button'
import Spinner from '../components/atoms/Spinner'
import { User } from '../context'
import styles from './Consume.module.scss'
import Route from "../components/templates/Route";
import Content from "../components/atoms/Content";


export default class Consume extends PureComponent {
    static contextType = User

    state = {
        didValue: undefined,
        ddoValue: {},
        message: undefined,
        isLoading: false,
        success: undefined,
        error: undefined,
        trxHash: undefined
    }

    componentDidMount = async () => {
        let did = queryString.parse(this.props.location.search.replace(/^\?/i, '')).did
        if (!did && this.context.did) {
            did = this.context.did
        }
        this.setState({didValue: did})
        await this.setDDO(did)
    }

    hasPermission = async (did) => {
        const { ocean, account } = this.context
        return ocean.keeper.conditions.accessSecretStoreCondition
            .checkPermissions(account, did, account)
    }

    prepareUrl = async (did) => {
        const agreementId = 'agreementIdBla'
        const { ocean, account, ddo } = this.context

        const { serviceEndpoint } = ddo.findServiceByType("Access")
        const agreementIdSignature = await ocean.utils.signature
            .signText(agreementId, account)
        let consumeUrl = serviceEndpoint
        consumeUrl += `?did=${did}`
        consumeUrl += `&consumerAddress=${account}`
        consumeUrl += `&agreementId=${agreementId}`
        consumeUrl += `&agreementIdSignature=${agreementIdSignature}`
        return consumeUrl
    }

    consume = async () => {
        this.setState({ isLoading: true })
        const { ocean, account, did, ddo } = this.context
        const messages = [
            'Creating Agreement',
            'Agreement Created',
            'Locking Payment',
            'Payment Locked',
        ]
        if (!(await this.hasPermission(did))){
            console.log('No permission, ordering')
            try {
                await ocean.assets
                    .order(
                        did,
                        ddo.findServiceByType('Access').serviceDefinitionId,
                        new Account(account))
                    .next(step => this.setState({
                            message: messages[step]
                        }))

            } catch (e) {
                this.setState({
                    error: `Could not order asset. Message: ${e}`,
                        isLoading: false
                    })
                return false
            }
        }
        console.log('Preparing URL')
        const consumeUrl = await this.prepareUrl(did)
        try {
            this.setState({
                message: "Consuming asset"
            })
            const response = await ocean.utils.fetch
                .get(consumeUrl, {
                    method: "GET",
                    headers: {
                        "Content-type": "application/json",
                    }
                })

            await save(await response.arrayBuffer(), 'test2.html')
            console.log('downloaded')

            this.setState({
                success: 'Successful download',
                isLoading: false
            })

        } catch (e) {
            this.setState({
                error: `Could not access service. Message: ${e.statusText}`,
                isLoading: false
            })
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
                {this.state.trxHash && (
                    <p>
                        <strong>Your Transaction Hash</strong>

                        <a href={submarineLink}>
                            <code>{trxHash}</code>
                        </a>
                    </p>
                )}
            </div>
        )
    }

    Error = () => (
        <div className={styles.error}>
            <p>{this.state.error}</p>
            <Button onClick={() => this.reset()}>Try again</Button>
        </div>
    )

    Action = () => {
        const { ddo } = this.context
        let price = null
        let validDDO = false
        if (ddo && ddo.service) {
            validDDO = true
            price = (parseInt(ddo.service[0].metadata.base.price)/1e18)
                .toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                })
        }
        return (
            <>
                <Button
                    primary
                    onClick={this.consume}
                    disabled={
                        !this.context.isLogged
                        || !this.context.isOceanNetwork
                        || !validDDO
                    }
                >
                    Consume DID {price && `(${price} OCEAN)`}
                </Button>
            </>
        )
    }

    setDDO = async (did) => {
        const { ocean } = this.context
        try {
            const ddo = await ocean.assets.resolve(did)
            if (ddo) {
                this.context.did = did
                this.context.ddo = ddo
                this.setState({ddoValue:ddo})
            }
            return ddo
        } catch (e) {
            return null
        }
    }

    handleChange = async (event) => {
        const didValue = event.target.value
        this.setState({didValue});
        await this.setDDO(didValue)
        this.reset()
    }

    render() {
        const { isWeb3, ddo } = this.context
        const { isLoading, error, success } = this.state

        return (
            <Route
                title="Consume Service"
                description="Get loaded with services on Ocean's Pacific network."
            >
                <Content>
                    <div className={styles.action}>
                        <input type="text"
                               className={styles.input}
                               value={this.state.didValue}
                               onChange={e => this.handleChange(e)} />

                        {isLoading ? (
                            <Spinner message={this.state.message} />
                        ) : error ? (
                            <this.Error />
                        ) : success ? (
                            <this.Success />
                        ) : (
                            isWeb3 && <this.Action />
                        )}
                    </div>
                </Content>
                <Content>
                    <div className={styles.ddoBox}>
                        <pre>
                            { `${JSON.stringify(ddo, undefined, 2)}` }
                        </pre>
                    </div>
                </Content>
            </Route>
        )
    }
}
