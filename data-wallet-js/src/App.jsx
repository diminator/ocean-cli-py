import React, { Component } from 'react'
import { BrowserRouter as Router } from 'react-router-dom'
import Spinner from "./components/atoms/Spinner";
import Header from "./components/organisms/Header";
import Footer from "./components/organisms/Footer";
import { User } from "./context";
import Routes from "./Routes"
import './styles/global.scss'
import styles from './App.module.scss'
import Login from "./routes/Login";

export default class App extends Component {
    static contextType = User

    render() {
        return (
            <div className="App">
                <Router>

                    <Header />

                        <main className={styles.main}>
                            {   this.context.isLoading ? (
                                    <div className={styles.loader}>
                                        <Spinner message="Loading" />
                                    </div>
                                ) : !this.context.isWeb3 ? (
                                    <Login />
                                ) : (
                                    <Routes />
                                )
                            }
                        </main>

                        <Footer />
                </Router>
            </div>
        );
    }
}
