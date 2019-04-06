from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from wallet import Wallet
from blockchain import Blockchain

app = Flask(__name__)

CORS(app)


# Get web app UI

@app.route('/', methods=['GET'])
def get_node_ui():
    return send_from_directory('frontend', 'node.html')


@app.route('/network', methods=['GET'])
def get_network_ui():
    return send_from_directory('frontend', 'network.html')


# Create wallet
@app.route('/wallet', methods=['POST'])
def create_keys():
    wallet.create_keys()
    if wallet.save_keys():
        global blockchain
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {'message': 'Saving the keys error'}
        return jsonify(response), 500

# Load wallet
@app.route('/wallet', methods=['GET'])
def load_keys():
    if wallet.load_keys():
        global blockchain
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {'message': 'Load the keys error'}
        return jsonify(response), 500

# Get wallet balance
@app.route('/balance', methods=['GET'])
def get_balance():
    balance = blockchain.get_balance()
    if balance != None:
        response = {
            'funds': balance
        }
        return jsonify(response), 200
    else:
        response = {
            'message': 'Error trying get balance',
            'wallet': wallet.public_key != None
        }
        return jsonify(response), 500

# Broadcast transaction
@app.route('/broadcast-transaction', methods=['POST'])
def broadcast_transaction():
    values = request.get_json()
    if not values:
        response = {'message': 'No data found.'}
        print('1')
        return jsonify(response), 400
    required_fields = ['sender', 'recipient', 'amount', 'signature']
    if not all(field in values for field in required_fields):
        response = {'message': 'Required data is missing'}
        print('2')
        return jsonify(response), 400
    success = blockchain.add_new_transaction(values['sender'], values['recipient'], values['signature'], values['amount'], True)
    if success:
        response = {
            'message': 'Trunsaction successfully add',
            'transaction': {
                'sender': values['sender'],
                'recipient': values['recipient'],
                'amount': values['amount'],
                'signature': values['signature']
            }
        }
        return jsonify(response), 201
    else:
        response = {'message': 'Failed add transaction'}
        print('4')
        return jsonify(response), 400

# Broadcast block
@app.route('/broadcast-block', methods=['POST'])
def broadcast_block():
    values = request.get_json()
    if not values:
        response = {'Message': 'No data found'}
        return jsonify(response), 400
    if 'block' not in values:
        response = {'Message': 'No Block in values'}
        return jsonify(response), 400
    block = values['block']
    if block['index'] == blockchain.chain[-1].index + 1:
        if blockchain.add_block(block):
            response = {'message': 'Block added'}
            return jsonify(response), 201
        else:
            response = {'message': 'Block seems invalid.'}
            return jsonify(response), 409
    elif block['index'] > blockchain.chain[-1].index + 1:
        response = {'message': 'Block seems to differ from local blockchain.'}
        blockchain.resolve_conflicts = True
        return jsonify(response), 200
    else:
        response = {'message': 'Blockchain seems to be shorter, block not added'}
        return jsonify(response), 409

# Add transaction
@app.route('/transaction', methods=['POST'])
def add_transaction():
    if wallet.public_key is None:
        response = {'message': 'You have no wallet'}
        return jsonify(response), 400
    values = request.get_json()
    if not values:
        response = {'message': 'No data found.'}
        return jsonify(response), 400
    required_fields = ['recipient', 'amount']
    if not all(field in values for field in required_fields):
        response = {'message': 'Required data is missing'}
        return jsonify(response), 400
    else:
        recipient = values['recipient']
        amount = values['amount']
        signature = wallet.sign_transaction(wallet.public_key, recipient, amount)
        success = blockchain.add_new_transaction(wallet.public_key, recipient, signature, amount)
        if success:
            response = {
                'message': 'Trunsaction successfully add',
                'transaction': {
                    'sender': wallet.public_key,
                    'recipient': recipient,
                    'amount': amount,
                    'signature': signature
                },
                'funds': blockchain.get_balance()
            }
            return jsonify(response), 201
        else:
            response = {'message': 'Failed add transaction'}
            return jsonify(response), 400

# Resolve miner conflicts
@app.route('/resolve-conflicts', methods=['POST'])
def resolve_conflicts():
    replaced = blockchain.resolve()
    if replaced:
        response = {'message': 'Chain was replaced'}
    else:
        response = {'message': 'Local chain saved'}
    return jsonify(response), 200

# Mine for reward
@app.route('/mine', methods=['POST'])
def mine():
    if blockchain.resolve_conflicts:
        response = {'message': 'Resolve conflicts first, block not added'}
        return jsonify(response), 409
    block = blockchain.mine_block()
    if block != None:
        dict_block = block.__dict__.copy()
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']]
        response = {
            'message': 'Block added successfully',
            'block': dict_block,
            'funds': blockchain.get_balance()
        }
    else:
        response = {
            'message': 'Adding a block failed',
            'wallet': wallet.public_key != None
        }
    return jsonify(response)


@app.route('/transactions', methods=['GET'])
def get_transactions():
    transactions = blockchain.get_open_transactions()
    transactions = [tx.__dict__ for tx in transactions]
    return jsonify(transactions)


@app.route('/chain', methods=['GET'])
def get_chain():
    chain_snapshot = blockchain.chain
    dict_chain = [block.__dict__.copy() for block in chain_snapshot]
    for dict_block in dict_chain:
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']]
    return jsonify(dict_chain), 200


@app.route('/node', methods=['POST'])
def add_node():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data attached'
        }
        return jsonify(response), 400
    if 'node' not in values:
        response = {
            'message': 'No node found'
        }
        return jsonify(response), 400
    blockchain.add_node(values['node'])
    response = {
        'message': 'Node add successfully',
        'nodes': blockchain.get_nodes()
    }
    return jsonify(response), 201


@app.route('/node/<node_url>', methods=['DELETE'])
def remove_node(node_url):
    if node_url == '' or node_url == None:
        response = {
            'message': 'No node found'
        }
        return jsonify(response), 400
    blockchain.remove_node(node_url)
    response = {
        'message': 'Node removed',
        'nodes': blockchain.get_nodes()
    }
    return jsonify(response), 200


@app.route('/nodes', methods=['GET'])
def get_nodes():
    response = {
        'nodes': blockchain.get_nodes()
    }
    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5000)
    args = parser.parse_args()
    port = args.port
    wallet = Wallet(port)
    blockchain = Blockchain(wallet.public_key, port)
    app.run(host='0.0.0.0', port=port)
