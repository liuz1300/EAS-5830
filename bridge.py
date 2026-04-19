from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json
import time


########################################
# CONNECT CHAINS
########################################
def connect(chain):
    if chain == "source":
        url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == "destination":
        url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        return None

    w3 = Web3(Web3.HTTPProvider(url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


########################################
# LOAD CONTRACT INFO
########################################
def load_info(path):
    with open(path, "r") as f:
        return json.load(f)


########################################
# SIGN + SEND TX (WARDEN)
########################################
def send_tx(w3, warden, tx):
    tx["nonce"] = w3.eth.get_transaction_count(warden["address"])
    tx["gas"] = 3000000
    tx["gasPrice"] = w3.to_wei("10", "gwei")

    signed = w3.eth.account.sign_transaction(tx, warden["private_key"])
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

    print("TX SENT:", tx_hash.hex())


########################################
# MAIN BRIDGE FUNCTION
########################################
def scan_blocks(chain, contract_info="contract_info.json"):

    if chain not in ["source", "destination"]:
        print("Invalid chain")
        return

    config = load_info(contract_info)

    warden = config["warden"]

    w3 = connect(chain)

    contract = w3.eth.contract(
        address=config[chain]["address"],
        abi=config[chain]["abi"]
    )

    latest = w3.eth.block_number
    from_block = max(0, latest - 5)


    ########################################
    # SOURCE → DESTINATION (Deposit → wrap)
    ########################################
    if chain == "source":

        events = contract.events.Deposit.get_logs(
            fromBlock=from_block,
            toBlock=latest
        )

        dest_w3 = connect("destination")

        dest_contract = dest_w3.eth.contract(
            address=config["destination"]["address"],
            abi=config["destination"]["abi"]
        )

        for e in events:
            recipient = e["args"]["recipient"]
            amount = e["args"]["amount"]

            print("Deposit detected → calling wrap()")

            tx = dest_contract.functions.wrap(
                recipient,
                amount
            ).build_transaction({
                "from": warden["address"]
            })

            send_tx(dest_w3, warden, tx)


    ########################################
    # DESTINATION → SOURCE (Unwrap → withdraw)
    ########################################
    elif chain == "destination":

        events = contract.events.Unwrap.get_logs(
            fromBlock=from_block,
            toBlock=latest
        )

        src_w3 = connect("source")

        src_contract = src_w3.eth.contract(
            address=config["source"]["address"],
            abi=config["source"]["abi"]
        )

        for e in events:
            recipient = e["args"]["recipient"]
            amount = e["args"]["amount"]

            print("Unwrap detected → calling withdraw()")

            tx = src_contract.functions.withdraw(
                recipient,
                amount
            ).build_transaction({
                "from": warden["address"]
            })

            send_tx(src_w3, warden, tx)


########################################
# OPTIONAL LOOP
########################################
def run():
    while True:
        scan_blocks("source")
        scan_blocks("destination")
        time.sleep(10)


if __name__ == "__main__":
    run()
