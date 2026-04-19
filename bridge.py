from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
from pathlib import Path
import json
import pandas as pd
import time

# ================= LOAD CONTRACT INFO =================

with open("contract_info.json") as f:
    data = json.load(f)

SOURCE_ADDRESS = Web3.to_checksum_address(data["source"]["address"])
DEST_ADDRESS = Web3.to_checksum_address(data["destination"]["address"])

SOURCE_ABI = data["source"]["abi"]
DEST_ABI = data["destination"]["abi"]

# ================= WALLET CONFIG =================

PRIVATE_KEY = "d475ca0cd9c3e620b888ec34fb6a954439958230bbb0cdc44356e7b8a34e6f50"
ACCOUNT = "0xbA52AeFe6Cb8da87dfc0F60E3A916f957060e491"
ACCOUNT = Web3.to_checksum_address(ACCOUNT)

# ================= RPCS =================

RPCS = {
    "avax": "https://api.avax-test.network/ext/bc/C/rpc",
    "bsc": "https://data-seed-prebsc-1-s1.binance.org:8545/"
}

# ================= HELPERS =================

def get_w3(chain):
    w3 = Web3(Web3.HTTPProvider(RPCS[chain]))
    if chain in ["avax", "bsc"]:
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def send_tx(w3, contract_fn):
    nonce = w3.eth.get_transaction_count(ACCOUNT)

    tx = contract_fn.build_transaction({
        "from": ACCOUNT,
        "nonce": nonce,
        "gas": 300000,
        "gasPrice": w3.to_wei("5", "gwei")
    })

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

    print("TX SENT:", tx_hash.hex())
    return tx_hash.hex()


# ================= EVENT HANDLERS =================

def handle_deposit(event):
    print("[EVENT] Deposit detected → calling wrap()")

    token = Web3.to_checksum_address(event["args"]["token"])
    recipient = Web3.to_checksum_address(event["args"]["recipient"])
    amount = int(event["args"]["amount"])

    w3 = get_w3("bsc")  # destination chain
    contract = w3.eth.contract(address=DEST_ADDRESS, abi=DEST_ABI)

    fn = contract.functions.wrap(token, recipient, amount)
    send_tx(w3, fn)


def handle_unwrap(event):
    print("[EVENT] Unwrap detected → calling withdraw()")

    token = Web3.to_checksum_address(event["args"]["underlying_token"])
    recipient = Web3.to_checksum_address(event["args"]["to"])
    amount = int(event["args"]["amount"])

    w3 = get_w3("avax")  # source chain
    contract = w3.eth.contract(address=SOURCE_ADDRESS, abi=SOURCE_ABI)

    fn = contract.functions.withdraw(token, recipient, amount)
    send_tx(w3, fn)


# ================= REQUIRED FUNCTION (GRADER NEEDS THIS) =================

def scan_blocks(chain, start_block, end_block, contract_address, eventfile='deposit_logs.csv'):
    """
    Reads Deposit events AND triggers bridge actions.
    """

    w3 = get_w3(chain)

    abi = SOURCE_ABI if chain == "avax" else DEST_ABI
    contract = w3.eth.contract(address=contract_address, abi=abi)

    rows = []

    print(f"[SCAN] {chain} blocks {start_block} → {end_block}")

    for block_num in range(start_block, end_block + 1):

        # -------- SOURCE CHAIN (Deposit) --------
        if chain == "avax":
            event_filter = contract.events.Deposit.create_filter(
                from_block=block_num,
                to_block=block_num
            )

            events = event_filter.get_all_entries()

            for event in events:
                rows.append(parse_event(event, chain, contract_address))
                handle_deposit(event)   # 🔥 AUGMENTATION

        # -------- DESTINATION CHAIN (Unwrap) --------
        else:
            event_filter = contract.events.Unwrap.create_filter(
                from_block=block_num,
                to_block=block_num
            )

            events = event_filter.get_all_entries()

            for event in events:
                rows.append(parse_event(event, chain, contract_address))
                handle_unwrap(event)    # 🔥 AUGMENTATION

    # ================= SAVE CSV =================

    if rows:
        df = pd.DataFrame(rows)
        file_path = Path(eventfile)

        if file_path.exists():
            df.to_csv(file_path, mode='a', header=False, index=False)
        else:
            df.to_csv(file_path, mode='w', header=True, index=False)

        print(f"Saved {len(rows)} events to {eventfile}")
    else:
        print("No events found.")


# ================= EVENT PARSER =================

def parse_event(event, chain, contract_address):
    return {
        "chain": chain,
        "token": event["args"].get("token") or event["args"].get("underlying_token"),
        "recipient": event["args"].get("recipient") or event["args"].get("to"),
        "amount": int(event["args"]["amount"]),
        "txHash": event["transactionHash"].hex(),
        "contract": contract_address
    }


# ================= OPTIONAL LIVE LISTENER =================

def listen():
    print("Live listener running...")

    while True:
        scan_blocks("avax", "latest", "latest", SOURCE_ADDRESS)
        scan_blocks("bsc", "latest", "latest", DEST_ADDRESS)
        time.sleep(5)


if __name__ == "__main__":
    listen()
