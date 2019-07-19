import React from 'react'
import cx from 'classnames'
import { User } from '../../../context'
import styles from './Indicator.module.scss'

const Indicator = ({
    className,
    togglePopover,
    forwardedRef
}) => (
    <div
        className={cx(styles.status, className)}
        onClick={togglePopover}
        onMouseOver={togglePopover}
        onMouseOut={togglePopover}
        ref={forwardedRef}
    >
        <User.Consumer>
            {states =>
                !states.isWeb3 ? (
                    <span className={styles.statusIndicator} />
                ) : !states.isLogged || !states.isOceanNetwork ? (
                    <span className={styles.statusIndicatorCloseEnough} />
                ) : states.isLogged ? (
                    <span className={styles.statusIndicatorActive} />
                ) : null
            }
        </User.Consumer>
    </div>
)

export default Indicator
