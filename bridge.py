from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
import json
import time


# =========================
# CONFIG (PUT YOUR KEY HERE)
# =========================
WARDEN_PRIVATE_KEY = "d475ca0cd9c3e620b888ec34fb6a954439958230bbb0cdc44356e7b8a34e6f50"
warden = Account.from_key(WARDEN_PRIVATE_KEY)

RPCS = {
    "source": "https://api.avax-test.network/ext/bc/C/rpc",
    "destination": "https://data-seed-prebsc-1-s1.binance.org:8545/"
}


# =========================
# CONNECT
# =========================
def connect(chain):
    w3 = Web3(Web3.HTTPProvider(RPCS[chain]))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


# =========================
# LOAD CONTRACT INFO
# =========================
def load_contract(chain, file="contract_info.json"):
    with open(file, "r") as f:
        return json.load(f)[chain]


# =========================
# SIGN + SEND TX (WEB3 v6 FIX)
# =========================
def send_tx(w3, fn):
    tx = fn.build_transaction({
        "from": warden.address,
        "nonce": w3.eth.get_transaction_count(warden.address, "pending"),
        "gas": 500000,
        "gasPrice": int(w3.eth.gas_price * 1.2)
    })

    signed = warden.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    return tx_hash.hex()


# =========================
# MAIN BRIDGE FUNCTION
# =========================
def scan_blocks(chain, contract_info="contract_info.json"):

    if chain not in ["source", "destination"]:
        print("Invalid chain")
        return 0

    w3 = connect(chain)

    info = load_contract(chain, contract_info)
    contract = w3.eth.contract(address=info["address"], abi=info["abi"])

    latest = w3.eth.block_number
    start = max(0, latest - 5)

    time.sleep(2)  # avoid RPC rate limit

    # =========================
    # SOURCE → DEST (Deposit → wrap)
    # =========================
    if chain == "source":

        events = contract.events.Deposit.get_logs(
            from_block=start,
            to_block=latest
        )

        dest_info = load_contract("destination", contract_info)
        dest = w3.eth.contract(address=dest_info["address"], abi=dest_info["abi"])

        for e in events:
            token = e["args"]["token"]
            recipient = e["args"]["recipient"]
            amount = e["args"]["amount"]

            print(f"[SOURCE] Deposit: {token}, {recipient}, {amount}")

            tx = send_tx(
                w3,
                dest.functions.wrap(token, recipient, amount)
            )

            print(f"[DEST] wrap tx: {tx}")

    # =========================
    # DEST → SOURCE (Unwrap → withdraw)
    # =========================
    if chain == "destination":

        events = contract.events.Unwrap.get_logs(
            from_block=start,
            to_block=latest
        )

        src_info = load_contract("source", contract_info)
        src = w3.eth.contract(address=src_info["address"], abi=src_info["abi"])

        for e in events:

            underlying = e["args"]["underlying_token"]
            wrapped = e["args"]["wrapped_token"]
            recipient = e["args"]["to"]
            amount = e["args"]["amount"]

            print(f"[DEST] Unwrap: {underlying}, {wrapped}, {recipient}, {amount}")

            # 🔥 CRITICAL FIX:
            # Source ONLY knows ORIGINAL token (underlying)
            tx = send_tx(
                w3,
                src.functions.withdraw(
                    underlying,   # MUST be registered in Source.approved[]
                    recipient,
                    amount
                )
            )

            print(f"[SOURCE] withdraw tx: {tx}")

    return 1


# =========================
# LOOP
# =========================
if __name__ == "__main__":
    while True:
        scan_blocks("source")
        scan_blocks("destination")
        time.sleep(6)
