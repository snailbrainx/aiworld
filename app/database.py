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
            ('Leanne', 'Leanne, the Elf princess. Leanne is high born and believes she is being chased through a dungeon by intelligent Trolls who are trying to wipe out her bloodline. She is being protected by Mira. Leanne has healing abilities.', 11, 3, 'lilith.png', 'heal', 1, 400, 15, 5, 'flowise_gpt-4-turbo'),
            ('Mira', 'Mira, the Human Rogue. She loves teasing and joking with her companions even with things look bleak. Mira is in love with Leanne and is trying to keep her safe. Mira has an attack.', 10, 3, 'lisa.png', 'attack', 0, 300, 15, 4, 'flowise_gpt-4-turbo'),
            ('Thorn', 'Thorn, is a Dwarf fighter with a large 2 handed axe. Likes to drink a lot and get into fights. Thorn was trapped in the dungeon but has managed to get free, now he''s lost and looking for an exit.', 25, 3, 'dave.png', 'attack', 0, 300, 15, 4, 'flowise_gpt-4-turbo'),
            ('Trollos', 'Trollos are Trolls, they have very bad broken English, with a super limited vocabulary of maybe 6 words. They are trying to go about their own business.', 24, 25, 'hulk.png', 'attack', 1, 500, 15, 3, 'flowise_gpt-4-turbo');
        ''')

    # Insert initial positions into aiworld table every time the script is run
    cursor.execute('''
        INSERT INTO aiworld (time, x, y, entity, health_points, thought, talk, move_direction, move_distance, ability, ability_target, timestamp)
        SELECT 1, start_x, start_y, name, hp, '', '', '', 0, '', '', CURRENT_TIMESTAMP FROM entities;
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

    # Check if the destinations table exists and create if not
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='destinations'")
    if not cursor.fetchone():
        cursor.execute('''
        CREATE TABLE destinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            x INTEGER,
            y INTEGER
        )
        ''')
        # Insert default destinations rows (optional)
        cursor.execute('''
        INSERT INTO destinations (name, x, y) 
        VALUES 
        ('Exit', 3, 28),
        ('Healing_fountain', 27, 28);
        ''')

    # Existing commit and close connection code...
    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_db()