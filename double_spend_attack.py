import json
import hashlib
import time
import requests

DIFFICULTY = 2 

with open("blockchain.json") as f:
    chain = json.load(f)

last_block = chain[-1]
previous_hash = last_block["hash"]

# Tworzymy dwie transakcje z tym samym nadawcą
transactions = [
    {"sender": "fdf583929f2bb0286b97fb75aaa74dd553f404171ff45dc0f997677e2a9a4f97", "receiver": "cfd58b0effdb2f07c2116bdc6e32cb8125d2c6f809cdf98fc03a048b8f8f73dd", "amount": 10},
    {"sender": "fdf583929f2bb0286b97fb75aaa74dd553f404171ff45dc0f997677e2a9a4f97", "receiver": "0027ee8c06d55c5aa5121b10f4ad3458d69c7ae228d49663a258c905f1b7a636", "amount": 10}
]

# Budujemy nowy blok
block = {
    "index": last_block["index"] + 1,
    "timestamp": time.time(),
    "transactions": transactions,
    "nonce": 0,
    "previous_hash": previous_hash
}

print("Szukanie poprawnego hasha...")
while True:
    block_string = json.dumps(block, sort_keys=True).encode()
    block_hash = hashlib.sha256(block_string).hexdigest()
    if block_hash.startswith("0" * DIFFICULTY):
        print(f"Hash znaleziony: {block_hash}")
        break
    else:
        block["nonce"] += 1

block["hash"] = block_hash

# Wysyłamy blok do node
response = requests.post("http://127.0.0.1:5000/new_block", json=block)
print("Odpowiedź serwera:")
print(response.text)
