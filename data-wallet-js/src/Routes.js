import React from 'react'
import { Route, Switch } from 'react-router-dom'

import Consume from './routes/Consume'
import NotFound from './routes/NotFound'
import { Faucet } from "./routes/Faucet";
import About from "./routes/About";

const Routes = () => (
    <Switch>
        <Route component={Consume} exact path="/" />
        <Route component={Faucet} path="/faucet" />
        <Route component={About} path="/about" />
        <Route component={NotFound} />
    </Switch>
)

export default Routes