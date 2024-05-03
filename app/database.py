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

    # Create the aiworld table with new columns for direction, distance, and action_target
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
        action TEXT,
        action_target TEXT,
        timestamp DATETIME
    )
    ''')

    # Check if the bot_summaries table exists and create if not
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_summaries'")
    if not cursor.fetchone():
        cursor.execute('''
        CREATE TABLE bot_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT,
            summary TEXT,
            time INTEGER
        )
        ''')
    else:
        # Clear the bot_summaries table if it already exists
        cursor.execute('DELETE FROM bot_summaries')

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
            action TEXT,
            boss INTEGER,
            hp INTEGER,
            sight_dist INTEGER,
            max_travel_distance INTEGER,
            model TEXT
        )
        ''')

    # Check if the items table exists and create if not
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
    if not cursor.fetchone():
        cursor.execute('''
        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            description TEXT,
            image TEXT,
            effect_value INTEGER
        )
        ''')
        # Insert basic items
        cursor.execute('''
        INSERT INTO items (name, type, description, image, effect_value)
        VALUES 
        ('berries', 'food', 'fresh fruit berries', 'berries.png', 10),
        ('Elixir of Health', 'health_potion', 'a magical healing potion', 'elixir_health.png', 100);
        ''')

    # Drop and recreate inventory table
    cursor.execute('DROP TABLE IF EXISTS inventory')
    cursor.execute('''
    CREATE TABLE inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER,
        item_id INTEGER,
        FOREIGN KEY (entity_id) REFERENCES entities(id),
        FOREIGN KEY (item_id) REFERENCES items(id)
    )
    ''')

    # Drop and recreate world items table
    cursor.execute('DROP TABLE IF EXISTS world_items')
    cursor.execute('''
    CREATE TABLE world_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        x INTEGER,
        y INTEGER,
        FOREIGN KEY (item_id) REFERENCES items(id)
    )
    ''')
    # Place items on the map
    cursor.execute('''
    INSERT INTO world_items (item_id, x, y)
    VALUES 
    ((SELECT id FROM items WHERE name = 'berries'), 14, 12),
    ((SELECT id FROM items WHERE name = 'Elixir of Health'), 22, 18);
    ''')

    # Check if the entities table is empty and insert default rows if it is
    cursor.execute("SELECT COUNT(*) FROM entities")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO entities (name, personality, start_x, start_y, image, action, boss, hp, sight_dist, max_travel_distance, model)
            VALUES 
            ('Leanne', 'Leanne, the Elf princess. Leanne is high born and believes she is being chased through a dungeon by intelligent Trolls who are trying to wipe out her bloodline. She is being protected by Mira. Leanne has healing actions.', 11, 3, 'lilith.png', 'heal', 1, 400, 15, 5, 'flowise_gpt-4-turbo'),
            ('Mira', 'Mira, the Human Rogue. She loves teasing and joking with her companions even with things look bleak. Mira is in love with Leanne and is trying to keep her safe. Mira has an attack.', 10, 3, 'lisa.png', 'attack', 0, 300, 15, 4, 'flowise_gpt-4-turbo'),
            ('Thorn', 'Thorn, is a Dwarf fighter with a large 2 handed axe. Likes to drink a lot and get into fights. Thorn was trapped in the dungeon but has managed to get free, now he''s lost and looking for an exit.', 25, 3, 'dave.png', 'attack', 0, 300, 15, 4, 'flowise_gpt-4-turbo'),
            ('Trollos', 'Trollos are Trolls, they have very bad broken English, with a super limited vocabulary of maybe 6 words. They are trying to go about their own business.', 24, 25, 'hulk.png', 'attack', 1, 500, 15, 3, 'flowise_gpt-4-turbo');
        ''')

    # Insert initial positions into aiworld table every time the script is run
    cursor.execute('''
        INSERT INTO aiworld (time, x, y, entity, health_points, thought, talk, move_direction, move_distance, action, action_target, timestamp)
        SELECT 1, start_x, start_y, name, hp, '', '', '', 0, '', '', CURRENT_TIMESTAMP FROM entities;
    ''')

    # Check if the actions table exists and create if not
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='actions'")
    if not cursor.fetchone():
        cursor.execute('''
        CREATE TABLE actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            range INTEGER,
            min_value INTEGER,
            max_value INTEGER
        )
        ''')

    # Check if the actions table is empty and insert default rows if it is
    cursor.execute("SELECT COUNT(*) FROM actions")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO actions (action, range, min_value, max_value)
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