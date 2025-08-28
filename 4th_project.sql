-- =====================================================
-- 4th Project Database Schema
-- GitHub Repository Analyzer with AI Chatbot
-- Version: 2.0
-- Last Updated: 2024
-- =====================================================

-- =====================================================
-- Database Configuration
-- =====================================================
-- Drop existing database (WARNING: This will delete all data!)
-- Comment out the DROP line if you want to preserve existing data
-- DROP DATABASE IF EXISTS 4th_project;

-- Create database with UTF-8 support
CREATE DATABASE IF NOT EXISTS 4th_project 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE 4th_project;

-- =====================================================
-- 1. User Management Table
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    
    -- GitHub OAuth fields
    is_github_user BOOLEAN DEFAULT FALSE,
    github_id VARCHAR(255),
    github_username VARCHAR(255),
    github_token VARCHAR(255),
    github_avatar_url VARCHAR(255),
    
    -- Google OAuth fields
    is_google_user BOOLEAN DEFAULT FALSE,
    google_id VARCHAR(255),
    google_username VARCHAR(255),
    google_token VARCHAR(255),
    google_avatar_url VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    
    -- Indexes for performance
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_github_id (github_id),
    INDEX idx_google_id (google_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='User accounts table';

-- =====================================================
-- 2. Chat Session Management Table
-- =====================================================
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    repo_url VARCHAR(255),
    token VARCHAR(255),
    name VARCHAR(255),
    display_order INT DEFAULT 0,
    files_data LONGTEXT COMMENT 'JSON data of analyzed files',
    directory_structure TEXT COMMENT 'Repository directory structure',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Indexes for performance
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Chat sessions for repository analysis';

-- =====================================================
-- 3. Chat History Table
-- =====================================================
CREATE TABLE IF NOT EXISTS chat_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL COMMENT 'user, assistant, or system',
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    
    -- Indexes for performance
    INDEX idx_chat_session (session_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Chat conversation history';

-- =====================================================
-- 4. Code Changes History Table
-- =====================================================
CREATE TABLE IF NOT EXISTS code_changes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255),
    file_name TEXT,
    old_code LONGTEXT,
    new_code LONGTEXT,
    commit_hash TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    
    -- Indexes for performance
    INDEX idx_code_session (session_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Code modification history';

-- =====================================================
-- 5. Add columns to existing tables (Migration support)
-- =====================================================
-- This section handles migration for existing databases
-- It safely adds new columns without dropping existing data

-- Add Google OAuth columns to users table if they don't exist
SET @dbname = DATABASE();
SET @tablename = 'users';
SET @columnname = 'is_google_user';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  'SELECT "is_google_user already exists" AS status;',
  'ALTER TABLE users ADD COLUMN is_google_user BOOLEAN DEFAULT FALSE AFTER is_github_user;'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

SET @columnname = 'google_id';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  'SELECT "google_id already exists" AS status;',
  'ALTER TABLE users ADD COLUMN google_id VARCHAR(255) AFTER is_google_user;'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

SET @columnname = 'google_username';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  'SELECT "google_username already exists" AS status;',
  'ALTER TABLE users ADD COLUMN google_username VARCHAR(255) AFTER google_id;'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

SET @columnname = 'google_token';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  'SELECT "google_token already exists" AS status;',
  'ALTER TABLE users ADD COLUMN google_token VARCHAR(255) AFTER google_username;'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

SET @columnname = 'google_avatar_url';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  'SELECT "google_avatar_url already exists" AS status;',
  'ALTER TABLE users ADD COLUMN google_avatar_url VARCHAR(255) AFTER google_token;'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- =====================================================
-- 6. Default Test Data
-- =====================================================
-- Create test accounts (only if they don't exist)

-- Test user account (password: test123)
INSERT IGNORE INTO users (username, email, password_hash, is_github_user, is_google_user) 
VALUES (
    'testuser', 
    'test@example.com', 
    '$2b$12$YIhXF8pV6LHmGzH6PxqOlOh2Q5zRnPf.K3VqKbMAz1TeXOpCHGGFa',
    FALSE,
    FALSE
);

-- Admin account (password: admin123)
INSERT IGNORE INTO users (username, email, password_hash, is_github_user, is_google_user) 
VALUES (
    'admin', 
    'admin@example.com', 
    '$2b$12$LQv3c1yqBWVHmFneT.3VmuxlpGY1.WUqjmZ0TIJjZsj6xvM2bN9ni',
    FALSE,
    FALSE
);

-- =====================================================
-- 7. Database User Creation and Permissions (OPTIONAL)
-- =====================================================
-- NOTE: This section requires CREATE USER privileges.
-- If you get an error, you can skip this section or run it with a privileged account.
-- Uncomment the lines below if you have the necessary privileges:

-- Create application user (adjust as needed for your environment)
-- CREATE USER IF NOT EXISTS 'chahae'@'localhost' IDENTIFIED BY '1234';
-- CREATE USER IF NOT EXISTS 'chahae'@'%' IDENTIFIED BY '1234';

-- Grant all privileges on the database
-- GRANT ALL PRIVILEGES ON 4th_project.* TO 'chahae'@'localhost';
-- GRANT ALL PRIVILEGES ON 4th_project.* TO 'chahae'@'%';

-- Apply permission changes
-- FLUSH PRIVILEGES;

-- =====================================================
-- 8. Status Check and Verification
-- =====================================================
SELECT '========================================' AS '';
SELECT '     DATABASE SETUP STATUS CHECK        ' AS '';
SELECT '========================================' AS '';

-- Check database character set
SELECT CONCAT('Database: ', DATABASE(), ' | Character Set: ', @@character_set_database) AS 'Database Info';

-- List all tables
SELECT '--- Created Tables ---' AS '';
SELECT TABLE_NAME, ENGINE, TABLE_COMMENT 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = DATABASE()
ORDER BY TABLE_NAME;

-- Check table record counts
SELECT '--- Record Counts ---' AS '';
SELECT 
    'users' AS table_name, 
    COUNT(*) AS records,
    CONCAT('OAuth Users - GitHub: ', SUM(is_github_user), ', Google: ', SUM(is_google_user)) AS details
FROM users
UNION ALL
SELECT 'sessions', COUNT(*), CONCAT('Active Sessions: ', COUNT(*)) FROM sessions
UNION ALL
SELECT 'chat_history', COUNT(*), CONCAT('Total Messages: ', COUNT(*)) FROM chat_history
UNION ALL
SELECT 'code_changes', COUNT(*), CONCAT('Code Modifications: ', COUNT(*)) FROM code_changes;

-- List user accounts
SELECT '--- User Accounts ---' AS '';
SELECT 
    username, 
    email, 
    CASE 
        WHEN is_github_user = 1 THEN 'GitHub OAuth'
        WHEN is_google_user = 1 THEN 'Google OAuth'
        ELSE 'Local Account'
    END AS auth_type,
    created_at 
FROM users
ORDER BY created_at;

-- Check users table structure
SELECT '--- Users Table Structure ---' AS '';
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'users'
ORDER BY ORDINAL_POSITION;

-- Final status
SELECT '========================================' AS '';
SELECT '    SETUP COMPLETED SUCCESSFULLY!       ' AS '';
SELECT '========================================' AS '';
SELECT 'Test Account: testuser / test123' AS 'Login Credentials';
SELECT 'Admin Account: admin / admin123' AS '';
SELECT 'Run Command: python app.py' AS 'How to Start';
SELECT '========================================' AS '';