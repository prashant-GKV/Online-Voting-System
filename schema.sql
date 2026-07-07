-- PostgreSQL schema for CampusVote.
-- Run this against your database once. On hosted Postgres (Supabase / Neon)
-- paste it into the SQL editor; locally: psql "<connection-string>" -f schema.sql
-- The database itself already exists on hosted providers, so we do NOT create it here.

CREATE TABLE IF NOT EXISTS students (
    student_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admins (
    admin_id SERIAL PRIMARY KEY,
    username VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS elections (
    election_id SERIAL PRIMARY KEY,
    election_name VARCHAR(100) NOT NULL,
    election_status VARCHAR(20) NOT NULL DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidates (
    candidate_id SERIAL PRIMARY KEY,
    election_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    votes INT NOT NULL DEFAULT 0,
    FOREIGN KEY (election_id) REFERENCES elections(election_id)
);

-- Deliberately does NOT store candidate_id: the tally lives in candidates.votes,
-- so a ballot's choice is never persisted alongside the voter's identity (ballot secrecy).
-- This row only proves a student voted in an election, to enforce one vote per student.
CREATE TABLE IF NOT EXISTS cast_vote (
    vote_id SERIAL PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL,
    election_id INT NOT NULL,
    vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uniq_student_election UNIQUE (student_id, election_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (election_id) REFERENCES elections(election_id)
);

CREATE TABLE IF NOT EXISTS election_results (
    result_id SERIAL PRIMARY KEY,
    election_id INT NOT NULL,
    election_name VARCHAR(100) NOT NULL,
    candidate_name VARCHAR(100) NOT NULL,
    votes INT NOT NULL DEFAULT 0,
    result_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
