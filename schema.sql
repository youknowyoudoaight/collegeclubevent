-- College Club Event Management System
-- Run: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS club_events_db;
USE club_events_db;

-- Admins
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clubs
CREATE TABLE IF NOT EXISTS clubs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    club_name VARCHAR(150) NOT NULL,
    description TEXT,
    contact_person VARCHAR(100),
    email VARCHAR(150),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events
CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    club_id INT NOT NULL,
    event_name VARCHAR(200) NOT NULL,
    event_date DATE NOT NULL,
    venue VARCHAR(200),
    max_participants INT DEFAULT 100,
    description TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

-- Participants
CREATE TABLE IF NOT EXISTS participants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20),
    college_branch VARCHAR(100),
    year VARCHAR(20)
);

-- Registrations
CREATE TABLE IF NOT EXISTS registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    participant_id INT NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('registered', 'attended', 'certificate_issued') DEFAULT 'registered',
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE,
    UNIQUE KEY unique_reg (event_id, participant_id)
);

-- Notices
CREATE TABLE IF NOT EXISTS notices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    admin_id INT,
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

-- Settings
CREATE TABLE IF NOT EXISTS settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(100) NOT NULL UNIQUE,
    value TEXT
);

-- Default college name
INSERT IGNORE INTO settings (`key`, value) VALUES ('college_name', 'My College');

-- Sample clubs
INSERT IGNORE INTO clubs (id, club_name, description, contact_person, email) VALUES
(1, 'Tech Club', 'Technology and innovation club', 'Dr. Smith', 'tech@college.edu'),
(2, 'Cultural Club', 'Arts, music and cultural activities', 'Prof. Rao', 'cultural@college.edu'),
(3, 'Sports Club', 'All sports and fitness activities', 'Coach Kumar', 'sports@college.edu');

-- Sample events (future dates)
INSERT IGNORE INTO events (id, club_id, event_name, event_date, venue, max_participants, description) VALUES
(1, 1, 'Hackathon 2026', '2026-06-15', 'Main Auditorium', 200, 'Annual 24-hour hackathon'),
(2, 2, 'Cultural Fest', '2026-07-20', 'Open Air Theatre', 500, 'Annual cultural festival'),
(3, 3, 'Sports Day', '2026-08-10', 'Sports Ground', 300, 'Annual sports day event'),
(4, 1, 'Tech Talk 2025', '2025-12-10', 'Seminar Hall', 100, 'Guest lecture series');

-- Sample participants
INSERT IGNORE INTO participants (id, name, email, phone, college_branch, year) VALUES
(1, 'Alice Johnson', 'alice@student.edu', '9876543210', 'Computer Science', '3rd Year'),
(2, 'Bob Williams', 'bob@student.edu', '9876543211', 'Electronics', '2nd Year'),
(3, 'Carol Davis', 'carol@student.edu', '9876543212', 'Mechanical', '4th Year');

-- Sample registrations
INSERT IGNORE INTO registrations (event_id, participant_id, status) VALUES
(1, 1, 'registered'),
(1, 2, 'attended'),
(2, 1, 'registered'),
(4, 3, 'certificate_issued');

-- Sample notices
INSERT IGNORE INTO notices (id, title, message, admin_id) VALUES
(1, 'Welcome to the new portal', 'The College Club Event Management System is now live. All clubs can register their events here.', NULL),
(2, 'Hackathon registrations open', 'Registrations for Hackathon 2026 are now open. Limited seats available!', NULL);

-- NOTE: The default admin is seeded by seed_admin.py (requires werkzeug hashing)
-- Default: email=admin@clubevents.com  password=admin123
