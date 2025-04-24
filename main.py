import hashlib
import time
import json
from flask import Flask, request
import os, sys
import atexit
import requests
import copy
import threading

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

def load_public_key_from_pem(pem_string):
    return serialization.load_pem_public_key(pem_string.encode('utf-8'))

def get_node_id_from_public_key(public_key):
    # Serializujemy klucz publiczny do bajtów
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    # Hashujemy
    pub_hash = hashlib.sha256(pub_bytes).hexdigest()
    return pub_hash

def load_known_nodes(file_path="known_nodes.txt"):
    if not os.path.exists(file_path):
        print("📄 Plik z nodami nie istnieje. Używam domyślnego noda.")
        return ["127.0.0.1:5000"]
    
    with open(file_path, "r") as f:
        nodes = [line.strip() for line in f if line.strip()]
    
    return nodes or ["127.0.0.1:5000"]

class Blockchain:
    def __init__(self, node_address, node_id, public_key, public_key_pem, known_nodes):
        self.chain = []
        self.transactions = []
        self.reward = 50
        self.difficulty = 2
        self.mining_in_progress = False
        self.nodes = {}
        self.node_address = node_address
        self.known_transaction_hashes = set()
        self.node_id = node_id
        self.public_key = public_key
        self.public_key_pem = public_key_pem
        
        self.load_blockchain()
        if not self.chain:
            genesis_block = self.proof_of_work()
            self.create_block(genesis_block)

        self.nodes[node_id] = {
            "ip": self.node_address,
            "public_key": public_key_pem
        }
        
        self.register_with_known_nodes(known_nodes)

    
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
            
            transaction_data = {
                'sender': "*",
                'receiver': self.node_id,
                'amount': self.reward,
                'timestamp': time.time()
            }
            copy_list.append(transaction_data)

            tx = json.dumps(transaction_data, sort_keys=True)

            signature = private_key.sign(
                tx.encode(),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )

            #signature = bytes.fromhex(signature)

            transaction_data['signature'] = signature.hex()
            
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

    def add_transaction(self, sender, receiver, amount, signature, timestamp=None):
        if timestamp is None:
            timestamp = time.time()

        tx = {
            'sender': sender,
            'receiver': receiver,
            'amount': amount,
            'timestamp': timestamp
        }

        tx_data = json.dumps(tx, sort_keys=True)
        
        # Weryfikacja podpisu transakcji
        if not self.verify_signature(sender, bytes.fromhex(str(signature)), tx_data):
            print("❌ Nieprawidłowy podpis transakcji!")
            return False

        # Tworzenie hash transakcji
        tx_hash = self.transaction_hash(tx)

        tx["signature"] = signature

        if tx_hash in self.known_transaction_hashes:
            return False  # Już dodana

        self.known_transaction_hashes.add(tx_hash)
        self.transactions.append(tx)
        return True
    
    def verify_signature(self, sender, signature, transaction_data):
        try:
            public_key = load_public_key_from_pem(self.nodes[sender]["public_key"])
            public_key.verify(
                signature,
                transaction_data.encode(),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False

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

        for node_id, info in self.nodes.items():
            if info["ip"] == self.node_address:
                continue
            try:
                response = requests.get(f"http://{info['ip']}/chain")
                if response.status_code == 200:
                    length = response.json()["length"]
                    chain = response.json()["chain"]
                    if length > max_length and self.is_chain_valid(chain):
                        max_length = length
                        longest_chain = chain
            except:
                continue
            
        if longest_chain:
            self.chain = longest_chain
            self.save_blockchain()
            return True
        return False

    def announce_updated_chain(self):
        for node_id, info in self.nodes.items():
            if info["ip"] == self.node_address:
                continue
            try:
                requests.get(f"http://{info['ip']}/sync")
            except:
                continue

    def announce_new_block(self, block):
        for node_id, info in self.nodes.items():
            if info["ip"] == self.node_address:
                continue
            try:
                requests.post(f"http://{info['ip']}/new_block", json=block)
            except:
                continue  # Ignorujemy błędy

    def announce_new_node(self, new_nodes):
        for node_id, info in self.nodes.items():
            if info["ip"] == self.node_address:
                continue
            try:
                requests.post(
                    f"http://{info['ip']}/register_node",
                    json={"nodes": new_nodes}
                )
            except:
                continue

    def register_with_known_nodes(self, known_nodes):
        my_node_data = {
            self.node_id: {
                "ip": self.node_address,
                "public_key": self.public_key_pem
            }
        }

        for node in known_nodes:
            if node == self.node_address:
                continue  # Nie rejestrujemy się u siebie

            try:
                response = requests.post(f"http://{node}/register_node", json={"nodes": [my_node_data]})
                if response.status_code == 201:
                    nodes = response.json().get("all_nodes", {})
                    self.nodes.update(nodes)
                    print(f"✅ Zarejestrowano w: {node}. Zaktualizowane nody: {list(self.nodes.keys())}")
            except Exception as e:
                print(f"❌ Nie udało się zarejestrować w {node}: {e}")


    def get_balance(self, node_id):
        balance = 0
        for block in self.chain:
            for tx in block["transactions"]:
                if tx["receiver"] == node_id:
                    balance += tx["amount"]
                elif tx["sender"] == node_id:
                    balance -= tx["amount"]
        return balance

    def get_temp_balance(self, node_id):
        balance = self.get_balance(node_id)

        for tx in self.transactions:
            if tx["receiver"] == node_id:
                balance += tx["amount"]
            elif tx["sender"] == node_id:
                balance -= tx["amount"]

        return balance

    def save_known_nodes(self, file_path="known_nodes.txt"):
        try:
            with open(file_path, "w") as f:
                for node_id, node_info in self.nodes.items():
                    f.write(f"{node_info['ip']}\n")
            print("💾 Zapisano znane nody do pliku.")
        except Exception as e:
            print("❌ Błąd zapisu nodów do pliku:", e)

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

    if not nodes or not isinstance(nodes, list):
        return "No node to register", 400

    added_nodes = {}

    for entry in nodes:
        for node_id, node_data in entry.items():
            if node_id not in blockchain.nodes:
                blockchain.nodes[node_id] = node_data
                added_nodes[node_id] = node_data

    if added_nodes:
        blockchain.announce_new_node([{nid: data} for nid, data in added_nodes.items()])

    return {
        "message": "Node(s) registered",
        "added": added_nodes,
        "all_nodes": blockchain.nodes
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
        blockchain.transactions = []
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

@app.route('/balance', methods = ['GET'])
def show_balance():
    balance = blockchain.get_balance(blockchain.node_id)
    return (f"💰 Twój balans: {balance} coins")


@app.route('/transaction', methods=['POST'])
def add_transaction():
    values = request.get_json()
    required_fields = ['sender', 'receiver', 'amount', 'signature']
    if not all(field in values for field in required_fields):
        return 'Brak wymaganych pól', 400

    # Dodajemy timestamp jeśli nie istnieje (czyli lokalna transakcja)
    if 'timestamp' not in values:
        values['timestamp'] = time.time()

    added = blockchain.add_transaction(values['sender'], values['receiver'], values['amount'], values['signature'], values['timestamp'])

    if not added:
        return 'Transakcja już istnieje', 200

    # Rozgłaszamy tylko NOWĄ transakcję
    for node_id, node_data in blockchain.nodes.items():
        if node_data["ip"] != blockchain.node_address:
            try:
                requests.post(f"http://{node_data['ip']}/transaction", json=values)
            except:
                continue

    return f'Transakcja dodana do bloku', 201


node_id = "test"

if __name__ == '__main__':
    

    # Załaduj nazwę bazową klucza z argv
    key_name = "default_key"
    if len(sys.argv) > 2:
        key_name = sys.argv[2]
        port = sys.argv[1]

    priv_path = f"{key_name}_private.pem"
    pub_path = f"{key_name}_public.pem"

    # Sprawdź czy pliki istnieją — jeśli nie, generujemy nowe klucze
    if not os.path.exists(priv_path) or not os.path.exists(pub_path):
        print(f"🔐 Generuję nowe klucze dla: {key_name}")

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Zapisz klucz prywatny
        with open(priv_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Zapisz klucz publiczny
        public_key = private_key.public_key()
        with open(pub_path, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))

    else:
        # Załaduj istniejące klucze
        with open(priv_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

        with open(pub_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')  # <-- zamieniamy na string

    print(f"🔑 Załadowano klucze: {key_name}")


    blockchain = Blockchain(f"127.0.0.1:{port}", get_node_id_from_public_key(public_key), public_key, public_key_pem, load_known_nodes())

    # 🔁 Uruchom Flask w osobnym wątku
    flask_thread = threading.Thread(target=lambda: app.run(host='127.0.0.1', port=port))
    flask_thread.daemon = True
    flask_thread.start()

    while True:
        print(f"\nWitaj node: {blockchain.node_id}")
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
            temp_balance = blockchain.get_temp_balance(blockchain.node_id)
            if amount > temp_balance:
                print(f"❌ Brak środków. Twój balans (z nierozliczonymi transakcjami): {temp_balance}")
            else:
                
                timestamp = time.time()
                transaction_data = {"sender": blockchain.node_id, "receiver": receiver, "amount": amount, "timestamp": timestamp}

                transaction_data = json.dumps(transaction_data, sort_keys=True)

                signature = private_key.sign(
                    transaction_data.encode(),
                    padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                    hashes.SHA256()
                )

                signature = signature.hex()

                print(signature)

                added = blockchain.add_transaction(blockchain.node_id, receiver, amount, signature, timestamp)
                print("✅ Transakcja dodana")

                # Rozgłaszamy tylko NOWĄ transakcję
                for node_id, node_data in blockchain.nodes.items():
                    if node_data["ip"] != blockchain.node_address:
                        print(node_id, node_data)
                        try:
                            requests.post(f"http://{node_data["ip"]}/transaction", json=blockchain.transactions[-1])
                        except:
                            continue

        elif choice == "2":
            balance = blockchain.get_balance(blockchain.node_id)
            temp_balance = blockchain.get_temp_balance(blockchain.node_id)
            print(f"💰 Twój balans: {balance} coins")
            print(f"🧮 Tymczasowy balans (z nierozliczonymi transakcjami): {temp_balance}")
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
            for node_id, info in blockchain.nodes.items():
                print(f" - {node_id}")
                print(f"{info["ip"]}")
        elif choice == "0":
            print("👋 Zamykanie node'a...")
            break

        else:
            print("❗ Nieznana opcja. Spróbuj ponownie.")


atexit.register(blockchain.save_blockchain)
atexit.register(blockchain.save_known_nodes)