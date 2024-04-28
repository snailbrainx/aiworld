# utils.py
import base64
import json
import heapq

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(start, goal, grid_width, grid_height, obstacle_data):
    if start == goal:
        return [start]

    neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    close_set = set()
    came_from = {}
    gscore = {start: 0}
    fscore = {start: heuristic(start, goal)}
    oheap = [(fscore[start], start)]

    while oheap:
        current = heapq.heappop(oheap)[1]
        if current == goal:
            return reconstruct_path(came_from, current, start)

        close_set.add(current)
        for i, j in neighbors:
            neighbor = current[0] + i, current[1] + j
            if not is_valid_neighbor(neighbor, grid_width, grid_height, obstacle_data, close_set, gscore, current):
                continue
            update_scores(neighbor, current, goal, gscore, fscore, came_from, oheap)

    return []

def reconstruct_path(came_from, current, start):
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[current]
    path.append(start)
    path.reverse()
    return path

def is_valid_neighbor(neighbor, grid_width, grid_height, obstacle_data, close_set, gscore, current):
    if not (0 <= neighbor[0] < grid_width and 0 <= neighbor[1] < grid_height):
        return False
    if is_obstacle(neighbor[0], neighbor[1], obstacle_data):
        return False
    tentative_g_score = gscore[current] + heuristic(current, neighbor)
    if neighbor in close_set and tentative_g_score >= gscore.get(neighbor, 0):
        return False
    return True

def update_scores(neighbor, current, goal, gscore, fscore, came_from, oheap):
    tentative_g_score = gscore[current] + heuristic(current, neighbor)
    if tentative_g_score < gscore.get(neighbor, 0) or neighbor not in [i[1] for i in oheap]:
        came_from[neighbor] = current
        gscore[neighbor] = tentative_g_score
        fscore[neighbor] = tentative_g_score + heuristic(neighbor, goal)
        heapq.heappush(oheap, (fscore[neighbor], neighbor))


def create_grid(width, height):
    return [(x, y) for x in range(width) for y in range(height)]

def is_within_sight(x1, y1, x2, y2, sight_distance):
    return max(abs(x1 - x2), abs(y1 - y2)) <= sight_distance

def calculate_direction_and_distance(start, goal, grid_size, obstacle_data, max_distance=float('inf')):
    path = astar(start, goal, grid_size[0], grid_size[1], obstacle_data)
    if path and len(path) > 1:
        direction, distance = calculate_path_direction_and_distance(path, start[0], start[1], max_distance)
        total_distance = len(path) - 1  # Calculate the total distance as the number of steps in the path
        if total_distance == 0:
            direction = "Here"
        return direction, distance, total_distance
    return None, None, None

def get_possible_movements(x, y, max_distance=20, grid_width=32, grid_height=32, obstacle_data=None, destinations=None):
    if obstacle_data is None:
        obstacle_data = []
    if destinations is None:
        destinations = []

    directions = {
        'N': (0, -1), 'NE': (1, -1), 'E': (1, 0), 'SE': (1, 1),
        'S': (0, 1), 'SW': (-1, 1), 'W': (-1, 0), 'NW': (-1, -1)
    }

    possible_movements = calculate_possible_movements(x, y, max_distance, (grid_width, grid_height), obstacle_data, directions)
    destination_direction = calculate_destination_directions(x, y, max_distance, (grid_width, grid_height), obstacle_data, destinations)

    return possible_movements, destination_direction

def calculate_possible_movements(x, y, max_distance, grid_size, obstacle_data, directions):
    possible_movements = {}
    for direction, (dx, dy) in directions.items():
        distance = calculate_movement_distance(x, y, dx, dy, max_distance, grid_size, obstacle_data)
        possible_movements[direction] = distance
    return possible_movements

def calculate_movement_distance(x, y, dx, dy, max_distance, grid_size, obstacle_data):
    for distance in range(1, max_distance + 1):
        new_x, new_y = x + dx * distance, y + dy * distance
        if not (0 <= new_x < grid_size[0] and 0 <= new_y < grid_size[1]):
            return max_distance
        if is_obstacle(new_x, new_y, obstacle_data):
            return distance - 1
    return max_distance

def calculate_destination_directions(x, y, max_distance, grid_size, obstacle_data, destinations):
    destination_direction = {}
    for dest_name, (dest_x, dest_y) in destinations.items():
        if dest_x == x and dest_y == y:
            destination_direction[dest_name] = {
                "direction": "Here",
                "path_distance": 0,
                "total_distance": 0
            }
        else:
            direction, distance, total_distance = calculate_direction_and_distance((x, y), (dest_x, dest_y), grid_size, obstacle_data, max_distance)
            if direction and distance is not None:
                destination_direction[dest_name] = {
                    "direction": direction,
                    "path_distance": min(distance, max_distance),
                    "total_distance": total_distance
                }
            else:
                print(f"No valid path found to destination {dest_name}")
    return destination_direction

def calculate_path_direction_and_distance(path, x, y, max_distance):
    next_step = path[1]
    dx, dy = next_step[0] - x, next_step[1] - y
    direction, _ = get_direction_from_deltas(dx, dy)
    distance = 1
    for i in range(2, len(path)):
        next_dx, next_dy = path[i][0] - path[i-1][0], path[i][1] - path[i-1][1]
        next_direction, _ = get_direction_from_deltas(next_dx, next_dy)
        if next_direction == direction and distance < max_distance:
            distance += 1
        else:
            break
    return direction, distance

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
    #print(f"Checking obstacle at index {index}: {obstacle_data[index]}")
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