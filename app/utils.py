# utils.py
def create_grid(width, height):
    return [(x, y) for x in range(width) for y in range(height)]


def is_within_sight(x1, y1, x2, y2, sight_distance):
    return max(abs(x1 - x2), abs(y1 - y2)) <= sight_distance


def get_movable_coordinates(position, width, height):
    x, y = position
    directions = {
        'N': [],
        'NE': [],
        'E': [],
        'SE': [],
        'S': [],
        'SW': [],
        'W': [],
        'NW': []
    }
    for dx in range(-2, 3):  # Range from -2 to 2
        for dy in range(-2, 3):  # Range from -2 to 2
            if dx == 0 and dy == 0:
                continue
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < width and 0 <= new_y < height:
                if dx == 0:
                    if dy > 0:
                        directions['N'].append((new_x, new_y))
                    else:
                        directions['S'].append((new_x, new_y))
                elif dx > 0:
                    if dy == 0:
                        directions['E'].append((new_x, new_y))
                    elif dy > 0:
                        directions['NE'].append((new_x, new_y))
                        directions['N'].append((new_x, new_y))
                        directions['E'].append((new_x, new_y))
                    else:
                        directions['SE'].append((new_x, new_y))
                        directions['S'].append((new_x, new_y))
                        directions['E'].append((new_x, new_y))
                else:
                    if dy == 0:
                        directions['W'].append((new_x, new_y))
                    elif dy > 0:
                        directions['NW'].append((new_x, new_y))
                        directions['N'].append((new_x, new_y))
                        directions['W'].append((new_x, new_y))
                    else:
                        directions['SW'].append((new_x, new_y))
                        directions['S'].append((new_x, new_y))
                        directions['W'].append((new_x, new_y))
    return directions