import hashlib
import time
import json
from flask import Flask, request

class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.create_block(proof=1, previous_hash='0')  # Tworzenie bloku genezy
        self.reward = 50  # Nagroda za blok (np. 50 jednostek kryptowaluty)

    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.transactions,
            'proof': proof,
            'previous_hash': previous_hash
        }
        self.transactions = []  # Resetowanie transakcji po dodaniu bloku
        self.chain.append(block)
        return block

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_work(self, previous_proof):
        new_proof = 1
        while not self.is_valid_proof(previous_proof, new_proof):
            new_proof += 1
        return new_proof

    def is_valid_proof(self, previous_proof, new_proof):
        guess = f'{previous_proof}{new_proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'  # Warunek proof-of-work

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

app = Flask(__name__)
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine_block():
    previous_block = blockchain.get_previous_block()
    proof = blockchain.proof_of_work(previous_block['proof'])
    previous_hash = blockchain.hash(previous_block)
    
    # Dodajemy nagrodę za blok (nagroda za mining)
    blockchain.add_transaction(sender="0", receiver="miner_address", amount=blockchain.reward)
    
    # Tworzymy nowy blok
    block = blockchain.create_block(proof, previous_hash)
    return block

@app.route('/chain', methods=['GET'])
def get_chain():
    response = {'chain': blockchain.chain, 'length': len(blockchain.chain)}
    return response

@app.route('/transaction', methods=['GET'])
def add_transaction():
    #values = request.get_json()

    #print(request)
    
    # Weryfikujemy dane transakcji
    #required_fields = ['sender', 'receiver', 'amount']
    #if not all(field in values for field in required_fields):
    #    return 'Brak wymaganych pól', 400

    # Dodajemy transakcję do listy
    blockchain.add_transaction("a", "b", 10)
    
    return f'Transakcja dodana do bloku', 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
