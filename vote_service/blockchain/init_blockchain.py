import json
import hashlib
from datetime import datetime


def create_genesis_block():
    """Create the genesis block for the blockchain"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    # Calculate hash for genesis block
    block_data = f"0{timestamp}[]0"
    block_hash = hashlib.sha256(block_data.encode()).hexdigest()

    genesis_block = {
        "index": 0,
        "timestamp": timestamp,
        "votes": [],
        "previous_hash": "0",
        "hash": block_hash
    }

    return [genesis_block]


def main():
    """Initialize the blockchain file"""
    blockchain = create_genesis_block()

    # Create blockchain directory if it doesn't exist
    import os

    # Save to file
    with open('vote_chain.json', 'w') as f:
        json.dump(blockchain, f, indent=2)

    print("Blockchain initialized successfully!")
    print(f"Genesis block hash: {blockchain[0]['hash']}")


if __name__ == "__main__":
    main()