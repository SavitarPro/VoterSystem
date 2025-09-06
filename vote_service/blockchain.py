import hashlib
import json
import time


class SimpleBlockchain:
    def __init__(self):
        self.chain = []
        self.create_block(proof=1, previous_hash='0', vote_data={})

    def create_block(self, proof, previous_hash, vote_data):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'proof': proof,
            'previous_hash': previous_hash,
            'vote_data': vote_data
        }
        block['hash'] = self.hash(block)
        self.chain.append(block)
        return block

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def add_vote(self, vote_data):
        previous_block = self.chain[-1]
        previous_hash = previous_block['hash']
        proof = previous_block['proof'] + 1
        new_block = self.create_block(proof, previous_hash, vote_data)
        return new_block



blockchain = SimpleBlockchain()