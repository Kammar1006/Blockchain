import json
import hashlib
import time
import requests

DIFFICULTY = 2  # ile zer musi mieć hash na początku

# 🔹 Wczytaj blockchain
with open("blockchain.json") as f:
    chain = json.load(f)

last_block = chain[-1]
previous_hash = last_block["hash"]

# 🔹 Dwie transakcje z tym samym nadawcą
transactions = [
    {"sender": "Alice", "receiver": "Bob", "amount": 10},
    {"sender": "Alice", "receiver": "Charlie", "amount": 10}
]

# 🔹 Budujemy nowy blok
block = {
    "index": last_block["index"] + 1,
    "timestamp": time.time(),
    "transactions": transactions,
    "nonce": 0,
    "previous_hash": previous_hash
}

# 🔹 Szukanie nonce i hash spełniającego difficulty
print("⛏️ Szukanie poprawnego hasha...")
while True:
    block_string = json.dumps(block, sort_keys=True).encode()
    block_hash = hashlib.sha256(block_string).hexdigest()
    if block_hash.startswith("0" * DIFFICULTY):
        print(f"✅ Hash znaleziony: {block_hash}")
        break
    else:
        block["nonce"] += 1

block["hash"] = block_hash

# 🔹 Wysyłamy blok do node’a
response = requests.post("http://127.0.0.1:5000/new_block", json=block)
print("📡 Odpowiedź serwera:")
print(response.text)
