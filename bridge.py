from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from pathlib import Path
import json
import pandas as pd
import time

# ================= WALLET CONFIG =================

PRIVATE_KEY = "d475ca0cd9c3e620b888ec34fb6a954439958230bbb0cdc44356e7b8a34e6f50"
ACCOUNT = Web3.to_checksum_address("0xbA52AeFe6Cb8da87dfc0F60E3A916f957060e491")

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


def send_tx(w3, fn):
    nonce = w3.eth.get_transaction_count(ACCOUNT)

    tx = fn.build_transaction({
        "from": ACCOUNT,
        "nonce": nonce,
        "gas": 300000,
        "gasPrice": w3.to_wei("5", "gwei")
    })

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

    print("[TX SENT]", tx_hash.hex())
    return tx_hash.hex()


# ================= REQUIRED FUNCTION =================

def scan_blocks(chain, contract_info="contract_info.json"):

    with open(contract_info) as f:
        data = json.load(f)

    source_addr = Web3.to_checksum_address(data["source"]["address"])
    dest_addr = Web3.to_checksum_address(data["destination"]["address"])

    source_abi = data["source"]["abi"]
    dest_abi = data["destination"]["abi"]

    w3 = get_w3(chain)

    rows = []

    # ================= SOURCE CHAIN (Deposit) =================
    if chain == "avax":

        contract = w3.eth.contract(address=source_addr, abi=source_abi)
        event_filter = contract.events.Deposit.create_filter(from_block="latest")

        for event in event_filter.get_new_entries():

            rows.append(parse_event(event, chain))

            handle_deposit(event, dest_addr, dest_abi)

    # ================= DESTINATION CHAIN (Unwrap) =================
    else:

        contract = w3.eth.contract(address=dest_addr, abi=dest_abi)
        event_filter = contract.events.Unwrap.create_filter(from_block="latest")

        for event in event_filter.get_new_entries():

            rows.append(parse_event(event, chain))

            handle_unwrap(event, source_addr, source_abi)

    # ================= SAVE CSV =================

    if rows:
        df = pd.DataFrame(rows)
        file_path = Path("deposit_logs.csv")

        if file_path.exists():
            df.to_csv(file_path, mode="a", header=False, index=False)
        else:
            df.to_csv(file_path, mode="w", header=True, index=False)

        print(f"[CSV] Saved {len(rows)} events")


# ================= EVENT HANDLERS =================

def handle_deposit(event, dest_addr, dest_abi):

    print("[EVENT] Deposit → wrap()")

    token = Web3.to_checksum_address(event["args"]["token"])
    recipient = Web3.to_checksum_address(event["args"]["recipient"])
    amount = int(event["args"]["amount"])

    w3 = get_w3("bsc")
    contract = w3.eth.contract(address=dest_addr, abi=dest_abi)

    fn = contract.functions.wrap(token, recipient, amount)
    send_tx(w3, fn)


def handle_unwrap(event, source_addr, source_abi):

    print("[EVENT] Unwrap → withdraw()")

    token = Web3.to_checksum_address(event["args"]["underlying_token"])
    recipient = Web3.to_checksum_address(event["args"]["to"])
    amount = int(event["args"]["amount"])

    w3 = get_w3("avax")
    contract = w3.eth.contract(address=source_addr, abi=source_abi)

    fn = contract.functions.withdraw(token, recipient, amount)
    send_tx(w3, fn)


# ================= EVENT PARSER =================

def parse_event(event, chain):
    args = event["args"]

    return {
        "chain": chain,
        "token": args.get("token") or args.get("underlying_token"),
        "recipient": args.get("recipient") or args.get("to"),
        "amount": int(args["amount"]),
        "txHash": event["transactionHash"].hex()
    }


# ================= OPTIONAL RUN LOOP =================

def listen():
    print("Listening...")

    while True:
        scan_blocks("avax")
        scan_blocks("bsc")
        time.sleep(5)


if __name__ == "__main__":
    listen()
