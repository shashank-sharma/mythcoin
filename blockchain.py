import functools
import json
import hashlib
import requests

from block import Block
from transaction import Transaction
from verification import Verification

from wallet import Wallet
from blockchain_settings import MINING_REWARD

# Reward for mining
reward = MINING_REWARD


# Defining attributes and methods of a blockchain
class Blockchain:
    def __init__(self, wallet, node_id):
        ''' Genesis block: The very first block that is hardcoded in the blockchain -
                index: 0
                previous hash: ''
                transactions: []
                proof number: 100
                timestamp: 0
        '''
        genesis_block = Block(0, '', [], 100, 0)

        self.__chain = [genesis_block]
        self.__open_transactions = []
        self.wallet = wallet
        self.__nodes = set()
        self.node_id = node_id
        self.resolve_conflicts = False
        self.load_data()

    @property
    def chain(self):
        return self.__chain[:]

    def get_open_transactions(self):
        return self.__open_transactions[:]

    def get_nodes(self):
        return list(self.__nodes)[:]

    # Function to add transaction in a block
    '''
        sender: Sends transaction to recipient 
        recipient: Receives transactoin from sender
        signature: Unique signature by sender
        amount: Amount to be transfered
    '''

    def add_new_transaction(self, sender, recipient, signature, amount, is_receiving=False):
        transaction = Transaction(sender, recipient, amount, signature)
        if Verification.verify_transaction(transaction, self.get_balance, not is_receiving):
            # Append in outstanding transactions if verification returns true
            self.__open_transactions.append(transaction)
            print("Transaction successfully added!")
            # Save in text file after passing validity check
            self.save_data()
            if not is_receiving:
                # if receiving:
                for node in self.__nodes:
                    # Broadcast transaction to all nodes
                    url = 'http://{}/broadcast-transaction'.format(node)
                    try:
                        response = requests.post(url,
                                                 json={'sender': self.wallet, 'recipient': recipient, 'amount': amount,
                                                       'signature': signature})
                        # Report failure if failed to broadcast transaction
                        if response.status_code == 400 or response.status_code == 500:
                            print('Failed broadcast transaction')
                            return False
                    except requests.exceptions.ConnectionError:
                        continue
            return True
        # Report transaction failure in case transaction does not pass verification
        else:
            print("Transaction failed!")
            return False

    # Function to add block in blockchain
    ''' block: block that needs to be added in the blockchain '''

    def add_block(self, block):
        # loop through transaction attribute in block object and store in variable
        transactions = [Transaction(tx['sender'], tx['recipient'], tx['amount'], tx['signature']) for tx in
                        block['transactions']]
        # First two characters of hash should be 0
        valid_proof = Verification.valid_proof(transactions[:-1], block['previous_hash'], block['proof_number'])
        if not valid_proof:
            print('not valid proof')
        # Checks if previous hashes match in chain
        last_hash = self.get_hash(self.chain[-1]) == block['previous_hash']
        if not last_hash:
            print('not last hash')
        if not valid_proof or not last_hash:
            # Do not add block in chain
            print('Block is not valid. Adding stop')
            return False
        # Add block in chain
        self.__chain.append(
            Block(block['index'], block['previous_hash'], transactions, block['proof_number'], block['timestamp']))
        stored_transactions = self.__open_transactions[:]
        for tx in block['transactions']:
            for opentx in stored_transactions:
                # Check transaction consistency
                if opentx.sender == tx['sender'] and opentx.recipient == tx['recipient'] and opentx.amount == tx[
                    'amount'] and opentx.signature == tx['signature']:
                    try:
                        # Remove from outstanding transaction to maintain consistency
                        self.__open_transactions.remove(opentx)
                    except ValueError:
                        print('Transaction was already removed')
        self.save_data()
        return True

    # Resolves miner conflicts based on chain length
    '''
        Chain with the longest length is considered valid chain
        Shorter chain is not considered in the blockchain
    '''

    def resolve(self):
        winner_chain = self.chain
        replace = False
        for node in self.__nodes:
            url = 'http://{}/chain'.format(node)
            try:
                response = requests.get(url)
                node_chain = response.json()
                node_chain = [Block(block['index'], block['previous_hash'],
                                    [Transaction(tx['sender'], tx['recipient'], tx['amount'], tx['signature'])
                                     for tx in block['transactions']], block['proof_number'], block['timestamp']) for
                              block in node_chain]
                node_chain_len = len(node_chain)
                local_chain_len = len(winner_chain)
                # Make node chain winner if its length is greater than winner chain and it passes verification
                if node_chain_len > local_chain_len and Verification.verify_chain(node_chain, self.get_hash):
                    winner_chain = node_chain
                    replace = True  # Assumed winner chain has been replaced
                    print("1        ")
            except requests.exceptions.ConnectionError:
                continue
        self.resolve_conflicts = False
        self.__chain = winner_chain
        self.save_data()
        return replace

    # Retrieves balance of sender
    '''
        Balance: take into account coins recevied and coins sent
        coins_sent_list: amount sent in transaction if sender is a participant in that transaction
        coins_sent_open_list: amount sent in outstanding transaction if sender is a participant in the outstanding transaction
    '''

    def get_balance(self, sender=None):
        if not sender:
            if self.wallet == None:
                return None
            participant = self.wallet
        else:
            participant = sender
        coins_sent_list = [[tx.amount for tx in block.transactions if tx.sender == participant] for block in
                           self.__chain]
        coins_sent_open_list = [tx.amount for tx in self.__open_transactions if tx.sender == participant]
        coins_sent_list.append(coins_sent_open_list)

        coins_sent = functools.reduce(lambda sum1, amt: sum1 + sum(amt) if len(amt) > 0 else sum1, coins_sent_list, 0)

        coins_accept_list = [[tx.amount for tx in block.transactions if tx.recipient == self.wallet] for block in
                             self.__chain]
        coins_accept = functools.reduce(lambda sum1, amt: sum1 + sum(amt) if len(amt) > 0 else sum1, coins_accept_list,
                                        0)
        return coins_accept - coins_sent

    # Function to mine blocks
    def mine_block(self):
        if not self.wallet:
            return None
        proof_number = self.proof_of_work()
        transaction_reward = Transaction('REWARD', self.wallet, reward, '')
        copy_open_transactions = self.__open_transactions[:]
        for tx in copy_open_transactions:
            # Check validity of outstanding transaction
            if not Wallet.verify_transaction(tx):
                print('open transactions is not valid')
                return None
        copy_open_transactions.append(transaction_reward)
        previous_hash = self.get_hash(self.__chain[-1])
        block = Block(len(self.__chain), previous_hash, copy_open_transactions, proof_number)
        # Append block in chain and clear outstanding transaction
        self.__chain.append(block)
        self.__open_transactions.clear()
        self.save_data()
        dict_block = block.__dict__.copy()
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']]
        # Broadcast this to other nodes in the network
        for node in self.__nodes:
            url = 'http://{}/broadcast-block'.format(node)
            try:
                response = requests.post(url, json={'block': dict_block})
                if response.status_code == 400 or response.status_code == 500:
                    print('Failed broadcast block')
                if response.status_code == 409:
                    self.resolve_conflicts = True
            except requests.exceptions.ConnectionError:
                continue
        return block

    # Function of POW
    def proof_of_work(self):
        last_block = self.__chain[-1]
        previous_hash = self.get_hash(last_block)
        proof_number = 0
        while not Verification.valid_proof(self.__open_transactions, previous_hash, proof_number):
            proof_number += 1
        return proof_number

    def get_hash(self, block):
        hashed_block = block.__dict__.copy()
        hashed_block['transactions'] = [tx.to_ordered_dict() for tx in hashed_block['transactions']]
        return hashlib.sha256(json.dumps(hashed_block, sort_keys=True).encode()).hexdigest()

    # Saves data in blockchain-host.txt if validity check is passed
    def save_data(self):
        with open('blockchain-{}.txt'.format(self.node_id), mode='w') as file:
            # pickle realization
            # save_data = {
            #     'blockchain': blockchain,
            #     'open_transactions': open_transactions
            # }
            # file.write(pickle.dumps(save_data))

            # json realization

            dict_blockchain = [block.__dict__ for block in [
                Block(block_el.index, block_el.previous_hash, [tx.__dict__ for tx in block_el.transactions],
                      block_el.proof_number, block_el.timestamp) for block_el in self.__chain.copy()]]
            file.write(json.dumps(dict_blockchain))
            file.write('\n')
            savable_transactions = [tx.__dict__ for tx in self.__open_transactions]
            file.write(json.dumps(savable_transactions))
            file.write('\n')
            file.write(json.dumps(list(self.__nodes)))

    # Function to load blockchain
    def load_data(self):
        try:
            with open('blockchain-{}.txt'.format(self.node_id), mode='r') as file:
                # pickle realization
                # file_content = pickle.loads(file.read())
                # blockchain = file_content['blockchain']
                # open_transactions = file_content['open_transactions']

                # json realization
                line = file.readlines()
                updated_blockchain = []
                blockchain = json.loads(line[0][:-1])
                for block in blockchain:
                    transactions = [Transaction(tx['sender'], tx['recipient'], tx['amount'], tx['signature']) for tx in
                                    block['transactions']]
                    updated_block = Block(block['index'], block['previous_hash'], transactions, block['proof_number'],
                                          block['timestamp'])
                    updated_blockchain.append(updated_block)
                self.__chain = updated_blockchain

                json_transactions = json.loads(line[1][:-1])
                updated_transactions = [Transaction(tx['sender'], tx['recipient'], tx['amount'], tx['signature']) for tx
                                        in
                                        json_transactions]
                self.__open_transactions = updated_transactions
                self.__nodes = set(json.loads(line[2]))

        except (IOError, IndexError):
            print("Error load file")

    def add_node(self, node):
        self.__nodes.add(node)
        self.save_data()

    def remove_node(self, node):
        self.__nodes.discard(node)
        self.save_data()
