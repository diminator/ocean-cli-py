#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import os
from os.path import join

from setuptools import setup

# Installed by pip install squid-py
# or pip install -e .
install_requirements = [
    'jupyter==1.0.0',
    'autopep8==1.4.4',  # nbextensions
    'pandas==0.24.2',
    'folium==0.9.1',
    'Flask==1.0.3',
    'Flask-Cors==3.0.8',
    'docker==4.0.2',
    'Click==7.0',
    'jupytext==1.1.6',
    'google-auth==1.6.3',
    'google-auth-httplib2==0.0.3',
    'google-auth-oauthlib==0.4.0',
    'google-api-python-client==1.7.9',
    'squid-py==0.6.13',
    # web3 requires eth-abi, requests, and more,
    # so those will be installed too.
    # See https://github.com/ethereum/web3.py/blob/master/setup.py
]

# Required to run setup.py:
setup_requirements = ['pytest-runner', ]

test_requirements = [
    'codacy-coverage',
    'coverage',
    'docker',
    'mccabe',
    'pylint',
    'pytest',
    'pytest-watch',
    'tox',
]

# Possibly required by developers of squid-py:
dev_requirements = [
    'bumpversion',
    'pkginfo',
    'twine',
    'watchdog',
]

docs_requirements = [
    'Sphinx',
    'sphinxcontrib-apidoc',
]

packages = []
for d, _, _ in os.walk('ocean_cli'):
    if os.path.exists(join(d, '__init__.py')):
        packages.append(d.replace(os.path.sep, '.'))

setup(
    author="leucothia",
    author_email='devops@oceanprotocol.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
    ],
    description="🐳 Ocean Command Line Interface in Python.",
    extras_require={
        'test': test_requirements,
        'dev': dev_requirements + test_requirements + docs_requirements,
        'docs': docs_requirements,
    },
    install_requires=install_requirements,
    license="Apache Software License 2.0",
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords='ocean-cli',
    name='ocean-cli',
    packages=packages,
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/oceanprotocol/ocean-cli-py',
    version='0.0.1',
    zip_safe=False,
    entry_points='''
        [console_scripts]
        ocean=ocean_cli.ocean:ocean
    ''',
)
