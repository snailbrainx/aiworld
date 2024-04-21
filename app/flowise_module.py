import requests
import sqlite3
import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# API URLs mapped by model names
API_URLS = {
    "flowise_llama3_8B": "xxx",
    "flowise_llama3_70B": "xxxx",
    "flowise_gpt-4-turbo": "xxxx",
    "flowise_35-turbo": "xxxx"
}

# Directions for movement
directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

def read_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read()

def fetch_schema_from_db():
    conn = sqlite3.connect('aiworld.db')
    cursor = conn.cursor()
    cursor.execute('SELECT property, type, description FROM output_format')
    schema = {"type": "object", "properties": {}, "required": []}
    for property, type, description in cursor.fetchall():
        schema["properties"][property] = {"type": type, "description": description}
        schema["required"].append(property)
    conn.close()
    return schema

def query_new_api(question, url):
    response = requests.post(url, json={"question": question})
    return response.json()

def get_flowise_response(user_content, valid_entities, model_name, max_retries=3, timeout_duration=30):
    if model_name not in API_URLS:
        raise ValueError("Invalid model name provided.")
    api_url = API_URLS[model_name]
    
    db_schema = fetch_schema_from_db()
    type_map = {
        "string": str,
        "number": int,
        "boolean": bool,
        "array": list,
        "object": dict
    }

    for attempt in range(max_retries):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(query_new_api, user_content, api_url)
            try:
                response = future.result(timeout=timeout_duration)
                if 'json' in response:
                    json_response = response['json']
                    for property in db_schema["required"]:
                        if property not in json_response:
                            raise ValueError(f"Missing required property: {property}")
                    for property, value in json_response.items():
                        if property not in db_schema["properties"]:
                            raise ValueError(f"Unexpected property: {property}")
                        expected_type = type_map[db_schema["properties"][property]["type"]]
                        if not isinstance(value, expected_type):
                            raise ValueError(f"Incorrect type for property {property}")
                        if property == "move":
                            if value == '0':
                                json_response["move"] = 'N'  # Default to North if '0'
                            elif value not in directions:
                                raise ValueError("Invalid direction for move")
                        if property == "ability":
                            if json_response["ability"] != '0' and json_response["ability"] not in ["attack", "heal"]:
                                raise ValueError("Invalid ability")
                        if property == "ability_target":
                            if json_response["ability_target"] != '0':
                                found_valid_entity = False
                                for entity in valid_entities:
                                    if entity == json_response["ability_target"]:
                                        found_valid_entity = True
                                        break
                                if not found_valid_entity:
                                    json_response["ability_target"] = '0'  # Set to '0' if no valid entity is found
                    return json_response
                else:
                    raise ValueError("No valid content found in the response")
            except TimeoutError:
                print(f"Attempt {attempt + 1}: API request timed out after {timeout_duration} seconds.")
            except json.JSONDecodeError as e:
                print(f"JSON Parsing Error: {str(e)}")
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise e

    raise RuntimeError("Failed to get a conforming response after max retries.")

# Example usage and testing:
if __name__ == "__main__":
    user_input = """ {
  "present_time": {
    "your_name": "Mira",
    "your_personality": "Mira, the gentle healer whose touch revives the fallen. You are on the blue team.

The Red team is Lilith, Thorn, Elara and Drake.
The Blue team is Mira, Voltan, Seraphine and Hulk.
Work as a team.",
    "available_ability": "heal",
    "health_points": 300,
    "time": 1,
    "position": [
      250,
      250
    ],
    "possible_directions": {
      "N": 150,
      "NE": 150,
      "E": 150,
      "SE": 150,
      "S": 150,
      "SW": 150,
      "W": 150,
      "NW": 150
    },
    "nearby_entities": {
      "Lilith": {
        "direction": "Here",
        "distance": 0,
        "health_points": 300,
        "in_talk_range": true,
        "talk": "Red Team, gather around me for strategizing. Blue Team members are close!",
        "in_range_of_heal": true
      },
      "Thorn": {
        "direction": "Here",
        "distance": 0,
        "health_points": 300,
        "in_talk_range": true
      },
      "Voltan": {
        "direction": "Here",
        "distance": 0,
        "health_points": 300,
        "in_talk_range": true
      },
      "Elara": {
        "direction": "Here",
        "distance": 0,
        "health_points": 300,
        "in_talk_range": true
      },
      "Seraphine": {
        "direction": "Here",
        "distance": 0,
        "health_points": 300,
        "in_talk_range": true
      }
    }
  },
  "history": []
}"""
    valid_entities = ["Lilith", "Thorn", "Voltan"]  # Example list of valid entities
    model_name = "flowise_llama3_8B"  # Select the model
    result = get_flowise_response(user_input, valid_entities, model_name)
    print("Content part of the response:")
    print(result)