from wallet import Wallet

import hashlib
from blockchain_settings import POW_DIFFICULTY


class Verification:
    # Verifies transaction validity
    @staticmethod
    def verify_transaction(transaction, get_balance, check_funds=True):
        if check_funds:
            # Check if there are sufficient funds AND check for transaction validity as well
            return get_balance(transaction.sender) >= transaction.amount and Wallet.verify_transaction(transaction)
        else:
            # Only check for transaction validity, don't check funds
            return Wallet.verify_transaction(transaction)

    # Verifies chain validity
    @classmethod
    def verify_chain(cls, blockchain, get_hash):
        for (index, el) in enumerate(blockchain):
            if index == 0:
                continue
            if el.previous_hash != get_hash(blockchain[index - 1]):
                return False
            if not cls.valid_proof(el.transactions[:-1], el.previous_hash, el.proof_number):
                print("Proof of work is invalid")
                return False
        return True

    # Verifies POW
    @staticmethod
    def valid_proof(transactions, previous_hash, proof_number):
        guess = (str([tx.to_ordered_dict() for tx in transactions]) + str(previous_hash) + str(proof_number)).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[0:2] == '0' * POW_DIFFICULTY
