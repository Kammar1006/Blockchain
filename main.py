import hashlib
import time
import json
from flask import Flask, request
import os, sys
import atexit
import requests

class Blockchain:
    def __init__(self, node_address):
        self.chain = []
        self.transactions = []
        self.reward = 50
        self.difficulty = 2
        self.mining_in_progress = False
        self.nodes = set()
        self.node_address = node_address
        
        self.create_block(proof=1, previous_hash='0')
        self.load_blockchain()

        self.nodes.add(self.node_address)
        
        if node_address != "127.0.0.1:5000":
            self.register_with_main_node()


    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.transactions,
            'proof': proof,
            'previous_hash': previous_hash
        }

        block['hash'] = self.hash(block)  # 📌 Dodaj hash do bloku!

        self.transactions = []
        self.chain.append(block)
        if(len(self.chain) > 20*self.difficulty and self.difficulty < 7):
            self.difficulty += 1
        return block

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_work(self, previous_proof):
        new_proof = 1
        start_time = time.time()
        
        while True:
            if self.is_valid_proof(previous_proof, new_proof):
                break
            new_proof += 1
        
        mining_time = round(time.time() - start_time, 2)
        print(f"Blok wykopany w {mining_time} sekund. Proof: {new_proof}")
        
        return new_proof

    def is_valid_proof(self, previous_proof, new_proof):
        guess = f'{previous_proof}{new_proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:self.difficulty] == '0' * self.difficulty

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        previous_block = chain[0]
        for block in chain[1:]:
            if block['previous_hash'] != self.hash(previous_block):
                return False
            if not self.is_valid_proof(previous_block['proof'], block['proof']):
                return False
            previous_block = block
        return True

    def add_transaction(self, sender, receiver, amount):
        self.transactions.append({
            'sender': sender,
            'receiver': receiver,
            'amount': amount
        })

    def save_blockchain(self):
        with open("blockchain.json", "w") as file:
            json.dump(self.chain, file, indent=4)
    
    def load_blockchain(self):
        if os.path.exists("blockchain.json"):
            with open("blockchain.json", "r") as file:
                self.chain = json.load(file)

    def replace_chain(self):
        longest_chain = None
        max_length = len(self.chain)

        for node in self.nodes:
            if node == self.node_address:
                continue
            try:
                response = requests.get(f"http://{node}/chain")
                if response.status_code == 200:
                    length = response.json()["length"]
                    chain = response.json()["chain"]
                    if length > max_length and self.is_chain_valid(chain):
                        max_length = length
                        longest_chain = chain
            except:
                continue  # Węzeł może być offline, ignorujemy błędy
        
        if longest_chain:
            self.chain = longest_chain
            self.save_blockchain()
            return True
        return False

    def announce_updated_chain(self):
        for node in self.nodes:
            if node == self.node_address:
                continue
            try:
                requests.get(f"http://{node}/sync")
            except:
                continue 

    def announce_new_block(self, block):
        for node in self.nodes:
            if node == self.node_address:
                continue
            try:
                requests.post(f"http://{node}/new_block", json=block)
            except:
                continue  # Ignorujemy błędy

    def announce_new_node(self, new_nodes):
        for node in self.nodes:
            for new_node in new_nodes:
                if node == self.node_address:
                    continue
                try:
                    requests.post(f"http://{node}/register_node", json={"nodes": [new_node]})
                    
                except:
                    continue

    def register_with_main_node(self):
        try:
            response = requests.post(f"http://127.0.0.1:5000/register_node", json={"nodes": [self.node_address]})
            if response.status_code == 201:
                nodes = response.json().get("nodes", [])
                self.nodes.update(nodes)
                print(f"Zarejestrowano w sieci! Aktualne nody: {self.nodes}")
        except:
            print("Błąd rejestracji w bazowym nodzie.")

app = Flask(__name__)

@app.route('/mine', methods=['GET'])
def mine_block():

    if blockchain.mining_in_progress:
        return "Mining in progress....", 400
    
    blockchain.mining_in_progress = True

    previous_block = blockchain.get_previous_block()
    proof = blockchain.proof_of_work(previous_block['proof'])
    previous_hash = previous_block['hash']
    
    # Nagroda dla górnika
    blockchain.add_transaction(sender="0", receiver="miner_address", amount=blockchain.reward)
    
    block = blockchain.create_block(proof, previous_hash)

    blockchain.mining_in_progress = False

    blockchain.announce_new_block(block)

    return block

@app.route('/chain', methods=['GET'])
def get_chain():
    response = {'length': len(blockchain.chain), 'dif': blockchain.difficulty, 'chain': blockchain.chain}
    return response

@app.route('/register_node', methods=['POST'])
def register_node():
    values = request.get_json()
    nodes = values.get("nodes")
    if nodes is None:
        return "No node to register", 400

    for node in nodes:
        blockchain.nodes.add(node)

    # Informujemy inne nody o nowym węźle
    blockchain.announce_new_node(nodes)

    return {
        "message": "Node registered",
        "nodes": list(blockchain.nodes)
    }, 201

@app.route('/sync', methods=['GET'])
def sync():
    replaced = blockchain.replace_chain()
    if replaced:
        return {"message": "Blockchain update!"}
    return {"message": "Blockchain is already updated"}

@app.route('/new_block', methods=['POST'])
def new_block():
    values = request.get_json()
    if values is None:
        return "Invalid data", 400

    block = values
    previous_block = blockchain.get_previous_block()

    if previous_block["index"] + 1 == block["index"] and \
       previous_block["hash"] == block["previous_hash"] and \
       blockchain.is_valid_proof(previous_block["proof"], block["proof"]):

        blockchain.chain.append(block)
        blockchain.save_blockchain()

        # Po dodaniu nowego bloku, informujemy inne nody
        blockchain.announce_new_block(block)

        return {"message": "Block accepted"}, 201
    else:
        return {"message": "Block refused"}, 400

@app.route('/nodes', methods=['GET'])
def get_nodes():
    """Zwraca listę podłączonych nodów"""
    return {"nodes": list(blockchain.nodes)}, 200

'''
@app.route('/transaction', methods=['POST'])
def add_transaction():
    values = request.get_json()
    required_fields = ['sender', 'receiver', 'amount']
    if not all(field in values for field in required_fields):
        return 'Brak wymaganych pól', 400

    blockchain.add_transaction(values['sender'], values['receiver'], values['amount'])
    return f'Transakcja dodana do bloku', 201
'''

if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = int(sys.argv[1])  # Można podać port jako argument

    blockchain = Blockchain(f"127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port)


atexit.register(blockchain.save_blockchain)