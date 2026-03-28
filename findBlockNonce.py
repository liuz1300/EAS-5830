#!/bin/python
import hashlib
import os
import random


def mine_block(k, prev_hash, transactions):
    """
        k - Number of trailing zeros in the binary representation (integer)
        prev_hash - the hash of the previous block (bytes)
        transactions - list of strings

        Find a nonce such that:
        sha256(prev_hash + transactions + nonce)
        has >= k trailing zero bits
    """
    if not isinstance(k, int) or k < 0:
        print("mine_block expects positive integer")
        return b'\x00'

    if not isinstance(prev_hash, bytes):
        raise TypeError("prev_hash must be bytes")

    if not isinstance(transactions, list):
        raise TypeError("transactions must be a list of strings")

    # Convert transactions into a single bytes object
    tx_data = "".join(transactions).encode()

    # Mask to check last k bits
    mask = (1 << k) - 1

    nonce_int = 0

    while True:
        # Convert nonce to bytes (8 bytes is usually enough, can increase if needed)
        nonce = nonce_int.to_bytes(8, byteorder='big')

        # Compute hash
        h = hashlib.sha256(prev_hash + tx_data + nonce).digest()

        # Convert hash to integer
        hash_int = int.from_bytes(h, byteorder='big')

        # Check if last k bits are zero
        if (hash_int & mask) == 0:
            return nonce

        nonce_int += 1


def get_random_lines(filename, quantity):
    """
    This is a helper function to get the quantity of lines ("transactions")
    as a list from the filename given. 
    Do not modify this function
    """
    lines = []
    with open(filename, 'r') as f:
        for line in f:
            lines.append(line.strip())

    random_lines = []
    for x in range(quantity):
        random_lines.append(lines[random.randint(0, quantity - 1)])
    return random_lines


if __name__ == '__main__':
    # This code will be helpful for your testing
    filename = "bitcoin_text.txt"
    num_lines = 10  # The number of "transactions" included in the block

    # The "difficulty" level. For our blocks this is the number of Least Significant Bits
    # that are 0s. For example, if diff = 5 then the last 5 bits of a valid block hash would be zeros
    # The grader will not exceed 20 bits of "difficulty" because larger values take to long
    diff = 20

    transactions = get_random_lines(filename, num_lines)
    nonce = mine_block(diff, transactions)
    print(nonce)
