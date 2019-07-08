import React, { Component } from 'react'
import Route from "../components/templates/Route";
import Content from "../components/atoms/Content";
import { User } from "../context";
import Button from "../components/atoms/Button";
import styles from './Login.module.scss'

class Login extends Component {
    static contextType = User

    render() {
        return (
            <Route title="Log In to Web3">
                <Content>
                    <div className={styles.container}>
                        <Button primary onClick={this.context.loginMetamask}>Metamask</Button>
                        <Button primary onClick={this.context.loginZeroWallet}>Burner</Button>
                    </div>
                </Content>
            </Route>
        )
    }
}

export default Login
