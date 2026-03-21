from web3 import Web3
from eth_account.messages import encode_defunct
import random
import os
import json

def sign_challenge(challenge):
    w3 = Web3()

    """ To actually claim the NFT you need to write code in your own file, or use another claiming method
    Once you have claimed an NFT you can come back to this file, update the "sk" and submit to codio to 
    prove that you have claimed your NFT.

    This is the only line you need to modify in this file before you submit """
    sk = "c7da17951aa47188c10879e9a2c6414f30268d8f36d6396a6fb2094c9d63e1bb"

    acct = w3.eth.account.from_key(sk)

    signed_message = w3.eth.account.sign_message(challenge, private_key=acct.key)

    return acct.address, signed_message.signature


def verify_sig():
    """
        This is essentially the code that the autograder will use to test signChallenge
        We've added it here for testing 
    """

    challenge_bytes = random.randbytes(32)

    challenge = encode_defunct(challenge_bytes)
    address, sig = sign_challenge(challenge)

    w3 = Web3()

    return w3.eth.account.recover_message(challenge, signature=sig) == address


if __name__ == '__main__':
    if verify_sig():
        print(f"You passed the challenge!")
    else:
        print(f"You failed the challenge!")
