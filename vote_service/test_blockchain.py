from blockchain import SimpleBlockchain

def test_calculate_hash_consistency():
    blockchain = SimpleBlockchain()

    test_block = {
        'index': 1,
        'timestamp': '2023-01-01T00:00:00',
        'proof': 1,
        'previous_hash': '0',
        'vote_data': [{'nic': 'test_nic'}]
    }

    hash1 = blockchain.hash(test_block)
    hash2 = blockchain.hash(test_block)

    assert len(hash1) == 64
    assert hash1 == hash2