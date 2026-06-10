PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS organization (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    logo_url TEXT
);

CREATE TABLE IF NOT EXISTS branch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL REFERENCES organization(id),
    name TEXT NOT NULL,
    address TEXT,
    phone TEXT,
    working_hours TEXT DEFAULT '08:00-16:00',
    grace_period_minutes INTEGER DEFAULT 15,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL REFERENCES organization(id),
    name TEXT NOT NULL,
    name_ar TEXT,
    estimated_duration_minutes INTEGER DEFAULT 10,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS branch_service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id INTEGER NOT NULL REFERENCES branch(id),
    service_id INTEGER NOT NULL REFERENCES service(id),
    is_available INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    national_id TEXT,
    role TEXT NOT NULL DEFAULT 'citizen',  -- guest,citizen,staff,validation_staff,supervisor,admin
    preferred_language TEXT DEFAULT 'en',
    is_active INTEGER DEFAULT 1,
    branch_id INTEGER REFERENCES branch(id)
);

CREATE TABLE IF NOT EXISTS window (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id INTEGER NOT NULL REFERENCES branch(id),
    service_id INTEGER REFERENCES service(id),
    window_number INTEGER NOT NULL,
    label TEXT,
    status TEXT DEFAULT 'closed'  -- open, closed
);

CREATE TABLE IF NOT EXISTS window_assignment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_id INTEGER NOT NULL REFERENCES window(id),
    staff_id INTEGER NOT NULL REFERENCES user(id),
    assigned_date TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS time_slot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_service_id INTEGER NOT NULL REFERENCES branch_service(id),
    slot_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    max_capacity INTEGER DEFAULT 10,
    booked_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS booking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    citizen_id INTEGER NOT NULL REFERENCES user(id),
    time_slot_id INTEGER NOT NULL REFERENCES time_slot(id),
    branch_service_id INTEGER NOT NULL REFERENCES branch_service(id),
    queue_number TEXT NOT NULL,
    status TEXT DEFAULT 'booked',  -- booked,arrived,serving,completed,cancelled,no_show,skipped
    booked_at TEXT NOT NULL,
    arrived_at TEXT,
    served_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS notification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user(id),
    booking_id INTEGER REFERENCES booking(id),
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    sent_at TEXT NOT NULL
);
