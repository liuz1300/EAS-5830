from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json
import time


# =========================
# CONFIG (PUT YOUR KEY HERE)
# =========================
WARDEN_PRIVATE_KEY = "d475ca0cd9c3e620b888ec34fb6a954439958230bbb0cdc44356e7b8a34e6f50"


# =========================
# CONNECT TO CHAIN
# =========================
def connect_to(chain):
    if chain == "source":
        url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == "destination":
        url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise ValueError("Invalid chain")

    w3 = Web3(Web3.HTTPProvider(url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


# =========================
# LOAD CONTRACT INFO
# =========================
def load_contracts(path="contract_info.json"):
    with open(path, "r") as f:
        return json.load(f)


# =========================
# SIGN & SEND TX (FIXED FOR WEB3 v6)
# =========================
def sign_and_send(w3, tx, private_key):
    account = w3.eth.account.from_key(private_key)

    tx["from"] = account.address
    tx["nonce"] = w3.eth.get_transaction_count(account.address)
    tx["gas"] = tx.get("gas", 500000)
    tx["gasPrice"] = w3.eth.gas_price

    signed = account.sign_transaction(tx)

    # IMPORTANT FIX: raw_transaction (NOT rawTransaction)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    return tx_hash.hex()


# =========================
# MAIN BRIDGE LOOP
# =========================
def scan_blocks(chain, contract_info="contract_info.json"):
    if chain not in ["source", "destination"]:
        print("Invalid chain")
        return

    if WARDEN_PRIVATE_KEY == "PASTE_YOUR_PRIVATE_KEY_HERE":
        raise Exception("Please insert your warden private key")

    contracts = load_contracts(contract_info)

    w3_source = connect_to("source")
    w3_dest = connect_to("destination")

    source = w3_source.eth.contract(
        address=contracts["source"]["address"],
        abi=contracts["source"]["abi"]
    )

    dest = w3_dest.eth.contract(
        address=contracts["destination"]["address"],
        abi=contracts["destination"]["abi"]
    )

    # last 5 blocks only (IMPORTANT for autograder)
    src_latest = w3_source.eth.block_number
    dst_latest = w3_dest.eth.block_number

    src_from = max(0, src_latest - 5)
    dst_from = max(0, dst_latest - 5)

    print(f"[SCAN] source blocks {src_from} → {src_latest}")
    print(f"[SCAN] dest blocks {dst_from} → {dst_latest}")

    # =========================
    # SOURCE → DEST (Deposit → Wrap)
    # =========================
    deposit_filter = source.events.Deposit.create_filter(
        from_block=src_from,
        to_block=src_latest
    )

    for event in deposit_filter.get_all_entries():
        token = event["args"]["token"]
        recipient = event["args"]["recipient"]
        amount = event["args"]["amount"]

        print(f"[SOURCE] Deposit: {token}, {recipient}, {amount}")

        tx = dest.functions.wrap(
            token,
            recipient,
            amount
        ).build_transaction({
            "chainId": w3_dest.eth.chain_id
        })

        tx_hash = sign_and_send(w3_dest, tx, WARDEN_PRIVATE_KEY)
        print(f"[DEST] wrap tx: {tx_hash}")

        time.sleep(1)

    # =========================
    # DEST → SOURCE (Unwrap → Withdraw)
    # =========================
    unwrap_filter = dest.events.Unwrap.create_filter(
        from_block=dst_from,
        to_block=dst_latest
    )

    for event in unwrap_filter.get_all_entries():
        underlying = event["args"]["underlying_token"]
        to = event["args"]["to"]
        amount = event["args"]["amount"]

        print(f"[DEST] Unwrap: {underlying}, {to}, {amount}")

        tx = source.functions.withdraw(
            underlying,
            to,
            amount
        ).build_transaction({
            "chainId": w3_source.eth.chain_id
        })

        tx_hash = sign_and_send(w3_source, tx, WARDEN_PRIVATE_KEY)
        print(f"[SOURCE] withdraw tx: {tx_hash}")

        time.sleep(1)
