from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
import json
import time


# =========================
# CONNECTIONS
# =========================
def connect_to(chain):
    if chain == "source":
        url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == "destination":
        url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise Exception("Invalid chain")

    w3 = Web3(Web3.HTTPProvider(url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


# =========================
# LOAD CONTRACTS
# =========================
def get_contract_info(chain, file="contract_info.json"):
    with open(file, "r") as f:
        data = json.load(f)
    return data[chain]


# =========================
# WARDEN SETUP
# =========================
# Put your private key here OR use env var
WARDEN_PRIVATE_KEY = "d475ca0cd9c3e620b888ec34fb6a954439958230bbb0cdc44356e7b8a34e6f50"
warden = Account.from_key(WARDEN_PRIVATE_KEY)


# =========================
# SEND SIGNED TX
# =========================
def send_tx(w3, fn):
    tx = fn.build_transaction({
        "from": warden.address,
        "nonce": w3.eth.get_transaction_count(warden.address),
        "gas": 300000,
        "gasPrice": w3.eth.gas_price
    })

    signed = warden.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    return tx_hash.hex()


# =========================
# BRIDGE LOGIC
# =========================
def scan_blocks(chain, contract_info="contract_info.json"):

    if chain not in ["source", "destination"]:
        print("Invalid chain")
        return 0

    w3 = connect_to(chain)

    info = get_contract_info(chain, contract_info)
    contract = w3.eth.contract(address=info["address"], abi=info["abi"])

    latest = w3.eth.block_number
    start = max(0, latest - 5)

    # =====================================================
    # SOURCE → DESTINATION (Deposit → wrap)
    # =====================================================
    if chain == "source":

        events = contract.events.Deposit.get_logs(
            from_block=start,
            to_block=latest
        )

        dest_info = get_contract_info("destination", contract_info)
        dest = w3.eth.contract(
            address=dest_info["address"],
            abi=dest_info["abi"]
        )

        for e in events:
            token = e["args"]["token"]
            recipient = e["args"]["recipient"]
            amount = e["args"]["amount"]

            print(f"[SOURCE] Deposit detected: {token}, {recipient}, {amount}")

            tx_hash = send_tx(
                w3,
                dest.functions.wrap(token, recipient, amount)
            )

            print(f"[DEST] wrap tx: {tx_hash}")

    # =====================================================
    # DESTINATION → SOURCE (Unwrap → withdraw)
    # =====================================================
    if chain == "destination":

        events = contract.events.Unwrap.get_logs(
            from_block=start,
            to_block=latest
        )

        src_info = get_contract_info("source", contract_info)
        src = w3.eth.contract(
            address=src_info["address"],
            abi=src_info["abi"]
        )

        for e in events:
            token = e["args"]["underlying_token"]
            recipient = e["args"]["to"]
            amount = e["args"]["amount"]

            print(f"[DEST] Unwrap detected: {token}, {recipient}, {amount}")

            tx_hash = send_tx(
                w3,
                src.functions.withdraw(token, recipient, amount)
            )

            print(f"[SOURCE] withdraw tx: {tx_hash}")

    return 1


# =========================
# OPTIONAL LOOP (AUTOMATIC LISTENER)
# =========================
if __name__ == "__main__":
    while True:
        print("Scanning source...")
        scan_blocks("source")

        print("Scanning destination...")
        scan_blocks("destination")

        time.sleep(10)
