import React, { PureComponent } from 'react'
import { Account, utils } from '@oceanprotocol/squid'
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
        did: null,
        ddo: {},
        isLoading: false,
        success: undefined,
        error: undefined,
        trxHash: undefined
    }

    componentDidMount = async () => {
        const did = queryString.parse(this.props.location.search.replace(/^\?/i, '')).did
        const ddo = await this.fetchDDO(did)
        if (ddo) {
            this.setState({did, ddo})
        }
    }

    hasPermission = async (did) => {
        const { ocean, account } = this.context
        return ocean.keeper.conditions.accessSecretStoreCondition
            .checkPermissions(account, did, account)
    }

    authorize = async (did) => {
        this.setState({ isLoading: true })
        const { ocean, account } = this.context

        try {
            const consumer = new Account(account)
            const ddo = await ocean.assets.resolve(did)
            console.log(ddo)
            const templateName = ddo.findServiceByType("Access")
                .serviceAgreementTemplate.contractName
            const template = ocean.keeper.getTemplateByName(templateName)

            const agreementId = utils.zeroX(utils.generateId())

            const paymentFlow = new Promise(async (resolve, reject) => {
                console.log("Waiting for agreement", agreementId)
                await template.getAgreementCreatedEvent(agreementId).once()

                console.log("Agreement initialized")

                const {metadata} = ddo.findServiceByType("Metadata")

                console.log("Locking payment")

                const paid = await ocean.agreements.conditions
                    .lockReward(
                        agreementId,
                        metadata.base.price,
                        consumer
                    )

                if (paid) {
                    console.log("Payment was OK")
                } else {
                    console.error("Payment was KO")
                    console.error("Agreement ID: ", agreementId)
                    console.error("DID: ", ddo.id)
                    reject("Error on payment")
                }
                resolve()
            })

            await ocean.agreements.create(
                did,
                agreementId,
                ddo.findServiceByType('Access').serviceDefinitionId,
                "",
                consumer,
                consumer
            )

            await paymentFlow

            this.setState({
                isLoading: false,
            })

        } catch (error) {
            this.setState({
                isLoading: false,
                error: error.message })
        }
    }

    prepareUrl = async (did) => {
        const agreementId = 'agreementIdBla'
        const { ocean, account } = this.context

        const { serviceEndpoint } = this.state.ddo
            .findServiceByType("Access")
        const agreementIdSignature = await ocean.utils.signature
            .signText(agreementId, account)
        let consumeUrl = serviceEndpoint
        consumeUrl += `?did=${did}`
        consumeUrl += `&consumerAddress=${account}`
        consumeUrl += `&agreementId=${agreementId}`
        consumeUrl += `&agreementIdSignature=${agreementIdSignature}`
        return consumeUrl
    }

    consume = async (did) => {
        this.setState({ isLoading: true })
        const { ocean } = this.context
        if (!(await this.hasPermission(did))){
            console.log('No permission, authorizing')
            await this.authorize(did)
        }
        console.log('Preparing URL')
        const consumeUrl = await this.prepareUrl(did)
        try {
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
                <p>
                    <strong>Your Transaction Hash</strong>

                    <a href={submarineLink}>
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

    Action = () => (
        <>
            <Button
                primary
                onClick={() => this.consume(this.state.did)}
                disabled={
                    !this.context.isLogged || !this.context.isOceanNetwork
                }
            >
                Consume DID
            </Button>
        </>
    )

    fetchDDO = async (did) => {
        const { ocean } = this.context
        try {
            const ddo = await ocean.assets.resolve(did)
            return ddo
        } catch (e) {
            return null
        }
    }

    handleChange = async (event) => {
        const did = event.target.value
        this.setState({did});
        const ddo = await this.fetchDDO(did)
        this.setState({ddo})
        this.reset()
    }

    render() {
        const { isWeb3 } = this.context
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
                               value={this.state.did}
                               onChange={e => this.handleChange(e)} />

                        {isLoading ? (
                            <Spinner message="Authorizing ..." />
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
                    <pre>
                        { `${JSON.stringify(this.state.ddo, undefined, 2)}` }
                    </pre>
                </Content>
            </Route>
        )
    }
}
