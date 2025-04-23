import requests

# Adres istniejącego węzła
node_address = "http://127.0.0.1:5000"

# Tworzymy fałszywe węzły
fake_nodes = [
    {"fake_node_1": {"ip": "127.0.0.2:5000", "public_key": "FAKE_PUBLIC_KEY_1"}},
    {"fake_node_2": {"ip": "127.0.0.3:5000", "public_key": "FAKE_PUBLIC_KEY_2"}},
    {"fake_node_3": {"ip": "127.0.0.4:5000", "public_key": "FAKE_PUBLIC_KEY_3"}}
]

# Wysyłamy fałszywe węzły do istniejącego węzła
print("🔗 Dodawanie fałszywych węzłów...")
response = requests.post(f"{node_address}/register_node", json={"nodes": fake_nodes})

# Wyświetlamy odpowiedź serwera
if response.status_code == 201:
    print("✅ Fałszywe węzły zostały dodane:")
    print(response.json())
else:
    print("❌ Nie udało się dodać fałszywych węzłów:")
    print(response.text)
