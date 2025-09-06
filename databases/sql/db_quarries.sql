CREATE DATABASE central_voter_registry;

CREATE DATABASE voter_registration;

CREATE DATABASE voter_validity;

CREATE DATABASE voter_authentication;

CREATE DATABASE voting_system;

CREATE DATABASE admin_management;

CREATE TABLE IF NOT EXISTS central_voter_registry
(
    id SERIAL PRIMARY KEY,
    nic VARCHAR(20) UNIQUE NOT NULL,
    electoral_division VARCHAR(100) NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS voters
(
    id SERIAL PRIMARY KEY,
    unique_id VARCHAR(50) UNIQUE NOT NULL,
    nic VARCHAR(20) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    electoral_division VARCHAR(100) NOT NULL,
    face_image_path VARCHAR(255) NOT NULL,
    fingerprint_path VARCHAR(255) NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS voters
(
    id SERIAL PRIMARY KEY,
    unique_id VARCHAR(50) UNIQUE NOT NULL,
    nic VARCHAR(20) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    electoral_division VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS voters
(
    id SERIAL PRIMARY KEY,
    unique_id VARCHAR(50) UNIQUE NOT NULL,
    nic VARCHAR(20) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    face_image_path VARCHAR(255) NOT NULL,
    fingerprint_path VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS votes
(
    id SERIAL PRIMARY KEY,
    vote_data JSONB NOT NULL,
    block_hash VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS election_parties
(
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    logo_path VARCHAR(255),
    symbol VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS activity_log
(
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    voter_id VARCHAR(50),
    action VARCHAR(100),
    status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS voting_status
(
    id SERIAL PRIMARY KEY,
    is_active BOOLEAN DEFAULT FALSE,
    start_time TIMESTAMP,
    end_time TIMESTAMP
);

INSERT INTO voting_status (is_active)
VALUES (FALSE) ON CONFLICT DO NOTHING;

