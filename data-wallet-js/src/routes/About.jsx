import React, { Component } from 'react'
import Route from '../components/templates/Route'
import Content from '../components/atoms/Content'

class About extends Component {
    render() {
        return (
            <Route
                title="About"
                description="A wallet to consume services on the Ocean Network."
            >
                <Content>
                    <p>
                        Simple tool to
                    </p>

                    <ul>
                        <li>
                            <a href="https://blog.oceanprotocol.com/">
                                Read the blog post →
                            </a>
                        </li>
                        <li>
                            <a href="https://github.com/oceanprotocol">
                                Check out oceanprotocol on GitHub →
                            </a>
                        </li>
                    </ul>
                </Content>
            </Route>
        )
    }
}

export default About
