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
    {
        "sender": "fdf583929f2bb0286b97fb75aaa74dd553f404171ff45dc0f997677e2a9a4f97",
        "receiver": "f08c44a5cbe4aacf0581321e49af77f0fe8ed022250ef913dba54e191072065f",
        "amount": 600.0,
        "timestamp": 1745527116.8313453,
        "signature": "56ae36adefebf74b3b1602f57f48546b194a3c1afb9419f661f3281214f0832f2ab544b3e11c92524dc75d0782403af510f4de03906dc09b70d3bb3ce5043636ba511ae6d38011b193f9e8a0f33c5468a94966e235c036b8014ad2a4ea16f46c06efd75e021d81a4c7e7b025dd90dc2a655ccd48475589de6a466f87c2a4823fef3788a2e8ef2ef018ba66483695ec888d1bd9f0bfe0870f2ace0f3c03b596ff89d1ebd0ff612924d9baadcf091d84ed9a1a6a55747a9c37e10d18ec283d4dc81fc0284e4aae9916e33d92fae5f73cd966577e255e0815e343a9c00e216d1716a8a1322e5efe834b61f68732b77af66a27901e1bff00b7f8c2c401a64842930b"
    },
    {
        "sender": "fdf583929f2bb0286b97fb75aaa74dd553f404171ff45dc0f997677e2a9a4f97",
        "receiver": "cfd58b0effdb2f07c2116bdc6e32cb8125d2c6f809cdf98fc03a048b8f8f73dd",
        "amount": 600.0,
        "timestamp": 1745527295.423557,
        "signature": "787cfc7acb96f572caeb890d07ed6b93706d150a84ce7a3e1509859ce4f699948746fd52558f7925572ca0d430dee801ccbce9cfb6762b755c2572a8ba9426be9fc2c7c5565f96d7250de147970ab44149cb84bd13163f103df5174feb1c682088e0ce17e53623d09ba4274754dc01eb8a09212ac199c5d6adc65915280d7f8bf14abcdc9b277c54b6a4b55860f2ed2d6aa5b0ee1214c52c9476b2177e86b9b92267104427a05ca7c047ed32c174c8443c43d55c5dc1623bca45c50d33a021ba6c31eca8e6ff0b0b4be25a578fe806ca78072add20668d0835307511c852a00e8915e340b07a8d8d25f0ff2405e3968346b7e04da932fe85c15617c46d037e57"
    }
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
