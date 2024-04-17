# utils.py
def create_grid(width, height):
    return [(x, y) for x in range(width) for y in range(height)]


def is_within_sight(x1, y1, x2, y2, sight_distance):
    return max(abs(x1 - x2), abs(y1 - y2)) <= sight_distance

def get_possible_movements(x, y, max_distance=5, grid_size=500, is_obstacle_func=None):
    directions = {
        'N': (0, -1), 'NE': (1, -1), 'E': (1, 0), 'SE': (1, 1),
        'S': (0, 1), 'SW': (-1, 1), 'W': (-1, 0), 'NW': (-1, -1)
    }
    possible_movements = {}
    for direction, (dx, dy) in directions.items():
        for distance in range(1, max_distance + 1):
            new_x, new_y = x + dx * distance, y + dy * distance
            if 0 <= new_x < grid_size and 0 <= new_y < grid_size:
                if is_obstacle_func and is_obstacle_func(new_x, new_y):
                    break  # Stop checking further in this direction if an obstacle is found
                possible_movements[direction] = distance
            else:
                break  # Stop checking if out of bounds
    return possible_movements

def is_obstacle(x, y, map_data):
    # Implement obstacle checking logic based on map_data
    return (x, y) in map_data

def get_direction_from_deltas(dx, dy):
    if dy < 0:  # North
        if dx < 0:
            return 'NW', max(abs(dx), abs(dy))
        elif dx > 0:
            return 'NE', max(abs(dx), abs(dy))
        else:
            return 'N', abs(dy)
    elif dy > 0:  # South
        if dx < 0:
            return 'SW', max(abs(dx), abs(dy))
        elif dx > 0:
            return 'SE', max(abs(dx), abs(dy))
        else:
            return 'S', abs(dy)
    else:  # East or West
        if dx < 0:
            return 'W', abs(dx)
        elif dx > 0:
            return 'E', abs(dx)
    return 'Here', 0  # Same position