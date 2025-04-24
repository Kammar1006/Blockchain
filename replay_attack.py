import requests
import json

# Adres istniejącego węzła
node_address = "http://127.0.0.1:5000"

# Transakcja, którą chcemy powtórzyć (wcześniej zaakceptowana)
replayed_transaction = {
    "sender": "*",
    "receiver": "f08c44a5cbe4aacf0581321e49af77f0fe8ed022250ef913dba54e191072065f",
    "amount": 10,
    "timestamp": 1744148153.303206,  # Używamy timestampu z istniejącej transakcji
    "signature": "FAKE_SIGNATURE"  # Podpis musi być zgodny z oryginalnym
}

# Wysyłamy transakcję ponownie do sieci
print("🔁 Wysyłanie powtórzonej transakcji...")
response = requests.post(f"{node_address}/transaction", json=replayed_transaction)

# Wyświetlamy odpowiedź serwera
if response.status_code == 201:
    print("✅ Transakcja zaakceptowana przez sieć.")
else:
    print(f"❌ Sieć odrzuciła transakcję: {response.text}")
