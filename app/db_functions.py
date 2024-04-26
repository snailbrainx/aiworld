# db_functions.py
import datetime
from utils import is_within_sight, get_direction_from_deltas, astar

def insert_data(cursor, cnx, entity, thought, talk, x, y, time, health_points, action, action_target, move_direction, move_distance):
    query = ("INSERT INTO aiworld "
             "(time, x, y, entity, thought, talk, move_direction, move_distance, health_points, action, action_target, timestamp) "
             "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    values = (time, x, y, entity, thought, talk, move_direction, move_distance, health_points, action, action_target, datetime.datetime.now())
    print("Inserting into Database:\n", query)
    cursor.execute(query, values)
    cnx.commit()

def remove_item_from_world(cursor, cnx, item_name, x, y):
    cursor.execute("""
        DELETE FROM world_items
        WHERE id = (
            SELECT wi.id
            FROM world_items wi
            JOIN items i ON wi.item_id = i.id
            WHERE i.name = ? AND wi.x = ? AND wi.y = ?
        )
    """, (item_name, x, y))
    cnx.commit()

def fetch_bot_inventory(cursor, entity_name):
    cursor.execute("""
        SELECT i.name, i.description
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        JOIN entities e ON inv.entity_id = e.id
        WHERE e.name = ?
    """, (entity_name,))
    inventory = cursor.fetchall()
    return {item[0]: {"description": item[1]} for item in inventory}

def add_item_to_inventory(cursor, cnx, entity_name, item_name):
    cursor.execute("""
        INSERT INTO inventory (entity_id, item_id)
        VALUES (
            (SELECT id FROM entities WHERE name = ?),
            (SELECT id FROM items WHERE name = ?)
        )
    """, (entity_name, item_name))
    cnx.commit()

def fetch_nearby_items(cursor, x, y, sight_distance):
    cursor.execute("""
        SELECT i.name, wi.x, wi.y, i.description
        FROM world_items wi
        JOIN items i ON wi.item_id = i.id
        WHERE ABS(wi.x - ?) <= ? AND ABS(wi.y - ?) <= ?
    """, (x, sight_distance, y, sight_distance))
    items = cursor.fetchall()
    return items

def fetch_last_data(cursor, entity):
    # Updated SQL query to match the new database schema
    cursor.execute("""
        SELECT e.hp, a.time, a.x, a.y, a.entity, a.thought, a.talk,
            a.move_direction, a.move_distance, a.health_points, a.action, a.action_target
        FROM aiworld a
        JOIN entities e ON a.entity = e.name
        WHERE a.entity=?
        ORDER BY a.time DESC
        LIMIT 1
    """, (entity,))
    row = cursor.fetchone()
    
    if row:
        max_hp = row[0]
        time = row[1] + 1
        x = row[2]
        y = row[3]
        health_points = row[9]
        action = row[10]
        action_target = row[11]
        
        # Fetch the last 12 records for history
        cursor.execute("""
            SELECT time, x, y, entity, thought, talk, move_direction, move_distance, health_points, action, action_target
            FROM aiworld
            WHERE entity=?
            ORDER BY time DESC
            LIMIT 8
        """, (entity,))
        all_rows = cursor.fetchall()
        
        # Initialize history list and populate with data from fetched rows
        history = []
        for a_row in all_rows:
            current_dict = dict(zip(('time', 'x', 'y', 'entity', 'thought', 'talk', 'move_direction', 'move_distance', 'health_points', 'action', 'action_target'), a_row))
            
            # Conditionally include action and action_target keys
            if current_dict['action'] == '0' or current_dict['action_target'] == '0':
                current_dict.pop('action', None)
                current_dict.pop('action_target', None)
            
            history.append(current_dict)
    else:
        # If no records are found, set default values
        max_hp = cursor.execute("SELECT hp FROM entities WHERE name=?", (entity,)).fetchone()[0]
        time = 1
        x = None
        y = None
        health_points = max_hp
        action = ''
        action_target = ''
        history = []
    
    return time, x, y, history, health_points, action, action_target, max_hp

def fetch_and_initialize_bots(cursor):
    cursor.execute("""
        SELECT e.name, e.personality, a.x, a.y, e.action, e.sight_dist
        FROM entities e
        JOIN aiworld a ON e.name = a.entity
        WHERE a.time = (SELECT MAX(time) FROM aiworld a2 WHERE a2.entity = e.name)
    """)
    entities = cursor.fetchall()
    print("Entities fetched with latest positions:", entities)
    return entities

def fetch_current_talk_and_position(cursor, entity):
    cursor.execute("SELECT x, y, talk FROM aiworld WHERE entity=? ORDER BY time DESC LIMIT 1", (entity,))
    row = cursor.fetchone()
    if row:
        x, y = row[0], row[1]
        talk = row[2]
    else:
        x, y = None, None  # Use None if no data is found
        talk = ""
    return (x, y), talk

def fetch_nearby_entities_for_history(cursor, entity, history, bots, sight_dist, talk_distance):
    updated_history = []
    for a_row in history:
        current_dict = a_row
        nearby_entities_from_past = []
        for other_bot in bots:
            if other_bot.entity == entity:
                continue
            cursor.execute("SELECT x, y, talk, action, action_target, health_points FROM aiworld WHERE entity=? AND time<=? ORDER BY time DESC LIMIT 2", (other_bot.entity, a_row['time']))
            rows = cursor.fetchall()
            if rows:
                last_row = rows[0]
                other_bot_x, other_bot_y, other_bot_talk, other_bot_action, other_bot_action_target, other_bot_health_points = last_row
                if is_within_sight(current_dict['x'], current_dict['y'], other_bot_x, other_bot_y, sight_dist):
                    dx, dy = other_bot_x - current_dict['x'], other_bot_y - current_dict['y']
                    direction, distance = get_direction_from_deltas(dx, dy)
                    nearby_entity = {
                        "name": other_bot.entity,
                        "direction": direction,
                        "distance": distance,
                        "health_points": other_bot_health_points
                    }
                    if len(rows) > 1:
                        prev_row = rows[1]
                        prev_bot_x, prev_bot_y = prev_row[0], prev_row[1]
                        if other_bot_health_points > 0:
                            if is_within_sight(current_dict['x'], current_dict['y'], prev_bot_x, prev_bot_y, talk_distance) or \
                            is_within_sight(current_dict['x'], current_dict['y'], other_bot_x, other_bot_y, talk_distance):
                                nearby_entity["talks"] = other_bot_talk if other_bot_talk and other_bot_talk != '0' else ''
                    elif other_bot_health_points > 0 and is_within_sight(current_dict['x'], current_dict['y'], other_bot_x, other_bot_y, talk_distance):
                        nearby_entity["talks"] = other_bot_talk if other_bot_talk and other_bot_talk != '0' else ''
                    if other_bot_health_points > 0:
                        if other_bot_action != '0' and other_bot_action_target != '0':
                            nearby_entity["action"] = other_bot_action
                            nearby_entity["action_target"] = other_bot_action_target
                    nearby_entities_from_past.append(nearby_entity)
        current_dict["nearby_entities"] = nearby_entities_from_past if nearby_entities_from_past else []
        updated_history.append(current_dict)
    return updated_history

def evaluate_nearby_entities(cursor, entity, x, y, bots, sight_distance, talk_distance, action, grid_size, obstacle_data):
    nearby_entities = {}
    for bot in bots:
        if bot.entity == entity:
            continue
        bot_x, bot_y = bot.x, bot.y
        if is_within_sight(x, y, bot_x, bot_y, sight_distance):
            path = astar((x, y), (bot_x, bot_y), grid_size, obstacle_data)
            if path and len(path) > 1:
                first_step = path[1]
                dx, dy = first_step[0] - x, first_step[1] - y
                direction, distance = get_direction_from_deltas(dx, dy)
                in_talk_range = is_within_sight(x, y, bot_x, bot_y, talk_distance)
                nearby_entity = {
                    "direction": direction,
                    "distance": distance,
                    "health_points": bot.health_points,
                    "in_talk_range": in_talk_range
                }
                cursor.execute("SELECT x, y, talk, action, action_target FROM aiworld WHERE entity=? ORDER BY time DESC LIMIT 1", (bot.entity,))
                row = cursor.fetchone()
                if row:
                    last_bot_x, last_bot_y, last_bot_talk, last_bot_action, last_bot_action_target = row
                    if bot.health_points > 0:
                        if is_within_sight(x, y, last_bot_x, last_bot_y, talk_distance) and last_bot_talk and last_bot_talk != '0':
                            nearby_entity["talk"] = last_bot_talk
                        if last_bot_action != '0' and last_bot_action_target != '0':
                            nearby_entity["action"] = last_bot_action
                            nearby_entity["action_target"] = last_bot_action_target
                    cursor.execute("SELECT range FROM actions WHERE action=?", (action,))
                    action_range = cursor.fetchone()[0]
                    if action == 'heal':
                        nearby_entity["in_range_of_heal"] = is_within_sight(x, y, bot_x, bot_y, action_range)
                    elif action == 'attack':
                        nearby_entity["in_range_of_attack"] = is_within_sight(x, y, bot_x, bot_y, action_range)
                nearby_entities[bot.entity] = nearby_entity
    return nearby_entities