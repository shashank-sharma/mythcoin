from time import time


class Block:
    def __init__(self, index, previous_hash, transactions, proof_number, timestamp=None):
        self.index = index
        self.previous_hash = previous_hash  # Hash of previous block
        self.transactions = transactions    # Transactions in the block
        self.proof_number = proof_number
        self.timestamp = time() if timestamp is None else timestamp
        # self.timestamp = 0

    def __repr__(self):
        return str(self.__dict__)
