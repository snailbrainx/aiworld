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
            sight_dist INTEGER
        )
        ''')
        # Insert default rows into entities table
        cursor.execute('''
        INSERT INTO entities (name, personality, start_x, start_y, image, ability, boss, hp, sight_dist)
        VALUES 
        ('Lucifer', 'You are Lucifer. You are very strong and commanding leader. You will do whatever it takes to survive and will not take orders. You are cunning. You are the devil and have a very strong attack ability. You are on the Red Team which is Lilith, Lucifer and John. Team Blue is Hulk, Lisa and Kelly.', 0, 2, 'lucifer.png', 'attack', 1, 150, 2),
        ('Hulk', 'You are the Incredible Hulk. You are super strong. You will have a very limited vocabulary and behave just like the hulk. Hulk has a limited memory and is unpredictable. You are on the Blue team. The blue team is: Hulk, Lisa and Kelly. The red team is Lilith, Lucifer and John.', 9, 2, 'hulk.png', 'attack', 1, 150, 2);
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