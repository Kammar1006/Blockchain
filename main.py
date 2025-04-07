import hashlib
import time
import json
from flask import Flask, request
import os, sys
import atexit
import requests
import copy
import threading


class Blockchain:
    def __init__(self, node_address):
        self.chain = []
        self.transactions = []
        self.reward = 50
        self.difficulty = 2
        self.mining_in_progress = False
        self.nodes = set()
        self.node_address = node_address
        self.known_transaction_hashes = set()
        
        self.load_blockchain()
        if not self.chain:
            genesis_block = self.proof_of_work()
            self.create_block(genesis_block)

        self.nodes.add(self.node_address)
        
        if node_address != "127.0.0.1:5000":
            self.register_with_main_node()

    
    def create_block(self, block):
        self.chain.append(block)
        self.transactions = []
        self.save_blockchain()
        return block

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_work(self):
        previous_block = self.get_previous_block()
        previous_hash = previous_block["hash"]
        proof = 0  # Startujemy od 0, zamiast 1
        
        while True:
            copy_list = copy.deepcopy(self.transactions)
            copy_list.append({
                'sender': "*",
                'receiver': self.node_address,
                'amount': self.reward
            })
            block = {
                'index': previous_block['index'] + 1,
                'timestamp': time.time(),
                'transactions': copy_list,
                'proof': proof,
                'previous_hash': previous_hash
            }
            block['hash'] = self.hash(block)
            
            if block['hash'][:self.difficulty] == '0' * self.difficulty:
                break

            proof += 1
        
        print(f"Blok wykopany! Proof: {proof}, Hash: {block['hash']}")
        return block


    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        previous_block = chain[0]
        
        for block in chain[1:]:
            # Sprawdzamy, czy previous_hash zgadza się z hashem poprzedniego bloku
            if block['previous_hash'] != previous_block['hash']:
                return False
            
            # Sprawdzamy, czy hash bloku spełnia warunek trudności
            if block['hash'][:self.difficulty] != '0' * self.difficulty:
                return False

            previous_block = block  # Przechodzimy do następnego bloku
        
        return True
    
    def transaction_hash(self, tx):
        tx_copy = tx.copy()
        return hashlib.sha256(json.dumps(tx_copy, sort_keys=True).encode()).hexdigest()

    def add_transaction(self, sender, receiver, amount, timestamp=None):
        if timestamp is None:
            timestamp = time.time()

        tx = {
            'sender': sender,
            'receiver': receiver,
            'amount': amount,
            'timestamp': timestamp
        }

        tx_hash = self.transaction_hash(tx)

        if tx_hash in self.known_transaction_hashes:
            return False  # Już dodana

        self.known_transaction_hashes.add(tx_hash)
        self.transactions.append(tx)
        return True

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
            print("try?")
            if response.status_code == 201:
                nodes = response.json().get("all_nodes", [])
                self.nodes.update(nodes)
                print(f"Zarejestrowano w sieci! Aktualne nody: {self.nodes}")
        except:
            print("Błąd rejestracji w bazowym nodzie.")

    def get_balance(self, node_id):
        balance = 0
        for block in self.chain:
            for tx in block["transactions"]:
                if tx["receiver"] == node_id:
                    balance += tx["amount"]
                elif tx["sender"] == node_id:
                    balance -= tx["amount"]
        return balance

app = Flask(__name__)

@app.route('/mine', methods=['GET'])
def mine_block():
    if blockchain.mining_in_progress:
        return "Mining in progress....", 400

    blockchain.mining_in_progress = True
    
    # Kopanie bloku
    block = blockchain.proof_of_work()

    # Dodajemy blok do łańcucha
    blockchain.create_block(block)

    blockchain.mining_in_progress = False

    # Ogłaszamy nowy blok
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

    if nodes is None or not isinstance(nodes, list):
        return "No node to register", 400

    # Śledzimy, czy dodano coś nowego
    added_nodes = set()

    for node in nodes:
        if node != blockchain.node_address and node not in blockchain.nodes:
            blockchain.nodes.add(node)
            added_nodes.add(node)

    # Ogłaszamy tylko NOWE nody
    if added_nodes:
        blockchain.announce_new_node(added_nodes)

    return {
        "message": "Node(s) registered",
        "added": list(added_nodes),
        "all_nodes": list(blockchain.nodes)
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
    #print(block["previous_hash"])
    previous_block = blockchain.get_previous_block()
    #print(previous_block["hash"])

    # Sprawdzamy, czy blok ma prawidłowy poprzedni hash

    block_copy = block.copy()
    block_copy.pop("hash", None)  # Usuwamy hash przed obliczeniem

    if block['hash'] != blockchain.hash(block_copy):
        return {"message": "Hash nieprawidłowy"}, 400

    if block['hash'][:blockchain.difficulty] != '0' * blockchain.difficulty:
        return {"message": "Blok nie spełnia trudności"}, 400

    if previous_block["hash"] == block["previous_hash"]:
        # Jeśli blok jest poprawny, dodajemy go do łańcucha
        blockchain.chain.append(block)
        blockchain.save_blockchain()

        # Po dodaniu nowego bloku, informujemy inne nody o tym, że blok został zaakceptowany
        # blockchain.announce_new_block(block)

        return {"message": "Block accepted"}, 201
    else:
        return {"message": "Block refused"}, 400

@app.route('/nodes', methods=['GET'])
def get_nodes():
    """Zwraca listę podłączonych nodów"""
    return {"nodes": list(blockchain.nodes)}, 200


@app.route('/transaction', methods=['POST'])
def add_transaction():
    values = request.get_json()
    print(values)
    required_fields = ['sender', 'receiver', 'amount']
    if not all(field in values for field in required_fields):
        return 'Brak wymaganych pól', 400

    # Dodajemy timestamp jeśli nie istnieje (czyli lokalna transakcja)
    if 'timestamp' not in values:
        values['timestamp'] = time.time()

    added = blockchain.add_transaction(values['sender'], values['receiver'], values['amount'], values['timestamp'])

    if not added:
        return 'Transakcja już istnieje', 200

    # Rozgłaszamy tylko NOWĄ transakcję
    for node in blockchain.nodes:
        print(node, blockchain.nodes)
        if node != blockchain.node_address:
            try:
                requests.post(f"http://{node}/transaction", json=values)
            except:
                continue

    return f'Transakcja dodana do bloku', 201

node_id = "test"

if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = int(sys.argv[1])  # Można podać port jako argument

        if len(sys.argv) > 2:
            node_id = sys.argv[2]



    blockchain = Blockchain(f"127.0.0.1:{port}")
    blockchain.node_id = node_id  # zapisz identyfikator w obiekcie

    # 🔁 Uruchom Flask w osobnym wątku
    flask_thread = threading.Thread(target=lambda: app.run(host='127.0.0.1', port=port))
    flask_thread.daemon = True
    flask_thread.start()

    while True:
        print(f"\nWitaj node: {blockchain.node_address}")
        print("1. Wyślij transakcję")
        print("2. Sprawdź saldo")
        print("3. Rozpocznij kopanie")
        print("4. Pokaż blockchain")
        print("5. Lista nodów")
        print("0. Wyjdź")

        choice = input(">>> ")

        if choice == "1":
            receiver = input("Odbiorca (node_id): ")
            try:
                amount = float(input("Kwota: "))
            except ValueError:
                print("❗ Nieprawidłowa kwota.")
                continue
            balance = blockchain.get_balance(blockchain.node_address)
            if amount > balance:
                print(f"❌ Brak środków. Twój balans: {balance}")
            else:
                added = blockchain.add_transaction(blockchain.node_address, receiver, amount)
                print("✅ Transakcja dodana")

                # Rozgłaszamy tylko NOWĄ transakcję
                for node in blockchain.nodes:
                    print(node, blockchain.nodes)
                    if node != blockchain.node_address:
                        try:
                            requests.post(f"http://{node}/transaction", json=blockchain.transactions[-1])
                        except:
                            continue

        elif choice == "2":
            balance = blockchain.get_balance(blockchain.node_address)
            print(f"💰 Twój balans: {balance} coins")
        elif choice == "3":
            print("⛏️  Kopanie bloku...")
            mined_block = blockchain.proof_of_work()
            blockchain.create_block(mined_block)
            blockchain.announce_new_block(mined_block)
            print(f"✅ Wykopano blok #{mined_block['index']}")
        elif choice == "4":
            for block in blockchain.chain:
                print(json.dumps(block, indent=4))
        elif choice == "5":
            print("🌐 Lista nodów:")
            for node in blockchain.nodes:
                print(f" - {node}")
        elif choice == "0":
            print("👋 Zamykanie node'a...")
            break

        else:
            print("❗ Nieznana opcja. Spróbuj ponownie.")


atexit.register(blockchain.save_blockchain)