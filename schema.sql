DROP DATABASE IF EXISTS voting_system;
CREATE DATABASE voting_system;
USE voting_system;

CREATE TABLE students (
    student_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE admins (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE elections (
    election_id INT AUTO_INCREMENT PRIMARY KEY,
    election_name VARCHAR(100) NOT NULL,
    election_status VARCHAR(20) NOT NULL DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE candidates (
    candidate_id INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    votes INT NOT NULL DEFAULT 0,
    FOREIGN KEY (election_id) REFERENCES elections(election_id)
);

-- Deliberately does NOT store candidate_id: the tally lives in candidates.votes,
-- so a ballot's choice is never persisted alongside the voter's identity (ballot secrecy).
-- This row only proves a student voted in an election, to enforce one vote per student.
CREATE TABLE cast_vote (
    vote_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL,
    election_id INT NOT NULL,
    vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_student_election (student_id, election_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (election_id) REFERENCES elections(election_id)
);

CREATE TABLE election_results (
    result_id INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    election_name VARCHAR(100) NOT NULL,
    candidate_name VARCHAR(100) NOT NULL,
    votes INT NOT NULL DEFAULT 0,
    result_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
