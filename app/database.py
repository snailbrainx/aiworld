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

    # Create the aiworld table with new columns for direction, distance, and ability_target
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
        ability_target TEXT,
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
            max_travel_distance INTEGER,
            model TEXT
        )
        ''')

    # Check if the entities table is empty and insert default rows if it is
    cursor.execute("SELECT COUNT(*) FROM entities")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO entities (name, personality, start_x, start_y, image, ability, boss, hp, sight_dist, max_travel_distance, model)
            VALUES 
            ('Lilith', 'Lilith, strong evil healer. You are on the Red Team and you are a strong leader.', 50, 50, 'lilithred.png', 'heal', 1, 300, 200, 50, 'gpt4'),
            ('Mira', 'Mira, the gentle healer whose touch revives the fallen. You are on the blue team.', 450, 50, 'lisablue.png', 'heal', 1, 300, 200, 50, 'claude3'),
            ('Thorn', 'Thorn, the fierce guardian of the forgotten realms. You are on the Red Team.', 55, 50, 'davered.png', 'attack', 1, 300, 200, 50, 'gpt4'),
            ('Voltan', 'Voltan, the ruthless attacker from the stormy highlands. You are on the blue team and you are a strong leader.', 445, 45, 'johnblue.png', 'attack', 1, 300, 200, 50, 'claude3'),
            ('Elara', 'Elara, the mystical healer from the celestial skies. You are on the Red Team.', 45, 45, 'kellyred.png', 'heal', 1, 300, 200, 50, 'gpt4'),
            ('Seraphine', 'Seraphine, the divine healer with the power of light. You are on the blue team.', 440, 35, 'lisablue.png', 'heal', 1, 300, 200, 50, 'claude3'),
            ('Drake', 'Drake, the bold warrior of the scorched earth. You are on the Red Team.', 40, 45, 'davered.png', 'attack', 1, 300, 200, 50, 'gpt4'),
            ('Hulk', 'You are the Incredible Hulk. You talk like him with a limited vocabulary. You are on the blue team.', 444, 46, 'hulkblue.png', 'attack', 1, 300, 200, 50, 'claude3');
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
        ('move', 'string', 'the direction you wish to move in the format "N", "NE, "E", "SE", "S", "SW", "W" or "NW". Use 0 to stay still.'),
        ('distance', 'number', 'the distance to travel in the specified direction'),
        ('ability', 'string', 'the ability to use or 0 to not use an ability.'),
        ('ability_target', 'string', 'the target entity''s name or 0 to not use your ability on anyone.');
        ''')

    # Check if the abilities table exists and create if not
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='abilities'")
    if not cursor.fetchone():
        cursor.execute('''
        CREATE TABLE abilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ability TEXT,
            range INTEGER,
            min_value INTEGER,
            max_value INTEGER
        )
        ''')

    # Check if the abilities table is empty and insert default rows if it is
    cursor.execute("SELECT COUNT(*) FROM abilities")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO abilities (ability, range, min_value, max_value)
            VALUES 
            ('heal', 15, 10, 50),
            ('attack', 5, 20, 70);
        ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_db()