from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd


def connect_to(chain):
    if chain == 'source':  # The source contract chain is avax
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'destination':  # The destination contract chain is bsc
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['source','destination']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract_info(chain, contract_info):
    """
        Load the contract_info file into a dictionary
        This function is used by the autograder and will likely be useful to you
    """
    try:
        with open(contract_info, 'r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( f"Failed to read contract info\nPlease contact your instructor\n{e}" )
        return 0
    return contracts[chain]

def scan_blocks(chain, contract_info="contract_info.json"):

    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return 0

    # load config
    contracts = get_contract_info(chain, contract_info)

    w3 = connect_to(chain)

    source = get_contract_info("source", contract_info)
    dest = get_contract_info("destination", contract_info)

    source_contract = connect_to("source").eth.contract(
        address=source["address"],
        abi=source["abi"]
    )

    dest_contract = connect_to("destination").eth.contract(
        address=dest["address"],
        abi=dest["abi"]
    )

    latest_block = w3.eth.block_number
    start_block = max(0, latest_block - 5)

    rows = []

    # =========================
    # SOURCE CHAIN (AVALANCHE)
    # =========================
    if chain == "source":

        events = source_contract.events.Deposit.get_logs(
            from_block=start_block,
            to_block=latest_block
        )

        for event in events:
            token = event["args"]["token"]
            recipient = event["args"]["recipient"]
            amount = event["args"]["amount"]

            print(f"[SOURCE] Deposit detected: {token}, {recipient}, {amount}")

            # CALL DESTINATION wrap()
            tx = dest_contract.functions.wrap(
                token,
                recipient,
                amount
            ).build_transaction({
                "from": w3.eth.accounts[0],
                "nonce": w3.eth.get_transaction_count(w3.eth.accounts[0]),
                "gas": 3000000,
                "gasPrice": w3.eth.gas_price
            })

            signed_tx = w3.eth.account.sign_transaction(tx, private_key="YOUR_PRIVATE_KEY")
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            print(f"[DEST] wrap() sent: {tx_hash.hex()}")

    # =========================
    # DESTINATION CHAIN (BNB)
    # =========================
    elif chain == "destination":

        events = dest_contract.events.Unwrap.get_logs(
            from_block=start_block,
            to_block=latest_block
        )

        for event in events:
            token = event["args"]["underlying_token"]
            recipient = event["args"]["to"]
            amount = event["args"]["amount"]

            print(f"[DEST] Unwrap detected: {token}, {recipient}, {amount}")

            # CALL SOURCE withdraw()
            tx = source_contract.functions.withdraw(
                token,
                recipient,
                amount
            ).build_transaction({
                "from": w3.eth.accounts[0],
                "nonce": w3.eth.get_transaction_count(w3.eth.accounts[0]),
                "gas": 3000000,
                "gasPrice": w3.eth.gas_price
            })

            signed_tx = w3.eth.account.sign_transaction(tx, private_key="YOUR_PRIVATE_KEY")
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            print(f"[SOURCE] withdraw() sent: {tx_hash.hex()}")
