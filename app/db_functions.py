# db_functions.py
import datetime
from utils import is_within_sight, get_direction_from_deltas

def insert_data(cursor, cnx, entity, thought, talk, x, y, time, health_points, ability, ability_target, move_direction, move_distance):
    query = ("INSERT INTO aiworld "
             "(time, x, y, entity, thought, talk, move_direction, move_distance, health_points, ability, ability_target, timestamp) "
             "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    values = (time, x, y, entity, thought, talk, move_direction, move_distance, health_points, ability, ability_target, datetime.datetime.now())
    print("Inserting into Database:\n", query)
    cursor.execute(query, values)
    cnx.commit()


def fetch_last_data(cursor, entity):
    # Updated SQL query to match the new database schema
    cursor.execute("""
        SELECT e.hp, a.time, a.x, a.y, a.entity, a.thought, a.talk,
            a.move_direction, a.move_distance, a.health_points, a.ability, a.ability_target
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
        ability = row[10]
        ability_target = row[11]
        
        # Fetch the last 12 records for history
        cursor.execute("""
            SELECT time, x, y, entity, thought, talk, move_direction, move_distance, health_points, ability, ability_target
            FROM aiworld
            WHERE entity=?
            ORDER BY time DESC
            LIMIT 8
        """, (entity,))
        all_rows = cursor.fetchall()
        
        # Initialize history list and populate with data from fetched rows
        history = []
        for a_row in all_rows:
            current_dict = dict(zip(('time', 'x', 'y', 'entity', 'thought', 'talk', 'move_direction', 'move_distance', 'health_points', 'ability', 'ability_target'), a_row))
            
            # Conditionally include ability and ability_target keys
            if current_dict['ability'] == '0' or current_dict['ability_target'] == '0':
                current_dict.pop('ability', None)
                current_dict.pop('ability_target', None)
            
            history.append(current_dict)
    else:
        # If no records are found, set default values
        max_hp = cursor.execute("SELECT hp FROM entities WHERE name=?", (entity,)).fetchone()[0]
        time = 1
        x = None
        y = None
        health_points = max_hp
        ability = ''
        ability_target = ''
        history = []
    
    return time, x, y, history, health_points, ability, ability_target, max_hp

def fetch_and_initialize_bots(cursor):
    cursor.execute("""
        SELECT e.name, e.personality, a.x, a.y, e.ability, e.sight_dist
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
            cursor.execute("SELECT x, y, talk, ability, ability_target, health_points FROM aiworld WHERE entity=? AND time<=? ORDER BY time DESC LIMIT 2", (other_bot.entity, a_row['time']))
            rows = cursor.fetchall()
            if rows:
                last_row = rows[0]
                other_bot_x, other_bot_y, other_bot_talk, other_bot_ability, other_bot_ability_target, other_bot_health_points = last_row
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
                        if other_bot_ability != '0' and other_bot_ability_target != '0':
                            nearby_entity["ability"] = other_bot_ability
                            nearby_entity["ability_target"] = other_bot_ability_target
                    nearby_entities_from_past.append(nearby_entity)
        current_dict["nearby_entities"] = nearby_entities_from_past if nearby_entities_from_past else []
        updated_history.append(current_dict)
    return updated_history

def evaluate_nearby_entities(cursor, entity, x, y, bots, sight_distance, talk_distance, ability):
    nearby_entities = {}
    for bot in bots:
        if bot.entity == entity:
            continue
        bot_x, bot_y = bot.x, bot.y
        if is_within_sight(x, y, bot_x, bot_y, sight_distance):
            dx, dy = bot_x - x, bot_y - y
            direction, distance = get_direction_from_deltas(dx, dy)
            in_talk_range = is_within_sight(x, y, bot_x, bot_y, talk_distance)
            nearby_entity = {
                "direction": direction,
                "distance": distance,
                "health_points": bot.health_points,
                "in_talk_range": in_talk_range
            }
            cursor.execute("SELECT x, y, talk, ability, ability_target FROM aiworld WHERE entity=? ORDER BY time DESC LIMIT 1", (bot.entity,))
            row = cursor.fetchone()
            if row:
                last_bot_x, last_bot_y, last_bot_talk, last_bot_ability, last_bot_ability_target = row
                if bot.health_points > 0:
                    if is_within_sight(x, y, last_bot_x, last_bot_y, talk_distance) and last_bot_talk and last_bot_talk != '0':
                        nearby_entity["talk"] = last_bot_talk
                    if last_bot_ability != '0' and last_bot_ability_target != '0':
                        nearby_entity["ability"] = last_bot_ability
                        nearby_entity["ability_target"] = last_bot_ability_target
                cursor.execute("SELECT range FROM abilities WHERE ability=?", (ability,))
                ability_range = cursor.fetchone()[0]
                if ability == 'heal':
                    nearby_entity["in_range_of_heal"] = is_within_sight(x, y, bot_x, bot_y, ability_range)
                elif ability == 'attack':
                    nearby_entity["in_range_of_attack"] = is_within_sight(x, y, bot_x, bot_y, ability_range)
            nearby_entities[bot.entity] = nearby_entity
    return nearby_entities