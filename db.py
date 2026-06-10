import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'govqueue.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    schema = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with get_db() as conn:
        with open(schema) as f:
            conn.executescript(f.read())

def query(sql, args=(), one=False):
    conn = get_db()
    cur = conn.execute(sql, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def execute(sql, args=()):
    conn = get_db()
    cur = conn.execute(sql, args)
    conn.commit()
    lastid = cur.lastrowid
    conn.close()
    return lastid
