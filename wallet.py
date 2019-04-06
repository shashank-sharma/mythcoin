from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import Crypto.Random
import binascii


class Wallet:
    def __init__(self, node_id):
        self.private_key = None
        self.public_key = None
        self.node_id = node_id

    # Function to create public and secret (private) key
    def create_keys(self):
        private_key, public_key = self.generate_keys()
        self.private_key = private_key
        self.public_key = public_key

    # Function to save generated kets in a wallet-host.txt file
    def save_keys(self):
        if self.public_key is not None and self.private_key is not None:
            try:
                with open('wallet-{}.txt'.format(self.node_id), mode='w') as f:
                    f.write(self.public_key)
                    f.write('\n')
                    f.write(self.private_key)
                return True
            except(IOError, IndexError):
                print('Saving keys error')
                return False

    # Function to load wallet
    def load_keys(self):
            try:
                with open('wallet-{}.txt'.format(self.node_id), mode='r') as f:
                    keys = f.readlines()
                    self.public_key = keys[0][:-1]
                    self.private_key = keys[1]
                return True
            except(IOError, IndexError):
                print('Load keys error')
                return False

    # Function to generate public and secret(private) keys
    def generate_keys(self):
        private_key = RSA.generate(1024, Crypto.Random.get_random_bytes)
        public_key = private_key.publickey()
        private_key_str = binascii.hexlify(private_key.export_key(format='DER')).decode()
        public_key_str = binascii.hexlify(public_key.export_key(format='DER')).decode()
        return private_key_str, public_key_str

    # Function to sign transaction
    def sign_transaction(self, sender, recipient, amount):
        signer = PKCS1_v1_5.new(RSA.import_key(binascii.unhexlify(self.private_key)))
        h = SHA256.new((str(sender) + str(recipient) + str(amount)).encode('utf8'))
        signature = signer.sign(h)
        return binascii.hexlify(signature).decode('ascii')

    # Function to verify wallet transaction
    @staticmethod
    def verify_transaction(transaction):
        public_key = RSA.import_key(binascii.unhexlify(transaction.sender))
        verifier = PKCS1_v1_5.new(public_key)
        h = SHA256.new((str(transaction.sender) + str(transaction.recipient) + str(transaction.amount)).encode('utf8'))
        return verifier.verify(h, binascii.unhexlify(transaction.signature))
