from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from pathlib import Path
import json
import pandas as pd

# ---------------------------
# CONFIG HELPERS
# ---------------------------
PRIVATE_KEY = "d475ca0cd9c3e620b888ec34fb6a954439958230bbb0cdc44356e7b8a34e6f50"
def connect_to(chain):
    if chain == "source":
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == "destination":
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise ValueError("Invalid chain")

    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def A(w3, addr):
    """Checksum helper (IMPORTANT for Web3 v6)"""
    return w3.to_checksum_address(addr)


def get_contract_info(contract_info):
    with open(contract_info, "r") as f:
        return json.load(f)


# ---------------------------
# MAIN BRIDGE FUNCTION
# ---------------------------

def scan_blocks(chain, contract_info="contract_info.json"):
    if chain not in ["source", "destination"]:
        print(f"Invalid chain: {chain}")
        return 0

    info = get_contract_info(contract_info)

    w3_src = connect_to("source")
    w3_dst = connect_to("destination")

    src = w3_src.eth.contract(
        address=A(w3_src, info["source"]["address"]),
        abi=info["source"]["abi"]
    )

    dst = w3_dst.eth.contract(
        address=A(w3_dst, info["destination"]["address"]),
        abi=info["destination"]["abi"]
    )

    latest_src = w3_src.eth.block_number
    latest_dst = w3_dst.eth.block_number

    start_src = max(0, latest_src - 5)
    start_dst = max(0, latest_dst - 5)

    print(f"[SCAN] source blocks {start_src} → {latest_src}")
    print(f"[SCAN] dest blocks {start_dst} → {latest_dst}")

    # ---------------------------
    # SOURCE → DEST (Deposit → Wrap)
    # ---------------------------
    if chain == "source":
        events = src.events.Deposit.create_filter(
            from_block=start_src,
            to_block=latest_src
        ).get_all_entries()

        for ev in events:
            token = A(w3_dst, ev["args"]["token"])
            recipient = A(w3_dst, ev["args"]["recipient"])
            amount = int(ev["args"]["amount"])

            print(f"[SOURCE] Deposit: {token}, {recipient}, {amount}")

            try:
                tx = dst.functions.wrap(
                    token,
                    recipient,
                    amount
                ).build_transaction({
                    "from": w3_dst.eth.default_account,
                    "nonce": w3_dst.eth.get_transaction_count(w3_dst.eth.default_account),
                    "gas": 300000,
                    "gasPrice": w3_dst.eth.gas_price
                })

                signed = w3_dst.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                tx_hash = w3_dst.eth.send_raw_transaction(signed.rawTransaction)

                print(f"[DEST] wrap tx: {tx_hash.hex()}")

            except Exception as e:
                print("Wrap error:", e)

    # ---------------------------
    # DEST → SOURCE (Unwrap → Withdraw)
    # ---------------------------
    if chain == "destination":
        events = dst.events.Unwrap.create_filter(
            from_block=start_dst,
            to_block=latest_dst
        ).get_all_entries()

        for ev in events:
            underlying = A(w3_src, ev["args"]["underlying_token"])
            to = A(w3_src, ev["args"]["to"])
            amount = int(ev["args"]["amount"])

            print(f"[DEST] Unwrap: {underlying}, {to}, {amount}")

            try:
                tx = src.functions.withdraw(
                    underlying,
                    to,
                    amount
                ).build_transaction({
                    "from": w3_src.eth.default_account,
                    "nonce": w3_src.eth.get_transaction_count(w3_src.eth.default_account),
                    "gas": 300000,
                    "gasPrice": w3_src.eth.gas_price
                })

                signed = w3_src.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                tx_hash = w3_src.eth.send_raw_transaction(signed.rawTransaction)

                print(f"[SOURCE] withdraw tx: {tx_hash.hex()}")

            except Exception as e:
                print("Withdraw error:", e)
