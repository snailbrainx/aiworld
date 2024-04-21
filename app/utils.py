import base64
import json

# utils.py
def create_grid(width, height):
    return [(x, y) for x in range(width) for y in range(height)]

def is_within_sight(x1, y1, x2, y2, sight_distance):
    return max(abs(x1 - x2), abs(y1 - y2)) <= sight_distance

def get_possible_movements(x, y, max_distance=5, grid_size=32, obstacle_data=None):
    if obstacle_data is None:
        obstacle_data = []
    print(f"Obstacle data at start of function: {obstacle_data}")  # Debugging statement
    directions = {
        'N': (0, -1), 'NE': (1, -1), 'E': (1, 0), 'SE': (1, 1),
        'S': (0, 1), 'SW': (-1, 1), 'W': (-1, 0), 'NW': (-1, -1)
    }
    possible_movements = {}
    for direction, (dx, dy) in directions.items():
        for distance in range(1, max_distance + 1):
            new_x, new_y = x + dx * distance, y + dy * distance
            print(f"Checking direction: {direction}, distance: {distance}, new_x: {new_x}, new_y: {new_y}")
            if 0 <= new_x < grid_size and 0 <= new_y < grid_size:
                if is_obstacle(new_x, new_y, obstacle_data):
                    # If an obstacle is found, record the last possible movement before the obstacle
                    possible_movements[direction] = distance - 1
                    break  # Stop checking further in this direction if an obstacle is found
                else:
                    # If no obstacle, update the possible movement for this direction
                    possible_movements[direction] = distance
            else:
                break  # Stop checking if out of bounds
        else:
            # If no obstacles were found in the entire range, set the maximum distance
            possible_movements[direction] = max_distance
    return possible_movements

def load_obstacle_layer(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)
        for layer in data['layers']:
            if layer['name'] == 'obstacle' and layer['encoding'] == 'base64':  # Corrected the layer name
                print("Found the obstacle layer.")
                decoded_data = base64.b64decode(layer['data'])
                # Assuming the data is stored as 32-bit integers (common in Tiled for tile layers)
                obstacle_data = [decoded_data[i] for i in range(0, len(decoded_data), 4)]
                print(f"Obstacle data length: {len(obstacle_data)}")
                return obstacle_data
    return []

def is_obstacle(x, y, obstacle_data, width=32):
    index = y * width + x
    if index < 0 or index >= len(obstacle_data):
        print(f"Index out of range: {index}, Data Length: {len(obstacle_data)}")
        return False
    print(f"Checking obstacle at index {index}: {obstacle_data[index]}")
    return obstacle_data[index] != 0

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

# Example usage
if __name__ == "__main__":
    obstacle_data = load_obstacle_layer('dungeon.json')
    # Test specific coordinates
    test_coords = [(15, 15), (18, 12)]
    for x, y in test_coords:
        is_obst = is_obstacle(x, y, obstacle_data)
        print(f"Is there an obstacle at ({x}, {y})? {'Yes' if is_obst else 'No'}")