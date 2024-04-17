# database.py
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('aiworld.db')
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Reset only the aiworld table
    cursor.execute('DROP TABLE IF EXISTS aiworld')

    # Create the aiworld table with new columns for direction and distance
    cursor.execute('''
    CREATE TABLE aiworld (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time INTEGER,
        x INTEGER,
        y INTEGER,
        entity TEXT,
        thought TEXT,
        talk TEXT,
        move_direction TEXT,
        move_distance INTEGER,
        health_points INTEGER,
        ability TEXT,
        timestamp DATETIME
    )
    ''')

    # Check if the entities table exists and create if not
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities'")
    if not cursor.fetchone():
        cursor.execute('''
        CREATE TABLE entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            personality TEXT,
            start_x INTEGER,
            start_y INTEGER,
            image TEXT,
            ability TEXT,
            boss INTEGER,
            hp INTEGER,
            sight_dist INTEGER,
            max_travel_distance INTEGER DEFAULT 5
        )
        ''')

    # Check if the entities table is empty and insert default rows if it is
    cursor.execute("SELECT COUNT(*) FROM entities")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO entities (name, personality, start_x, start_y, image, ability, boss, hp, sight_dist, max_travel_distance)
            VALUES 
            ('Lilith', 'Lilith, strong evil healer.', 50, 50, 'lilith.png', 'heal', 1, 200, 50, 10),
            ('Thorn', 'Thorn, the fierce guardian of the forgotten realms.', 450, 50, 'thorn.png', 'attack', 1, 200, 50, 10),
            ('Elara', 'Elara, the mystical healer from the celestial skies.', 50, 450, 'elara.png', 'heal', 1, 200, 50, 10),
            ('Drake', 'Drake, the bold warrior of the scorched earth.', 450, 450, 'drake.png', 'attack', 1, 200, 50, 10),
            ('Mira', 'Mira, the gentle healer whose touch revives the fallen.', 250, 50, 'mira.png', 'heal', 1, 200, 50, 10),
            ('Voltan', 'Voltan, the ruthless attacker from the stormy highlands.', 50, 250, 'voltan.png', 'attack', 1, 200, 50, 10),
            ('Seraphine', 'Seraphine, the divine healer with the power of light.', 450, 250, 'seraphine.png', 'heal', 1, 200, 50, 10),
            ('Hulk', 'You are the Incredible Hulk. You talk like him with a limited vocabulary', 250, 450, 'hulk.png', 'attack', 1, 200, 50, 10);
        ''')

    # Check if the output_format table exists and create if not
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='output_format'")
    if not cursor.fetchone():
        cursor.execute('''
        CREATE TABLE output_format (
            property TEXT,
            type TEXT,
            description TEXT
        )
        ''')
        # Insert default output format rows
        cursor.execute('''
        INSERT INTO output_format (property, type, description) 
        VALUES
        ('thought', 'string', 'your thoughts. This should always contain content.'),
        ('talk', 'string', 'if you wish to speak to a nearby entity then use this key.'),
        ('move', 'string', 'the direction you wish to move in the format "N", "NE, "E", "SE", "S", "SW", "W" or "NW"'),
        ('distance', 'number', 'the distance to travel in the specified direction'),
        ('ability', 'string', 'the target entity''s name or 0 to not use your ability on anyone.');
        ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_db()