import React, { PureComponent } from 'react'
import { Manager, Reference, Popper } from 'react-popper'
import AccountPopover from './Popover'
import AccountIndicator from './Indicator'


export default class AccountStatus extends PureComponent {
    state = {
        isPopoverOpen: false
    }

    togglePopover() {
        this.setState(prevState => ({
            isPopoverOpen: !prevState.isPopoverOpen
        }))
    }

    render() {
        return (
            <Manager>
                <Reference>
                    {({ ref }) => (
                        <AccountIndicator
                            togglePopover={() => this.togglePopover()}
                            className={this.props.className}
                            forwardedRef={ref}
                        />
                    )}
                </Reference>
                {this.state.isPopoverOpen && (
                    <Popper placement="auto">
                        {({ ref, style, placement }) => (
                            <AccountPopover
                                forwardedRef={ref}
                                style={style}
                                data-placement={placement}
                            />
                        )}
                    </Popper>
                )}
            </Manager>
        )
    }
}
