import React from 'react'
import Content from '../atoms/Content'
import styles from './Route.module.scss'
import Markdown from '../atoms/Markdown'


const Route = ({
    title,
    description,
    image,
    wide,
    children,
    className
}) => {
    // Strip HTML from passed title
    const titleSanitized = title.replace(/(<([^>]+)>)/gi, '')

    return (
        <div className={className}>

            <article>
                <header className={styles.header}>
                    <Content wide={wide}>
                        <h1 className={styles.title}>{titleSanitized}</h1>

                        {image && image}

                        {description && (
                            <Markdown
                                text={description}
                                className={styles.description}
                            />
                        )}
                    </Content>
                </header>

                {children}
            </article>
        </div>
    )
}

export default Route
