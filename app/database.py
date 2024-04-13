# database.py
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
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS output_format (
        property TEXT,
        type TEXT,
        description TEXT
    )
    ''')
    # Check if the entities table is empty
    cursor.execute("SELECT COUNT(*) FROM entities")
    if cursor.fetchone()[0] == 0:
        # Insert default rows
        cursor.execute('''
        INSERT INTO entities (name, personality, start_pos, image, ability, boss) 
        VALUES 
        ('Lucifer', 'You are Lucifer. You are very strong and commanding leader. You will do whatever it takes to survive and not take orders. You are cunning. You can speak any language but your main language is English. You are the devil and have a very strong attack ability.', 'A3', 'lucifer.png', 'attack', 1),
        ('Hulk', 'You are the Incredible Hulk. You are super strong. You will have a very limited vocabulary and behave just like the hulk. You hate Lucifer and will kill him on site', 'A1', 'hulk.png', 'attack', 1);
        ''')

    # Check if the output_format table is empty
    cursor.execute("SELECT COUNT(*) FROM output_format")
    if cursor.fetchone()[0] == 0:
        # Insert default rows
        cursor.execute('''
        INSERT INTO output_format (property, type, description) 
        VALUES
        ('thought', 'string', 'your thoughts. This should always contain content.'),
        ('talk', 'string', 'if you wish to speak to a nearby entity then use this key.'),
        ('move', 'string', 'the coordinates you wish to move to or 0 to stay still.'),
        ('ability', 'string', 'the target entity of the ability. set as 0 if not using the ability on anyone. Only add the entity''s name and nothing else.');
        ''')
    conn.commit()
    conn.close()