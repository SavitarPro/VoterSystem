import cv2
import numpy as np
import pickle
import json
import hashlib
import os
from datetime import datetime
import psycopg2
from config import config


class FingerprintRecognizer:
    def __init__(self, model_path):
        self.model = None
        self.label_encoder = None
        self.load_model(model_path)

    def load_model(self, model_path):
        """Load the trained fingerprint model"""
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            self.model = model_data['model']
            self.label_encoder = model_data['label_encoder']
            print("Fingerprint model loaded successfully!")
        except Exception as e:
            print(f"Error loading fingerprint model: {e}")

    def extract_fingerprint_features(self, fingerprint_image):
        """EXACT SAME METHOD AS TRAINING - MUST MATCH EXACTLY"""
        # Resize to consistent size
        fingerprint_resized = cv2.resize(fingerprint_image, (100, 100))

        # Convert to grayscale if needed
        if len(fingerprint_resized.shape) == 3:
            fingerprint_gray = cv2.cvtColor(fingerprint_resized, cv2.COLOR_BGR2GRAY)
        else:
            fingerprint_gray = fingerprint_resized

        # Apply histogram equalization for better contrast
        fingerprint_eq = cv2.equalizeHist(fingerprint_gray)

        # Apply Gaussian blur to reduce noise
        fingerprint_blur = cv2.GaussianBlur(fingerprint_eq, (5, 5), 0)

        # Apply adaptive threshold to enhance ridges
        fingerprint_thresh = cv2.adaptiveThreshold(
            fingerprint_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Extract features using ORB (Oriented FAST and Rotated BRIEF)
        orb = cv2.ORB_create(nfeatures=100)
        keypoints, descriptors = orb.detectAndCompute(fingerprint_thresh, None)

        # If descriptors exist, use them as features
        if descriptors is not None:
            # Flatten descriptors and pad if necessary
            if len(descriptors) > 0:
                # Use the first descriptor
                features = descriptors[0].flatten()
                if len(features) < 100:
                    features = np.pad(features, (0, 100 - len(features)), 'constant')
                return features[:100]  # Return first 100 features

        # Fallback: use the processed image as features
        return fingerprint_thresh.flatten()[:100]

    def recognize_fingerprint(self, image):
        """Recognize fingerprint from image"""
        if self.model is None:
            return None, 0.0

        try:
            # Extract features using the SAME method as training
            features = self.extract_fingerprint_features(image)

            # Ensure we have exactly 100 features
            if len(features) != 100:
                features = features[:100] if len(features) > 100 else np.pad(features, (0, 100 - len(features)),
                                                                             'constant')

            # Reshape for prediction
            features = features.reshape(1, -1)

            # Predict
            prediction = self.model.predict(features)
            confidence = np.max(self.model.predict_proba(features))

            if confidence < 0.6:
                return None, confidence

            predicted_nic = self.label_encoder.inverse_transform(prediction)[0]
            return predicted_nic, confidence

        except Exception as e:
            print(f"Fingerprint recognition error: {e}")
            return None, 0.0


class Blockchain:
    def __init__(self, blockchain_file):
        self.blockchain_file = blockchain_file
        self.chain = self.load_chain()

    def load_chain(self):
        """Load blockchain from file"""
        try:
            with open(self.blockchain_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Initialize new blockchain
            return [self.create_genesis_block()]

    def create_genesis_block(self):
        """Create the first block in the chain"""
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
        """Calculate SHA-256 hash of block"""
        block_string = f"{index}{previous_hash}{json.dumps(votes)}{timestamp}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def add_vote(self, voter_nic):
        """Add a vote to the blockchain (only stores that someone voted, not who they voted for)"""
        # Check if voter has already voted
        for block in self.chain:
            for vote in block['votes']:
                if vote['voter_nic'] == voter_nic:
                    return False

        # Create new vote (only store NIC and timestamp for anonymity)
        vote_data = {
            'voter_nic': voter_nic,
            'timestamp': str(datetime.now()),
            'vote_id': f"vote_{len(self.chain)}_{voter_nic}"
        }

        # Add to current block or create new block
        if len(self.chain[-1]['votes']) >= 10:  # Create new block after 10 votes
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
            # Recalculate hash for current block
            self.chain[-1]['hash'] = self.calculate_hash(
                self.chain[-1]['index'],
                self.chain[-1]['previous_hash'],
                self.chain[-1]['votes'],
                self.chain[-1]['timestamp']
            )

        self.save_chain(self.chain)
        return True

    def save_chain(self, chain):
        """Save blockchain to file"""
        os.makedirs(os.path.dirname(self.blockchain_file), exist_ok=True)
        with open(self.blockchain_file, 'w') as f:
            json.dump(chain, f, indent=2)

    def get_vote_count(self):
        """Get total vote count"""
        total = 0
        for block in self.chain:
            total += len(block['votes'])
        return total

    def has_voted(self, voter_nic):
        """Check if voter has already voted"""
        for block in self.chain:
            for vote in block['votes']:
                if vote['voter_nic'] == voter_nic:
                    return True
        return False


class VoteManager:
    def __init__(self):
        self.registration_pool = config.registration_pool
        self.vote_pool = config.vote_pool
        self.voter_auth_pool = config.voter_auth_pool  # New connection pool
        self.blockchain = Blockchain(config.BLOCKCHAIN_FILE)
        self.init_databases()

    def init_databases(self):
        """Initialize vote database tables"""
        self.init_vote_db()

    def init_vote_db(self):
        """Initialize vote database tables"""
        conn = self.vote_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Vote sessions table
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

                # Anonymous vote storage table (stores party votes without voter linkage)
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
        """Get voter information"""
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
        """Check if voter has APPROVED status in voter_auth_db"""
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
        """Cast a vote using blockchain and store party vote anonymously"""
        if self.blockchain.has_voted(voter_nic):
            return False, "Voter has already voted"

        # Check if voter is approved in auth database
        if not self.check_voter_auth_status(voter_nic):
            return False, "Voter not approved for voting"

        # Add to blockchain (proves voter participated)
        blockchain_success = self.blockchain.add_vote(voter_nic)
        if not blockchain_success:
            return False, "Failed to record vote in blockchain"

        # Store anonymous vote (what was voted for, not who voted)
        conn = self.vote_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Get the latest block hash for reference
                latest_block_hash = self.blockchain.chain[-1]['hash']

                # Insert into anonymous_votes table
                cursor.execute('''
                               INSERT INTO anonymous_votes (party_code, block_hash)
                               VALUES (%s, %s) RETURNING vote_id
                               ''', (party_code, latest_block_hash))

                # FIXED: Update vote_sessions without ON CONFLICT
                # First check if session exists
                cursor.execute('SELECT session_id FROM vote_sessions WHERE voter_nic = %s', (voter_nic,))
                existing_session = cursor.fetchone()

                if existing_session:
                    # Update existing session
                    cursor.execute('''
                                   UPDATE vote_sessions
                                   SET end_time = CURRENT_TIMESTAMP,
                                       status   = 'completed'
                                   WHERE voter_nic = %s
                                   ''', (voter_nic,))
                else:
                    # Insert new session
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
        """Get voting statistics - only total votes for anonymity"""
        total_votes = self.blockchain.get_vote_count()

        return {
            'total_votes': total_votes
        }

    def validate_officer_id(self, officer_id):
        """Validate if officer ID is authorized for override"""
        return officer_id in config.AUTHORIZED_OFFICER_IDS