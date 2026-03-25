-- Tabla de usuarios
CREATE TABLE users (
    id VARCHAR(100) PRIMARY KEY, -- Cognito sub
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100),
    password_hash VARCHAR(255), -- Para alternativa sin Cognito
    role ENUM('user', 'admin') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Tabla de tokens de reset de contraseña
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    user_id VARCHAR(100) NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_expires (expires_at)
);

-- Tabla de conversaciones
CREATE TABLE conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabla de mensajes (cada mensaje del chat)
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT,
    role ENUM('user', 'assistant'),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Tabla de recetas favoritas
CREATE TABLE IF NOT EXISTS favorite_recipes (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         VARCHAR(100) NOT NULL,
    title           VARCHAR(255) NOT NULL,
    ingredients     TEXT,
    steps           TEXT,
    tip             VARCHAR(500),
    prep_time       VARCHAR(50),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabla de perfil extendido
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id         VARCHAR(100) PRIMARY KEY,
    avatar_emoji    VARCHAR(10) DEFAULT '👨‍🍳',
    bio             VARCHAR(300),
    favorite_cuisine VARCHAR(100),
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);