from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json


# =========================
# CONNECT
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
# MAIN LISTENER (NO SIGNING)
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

    # =========================
    # SOURCE → DESTINATION
    # =========================
    if chain == "source":

        events = contract.events.Deposit.get_logs(
            from_block=start,
            to_block=latest
        )

        for e in events:
            token = e["args"]["token"]
            recipient = e["args"]["recipient"]
            amount = e["args"]["amount"]

            print(f"[SOURCE] Deposit detected:")
            print(f"  token={token}")
            print(f"  recipient={recipient}")
            print(f"  amount={amount}")
            print("➡ ACTION REQUIRED: call wrap() on destination chain")

    # =========================
    # DESTINATION → SOURCE
    # =========================
    if chain == "destination":

        events = contract.events.Unwrap.get_logs(
            from_block=start,
            to_block=latest
        )

        for e in events:
            token = e["args"]["underlying_token"]
            recipient = e["args"]["to"]
            amount = e["args"]["amount"]

            print(f"[DESTINATION] Unwrap detected:")
            print(f"  token={token}")
            print(f"  recipient={recipient}")
            print(f"  amount={amount}")
            print("➡ ACTION REQUIRED: call withdraw() on source chain")

    return 1
