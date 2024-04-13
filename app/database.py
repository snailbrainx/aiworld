import sqlite3

def get_db_connection():
    # Connect to an SQLite database. The database file is named 'aiworld.db'.
    # It will be created if it doesn't exist.
    conn = sqlite3.connect('aiworld.db')
    conn.row_factory = sqlite3.Row  # Make it return rows as dictionaries
    return conn

def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aiworld (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time INTEGER,
        position TEXT,
        entity TEXT,
        thought TEXT,
        talk TEXT,
        move TEXT,
        health_points INTEGER,
        ability TEXT,
        timestamp DATETIME
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        personality TEXT,
        start_pos TEXT,
        image TEXT,
        ability TEXT,
        boss INTEGER
    )
    ''')
    conn.commit()
    conn.close()