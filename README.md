# Ocean Command Line Interface (Python)

> CLI tool for Ocean Protocol
> [oceanprotocol.com](https://oceanprotocol.com)

---

**🐲🦑 THERE BE DRAGONS AND SQUIDS. This is in alpha state and you can expect running into problems. If you run into them, please open up [a new issue](https://github.com/oceanprotocol/tuna/issues). 🦑🐲**

---

## Table of Contents

  - [Get started](#get-started)
  - [License](#license)

---

## Get started

### Setup
> The setup assumes either running a local network or setup a configuration file
for connecting to Nile, Duero, ...


## Compatibility

- keeper-contracts: `v0.9.7`
- brizo: `>0.3.7`

```bash
virtualenv venv -p python3
source venv/bin/activate
python setup.py install
```

### Usage

We're assuming user config files:
- Default: `config.ini`
- Alice: `alice.ini`
- Bob: `bob.ini`

```bash
## basics
> ocean --help

## accounts and tokens
> ocean accounts list
> ocean accounts balance
# switch accounts
> ocean -c <config.ini> accounts balance
> ocean -c alice.ini accounts balance
> ocean -c alice.ini tokens request <amount>
> ocean -c alice.ini tokens transfer <amount> <public key>

## publish / consume
# publish from metadata
> ocean -c bob.ini assets create <data/metadata.json>
  did: <did:op:123...ABC>

# 
> ocean -c alice.ini assets consume <did:op:123...ABC>
> ls consume-downloads
 <list of files>

```



## License

```
Copyright 2018 Ocean Protocol Foundation Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
