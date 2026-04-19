from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json


# =========================
# PRIVATE KEY (FILL THIS)
# =========================
WARDEN_PRIVATE_KEY = "d475ca0cd9c3e620b888ec34fb6a954439958230bbb0cdc44356e7b8a34e6f50"


# =========================
# CONNECT
# =========================
def connect(chain):
    if chain == "source":
        url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == "destination":
        url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise Exception("invalid chain")

    w3 = Web3(Web3.HTTPProvider(url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


# =========================
# LOAD CONTRACTS
# =========================
def load_info(path="contract_info.json"):
    with open(path, "r") as f:
        return json.load(f)


# =========================
# SIGN + SEND (WEB3 v6 FIXED)
# =========================
def send_tx(w3, tx, pk):
    acct = w3.eth.account.from_key(pk)

    tx["from"] = acct.address
    tx["nonce"] = w3.eth.get_transaction_count(acct.address)
    tx["gas"] = 500000
    tx["gasPrice"] = w3.eth.gas_price

    signed = acct.sign_transaction(tx)
    return w3.eth.send_raw_transaction(signed.raw_transaction).hex()


# =========================
# MAIN FUNCTION
# =========================
def scan_blocks(chain, contract_info="contract_info.json"):

    if WARDEN_PRIVATE_KEY == "PASTE_YOUR_PRIVATE_KEY_HERE":
        raise Exception("Missing private key")

    info = load_info(contract_info)

    w3_src = connect("source")
    w3_dst = connect("destination")

    src = w3_src.eth.contract(
        address=info["source"]["address"],
        abi=info["source"]["abi"]
    )

    dst = w3_dst.eth.contract(
        address=info["destination"]["address"],
        abi=info["destination"]["abi"]
    )

    # ONLY last 5 blocks (autograder requirement)
    src_latest = w3_src.eth.block_number
    dst_latest = w3_dst.eth.block_number

    src_from = max(0, src_latest - 5)
    dst_from = max(0, dst_latest - 5)

    print(f"[SCAN] source {src_from}-{src_latest}")
    print(f"[SCAN] dest {dst_from}-{dst_latest}")

    # =========================
    # SOURCE → DEST (Deposit → Wrap)
    # =========================
    deposits = src.events.Deposit.create_filter(
        from_block=src_from,
        to_block=src_latest
    ).get_all_entries()

    for ev in deposits:
        token = ev["args"]["token"]
        recipient = ev["args"]["recipient"]
        amount = ev["args"]["amount"]

        # 🔴 FIX: map source token → destination wrapped token
        wrapped = dst.functions.wrapped_tokens(token).call()

        if int(w3_dst.to_hex(wrapped), 16) == 0:
            print(f"[SKIP] token not registered: {token}")
            continue

        print(f"[SOURCE] Deposit {token} {recipient} {amount}")

        tx = dst.functions.wrap(
            token,
            recipient,
            amount
        ).build_transaction({
            "chainId": w3_dst.eth.chain_id
        })

        tx_hash = send_tx(w3_dst, tx, WARDEN_PRIVATE_KEY)
        print(f"[DEST] wrap tx: {tx_hash}")

    # =========================
    # DEST → SOURCE (Unwrap → Withdraw)
    # =========================
    unwraps = dst.events.Unwrap.create_filter(
        from_block=dst_from,
        to_block=dst_latest
    ).get_all_entries()

    for ev in unwraps:
        underlying = ev["args"]["underlying_token"]
        to = ev["args"]["to"]
        amount = ev["args"]["amount"]

        print(f"[DEST] Unwrap {underlying} {to} {amount}")

        tx = src.functions.withdraw(
            underlying,
            to,
            amount
        ).build_transaction({
            "chainId": w3_src.eth.chain_id
        })

        tx_hash = send_tx(w3_src, tx, WARDEN_PRIVATE_KEY)
        print(f"[SOURCE] withdraw tx: {tx_hash}")
