# Blockchain - Attack and Defence 

## Installations

1. Clone repository:
```
git clone https://github.com/Kammar1006/Blockchain.git
cd Blockchain
```

2. Set up the virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install dependencies:
```
pip install flask, requests, cryptography
```

4. Run Server / Blockchain:
```
python main.py <port> <file_name>
```
Program run on port `<port>` using as keys files: `<file_name>_private.pem` and `<file_name>_public.pem`
If that files no exist program create them when start.

## Use cases:

1. You may use 2 modes: console or website
2. In console mode you have 5 actions:
- Send transaction
- Show balance
- Start Mining
- Show Blockchain
- Show Nodes

3. In Website you may use few endpoints:
- `/nodes` - to show all nodes
- `/chain` - to show chain
- `/mine` - to mine block
- `/balance` - to show balance