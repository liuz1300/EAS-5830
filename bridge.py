from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json
import time

PRIVATE_KEY = "d475ca0cd9c3e620b888ec34fb6a954439958230bbb0cdc44356e7b8a34e6f50"
ACCOUNT = Web3.to_checksum_address("0xbA52AeFe6Cb8da87dfc0F60E3A916f957060e491")

SOURCE_CHAIN = "avax"
DEST_CHAIN = "bsc"

SOURCE_ADDRESS = Web3.to_checksum_address("0x1f6DEeEFA8C78f71b00580Eadbd7ff531a993531")
DEST_ADDRESS = Web3.to_checksum_address("0x4A5aC4b01AcB4F708FeCf15b7840057763952D18")

RPCS = {
    "avax": "https://api.avax-test.network/ext/bc/C/rpc",
    "bsc": "https://data-seed-prebsc-1-s1.binance.org:8545/"
}

def get_w3(chain):
    w3 = Web3(Web3.HTTPProvider(RPCS[chain]))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


# ===== LOAD FULL ABI =====
with open("contracts.json") as f:
    data = json.load(f)

SOURCE_ABI = data["source"]["abi"]
DEST_ABI = data["destination"]["abi"]


def send_tx(w3, function):
    nonce = w3.eth.get_transaction_count(ACCOUNT)

    tx = function.build_transaction({
        "from": ACCOUNT,
        "nonce": nonce,
        "gas": 300000,
        "gasPrice": w3.to_wei("5", "gwei")
    })

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

    print("TX SENT:", tx_hash.hex())


# ===== HANDLERS =====

def handle_deposit(event):
    print("Deposit detected")

    token = event["args"]["token"]
    recipient = event["args"]["recipient"]
    amount = int(event["args"]["amount"])

    w3 = get_w3(DEST_CHAIN)
    contract = w3.eth.contract(address=DEST_ADDRESS, abi=DEST_ABI)

    tx = contract.functions.wrap(token, recipient, amount)
    send_tx(w3, tx)


def handle_unwrap(event):
    print("Unwrap detected")

    token = event["args"]["underlying_token"]
    recipient = event["args"]["to"]
    amount = int(event["args"]["amount"])

    w3 = get_w3(SOURCE_CHAIN)
    contract = w3.eth.contract(address=SOURCE_ADDRESS, abi=SOURCE_ABI)

    tx = contract.functions.withdraw(token, recipient, amount)
    send_tx(w3, tx)


# ===== MAIN LISTENER =====

def listen():
    w3_source = get_w3(SOURCE_CHAIN)
    w3_dest = get_w3(DEST_CHAIN)

    source_contract = w3_source.eth.contract(address=SOURCE_ADDRESS, abi=SOURCE_ABI)
    dest_contract = w3_dest.eth.contract(address=DEST_ADDRESS, abi=DEST_ABI)

    deposit_filter = source_contract.events.Deposit.create_filter(from_block="latest")
    unwrap_filter = dest_contract.events.Unwrap.create_filter(from_block="latest")

    print("Listening...")

    while True:
        for event in deposit_filter.get_new_entries():
            handle_deposit(event)

        for event in unwrap_filter.get_new_entries():
            handle_unwrap(event)

        time.sleep(5)


if __name__ == "__main__":
    listen()
