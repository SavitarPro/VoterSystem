import cv2
import numpy as np
import pickle
import json
import hashlib
import tensorflow as tf
import os
from datetime import datetime
import psycopg2
from config import config


class FingerprintRecognizer:
    def __init__(self, model_path):
        self.model = None
        self.label_encoder = None
        self.input_shape = None
        self.load_model(model_path)

    def load_model(self, model_path):
        
        try:
            
            self.model = tf.keras.models.load_model(model_path.replace('.pkl', '.h5'))

            
            metadata_path = model_path.replace('.pkl', '_metadata.pkl')
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)

            self.label_encoder = metadata['label_encoder']
            self.input_shape = metadata['input_shape']
            print("Fingerprint CNN model loaded successfully!")
        except Exception as e:
            print(f"Error loading fingerprint model: {e}")

    def extract_fingerprint_features_cnn(self, fingerprint_image):
        
        
        fingerprint_resized = cv2.resize(fingerprint_image, (self.input_shape[0], self.input_shape[1]))

        
        if len(fingerprint_resized.shape) == 3:
            fingerprint_gray = cv2.cvtColor(fingerprint_resized, cv2.COLOR_BGR2GRAY)
        else:
            fingerprint_gray = fingerprint_resized

        
        fingerprint_eq = cv2.equalizeHist(fingerprint_gray)

        
        fingerprint_normalized = fingerprint_eq / 255.0

        
        fingerprint_normalized = np.expand_dims(fingerprint_normalized, axis=-1)

        return fingerprint_normalized

    def recognize_fingerprint(self, image):
        
        if self.model is None:
            return None, 0.0

        try:
            
            processed_image = self.extract_fingerprint_features_cnn(image)

            
            processed_image = np.expand_dims(processed_image, axis=0)

            
            predictions = self.model.predict(processed_image, verbose=0)
            confidence = np.max(predictions)
            predicted_class = np.argmax(predictions, axis=1)

            if confidence < 0.6:  
                return None, confidence

            predicted_nic = self.label_encoder.inverse_transform(predicted_class)[0]
            return predicted_nic, confidence

        except Exception as e:
            print(f"Fingerprint recognition error: {e}")
            return None, 0.0


class Blockchain:
    def __init__(self, blockchain_file):
        self.blockchain_file = blockchain_file
        self.chain = self.load_chain()

    def load_chain(self):
        
        try:
            with open(self.blockchain_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            
            return [self.create_genesis_block()]

    def create_genesis_block(self):
        
        genesis_block = {
            'index': 0,
            'timestamp': str(datetime.now()),
            'votes': [],
            'previous_hash': '0',
            'hash': self.calculate_hash(0, '0', [], str(datetime.now()))
        }
        self.save_chain([genesis_block])
        return genesis_block

    def calculate_hash(self, index, previous_hash, votes, timestamp):
        
        block_string = f"{index}{previous_hash}{json.dumps(votes)}{timestamp}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def add_vote(self, voter_nic):
        
        
        for block in self.chain:
            for vote in block['votes']:
                if vote['voter_nic'] == voter_nic:
                    return False

        
        vote_data = {
            'voter_nic': voter_nic,
            'timestamp': str(datetime.now()),
            'vote_id': f"vote_{len(self.chain)}_{voter_nic}"
        }

        
        if len(self.chain[-1]['votes']) >= 10:  
            new_block = {
                'index': len(self.chain),
                'timestamp': str(datetime.now()),
                'votes': [vote_data],
                'previous_hash': self.chain[-1]['hash'],
                'hash': self.calculate_hash(len(self.chain), self.chain[-1]['hash'], [vote_data], str(datetime.now()))
            }
            self.chain.append(new_block)
        else:
            self.chain[-1]['votes'].append(vote_data)
            
            self.chain[-1]['hash'] = self.calculate_hash(
                self.chain[-1]['index'],
                self.chain[-1]['previous_hash'],
                self.chain[-1]['votes'],
                self.chain[-1]['timestamp']
            )

        self.save_chain(self.chain)
        return True

    def save_chain(self, chain):
        
        os.makedirs(os.path.dirname(self.blockchain_file), exist_ok=True)
        with open(self.blockchain_file, 'w') as f:
            json.dump(chain, f, indent=2)

    def get_vote_count(self):
        
        total = 0
        for block in self.chain:
            total += len(block['votes'])
        return total

    def has_voted(self, voter_nic):
        
        for block in self.chain:
            for vote in block['votes']:
                if vote['voter_nic'] == voter_nic:
                    return True
        return False


class VoteManager:
    def __init__(self):
        self.registration_pool = config.registration_pool
        self.vote_pool = config.vote_pool
        self.voter_auth_pool = config.voter_auth_pool  
        self.blockchain = Blockchain(config.BLOCKCHAIN_FILE)
        self.init_databases()

    def init_databases(self):
        
        self.init_vote_db()

    def init_vote_db(self):
        
        conn = self.vote_pool.getconn()
        try:
            with conn.cursor() as cursor:
                
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS vote_sessions
                               (
                                   session_id
                                   SERIAL
                                   PRIMARY
                                   KEY,
                                   voter_nic
                                   VARCHAR
                               (
                                   20
                               ) NOT NULL,
                                   start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   end_time TIMESTAMP,
                                   status VARCHAR
                               (
                                   20
                               ) DEFAULT 'active'
                                   )
                               ''')

                
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS anonymous_votes
                               (
                                   vote_id
                                   SERIAL
                                   PRIMARY
                                   KEY,
                                   party_code
                                   VARCHAR
                               (
                                   10
                               ) NOT NULL,
                                   vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   block_hash VARCHAR
                               (
                                   64
                               ) NOT NULL
                                   )
                               ''')
                conn.commit()
        except Exception as e:
            print(f"Error initializing vote DB: {e}")
        finally:
            self.vote_pool.putconn(conn)

    def get_voter_info(self, nic):
        
        conn = self.registration_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                               SELECT nic, full_name, electoral_division
                               FROM voters
                               WHERE nic = %s
                               ''', (nic,))
                result = cursor.fetchone()
                if result:
                    return {
                        'nic': result[0],
                        'full_name': result[1],
                        'electoral_division': result[2]
                    }
        except Exception as e:
            print(f"Error getting voter info: {e}")
        finally:
            self.registration_pool.putconn(conn)
        return None

    def check_voter_auth_status(self, nic):
        
        if not self.voter_auth_pool:
            return False

        conn = self.voter_auth_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                               SELECT status
                               FROM authentications
                               WHERE nic = %s
                               ORDER BY auth_time DESC LIMIT 1
                               ''', (nic,))
                result = cursor.fetchone()
                if result:
                    return result[0] == 'APPROVED'
                return False
        except Exception as e:
            print(f"Error checking voter auth status: {e}")
            return False
        finally:
            self.voter_auth_pool.putconn(conn)

    def cast_vote(self, voter_nic, party_code):
        
        if self.blockchain.has_voted(voter_nic):
            return False, "Voter has already voted"

        
        if not self.check_voter_auth_status(voter_nic):
            return False, "Voter not approved for voting"

        
        blockchain_success = self.blockchain.add_vote(voter_nic)
        if not blockchain_success:
            return False, "Failed to record vote in blockchain"

        
        conn = self.vote_pool.getconn()
        try:
            with conn.cursor() as cursor:
                
                latest_block_hash = self.blockchain.chain[-1]['hash']

                
                cursor.execute('''
                               INSERT INTO anonymous_votes (party_code, block_hash)
                               VALUES (%s, %s) RETURNING vote_id
                               ''', (party_code, latest_block_hash))

                
                
                cursor.execute('SELECT session_id FROM vote_sessions WHERE voter_nic = %s', (voter_nic,))
                existing_session = cursor.fetchone()

                if existing_session:
                    
                    cursor.execute('''
                                   UPDATE vote_sessions
                                   SET end_time = CURRENT_TIMESTAMP,
                                       status   = 'completed'
                                   WHERE voter_nic = %s
                                   ''', (voter_nic,))
                else:
                    
                    cursor.execute('''
                                   INSERT INTO vote_sessions (voter_nic, end_time, status)
                                   VALUES (%s, CURRENT_TIMESTAMP, 'completed')
                                   ''', (voter_nic,))

                conn.commit()
                return True, "Vote recorded successfully"
        except Exception as e:
            print(f"Error storing anonymous vote: {e}")
            conn.rollback()
            return False, "Failed to store vote"
        finally:
            self.vote_pool.putconn(conn)

    def get_vote_stats(self):
        
        total_votes = self.blockchain.get_vote_count()

        return {
            'total_votes': total_votes
        }

    def validate_officer_id(self, officer_id):
        
        return officer_id in config.AUTHORIZED_OFFICER_IDS