PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS role (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS branch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS branch_service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id INTEGER NOT NULL REFERENCES branch(id),
    service_id INTEGER NOT NULL REFERENCES service(id),
    estimated_duration_minutes INTEGER DEFAULT 10,
    is_active INTEGER DEFAULT 1,
    UNIQUE(branch_id, service_id)
);

CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone_number TEXT NOT NULL UNIQUE,
    preferred_language TEXT DEFAULT 'en' CHECK(preferred_language IN ('ar', 'en')),
    branch_id INTEGER REFERENCES branch(id),
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_role (
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS window (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id INTEGER NOT NULL REFERENCES branch(id),
    window_number INTEGER NOT NULL,
    is_open INTEGER DEFAULT 0,
    UNIQUE(branch_id, window_number)
);

CREATE TABLE IF NOT EXISTS staff_service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES service(id) ON DELETE CASCADE,
    UNIQUE(user_id, service_id)
);

CREATE TABLE IF NOT EXISTS staff_window (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES user(id) ON DELETE CASCADE,
    window_id INTEGER NOT NULL UNIQUE REFERENCES window(id) ON DELETE CASCADE,
    assigned_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_service_id INTEGER NOT NULL UNIQUE REFERENCES branch_service(id),
    current_serving_number INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id INTEGER NOT NULL REFERENCES queue(id),
    citizen_id INTEGER NOT NULL REFERENCES user(id),
    queue_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Waiting',
    ticket_date TEXT NOT NULL,
    joined_at TEXT NOT NULL,
    called_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS staff_round_robin (
    user_id INTEGER PRIMARY KEY REFERENCES user(id) ON DELETE CASCADE,
    last_service_id INTEGER REFERENCES service(id)
);

CREATE TABLE IF NOT EXISTS otp_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL,
    code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS push_subscription (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    p256dh_key TEXT NOT NULL,
    auth_key TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    ticket_id INTEGER REFERENCES ticket(id),
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    sent_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ticket_queue_date ON ticket(queue_id, ticket_date);
CREATE INDEX IF NOT EXISTS idx_ticket_citizen_status ON ticket(citizen_id, status);
CREATE INDEX IF NOT EXISTS idx_ticket_status_date ON ticket(status, ticket_date);
