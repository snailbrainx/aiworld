import requests
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# API URLs mapped by model names
API_URLS = {
    "flowise_claude3-opus": "http://192.168.5.218:3000/api/v1/prediction/97640c0b-54af-4ef5-a10a-45685fafe2d5",
    "flowise_llama3_70B": "http://192.168.5.218:3000/api/v1/prediction/72b204fe-2354-4b27-a641-557cb931b9a5",
    "flowise_gpt-4-turbo": "http://192.168.5.218:3000/api/v1/prediction/62c689ea-8191-4331-804b-e2eeec21cc2c",
    "flowise_35-turbo": "http://192.168.5.218:3000/api/v1/prediction/1474e6d6-8b9a-4062-ace3-afc05baf8a9d"
}

# Directions for movement
directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# Output format schema
OUTPUT_FORMAT = {
    "type": "object",
    "properties": {
        "thought": {"type": ["string", "null"]},
        "talk": {"type": ["string", "null"]},
        "direction": {"type": ["string", "null"]},
        "distance": {"type": ["number", "null"]},
        "action": {"type": ["string", "null"]},
        "action_target": {"type": ["string", "null"]},
        "pickup_item": {"type": ["string", "null"]}
    },
    "required": ["thought", "talk", "direction", "distance", "action", "action_target", "pickup_item"]
}

def read_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read()

def query_new_api(question, url):
    response = requests.post(url, json={"question": question})
    return response.json()

def validate_response(json_response, valid_entities, valid_items):
    type_map = {
        "string": str,
        "number": int,
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None)
    }

    def validate_property(property, value):
        if property not in OUTPUT_FORMAT["properties"]:
            raise ValueError(f"Unexpected property: {property}")
        expected_types = OUTPUT_FORMAT["properties"][property]["type"]
        if not any(isinstance(value, type_map[t]) for t in expected_types):
            raise ValueError(f"Incorrect type for property {property}")

    def validate_direction(value):
        if json_response.get("action") != "move":
            json_response["direction"] = 'N'  # Default to North if action is not "move"
            json_response["distance"] = 0  # Set distance to 0 if action is not "move"
        elif value == '0' or value is None:
            json_response["direction"] = 'N'  # Default to North if '0' or None
        elif value not in directions:
            raise ValueError("Invalid direction")

    def validate_action(value):
        if value != '0' and value not in ["attack", "heal", "move", "pickup"]:
            raise ValueError("Invalid action")

    def validate_action_target(value):
        if value != '0' and value is not None and value not in valid_entities and value not in valid_items:
            json_response["action_target"] = '0'  # Set to '0' if no valid entity or item is found

    for property, value in json_response.items():
        validate_property(property, value)
        if property == "direction": 
            validate_direction(value)
        elif property == "action":
            validate_action(value)
        elif property == "action_target":
            validate_action_target(value)

    return json_response

def get_flowise_response(user_content, valid_entities, valid_items, model_name, max_retries=3, timeout_duration=60):
    if model_name not in API_URLS:
        raise ValueError("Invalid model name provided.")
    api_url = API_URLS[model_name]

    for attempt in range(max_retries):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(query_new_api, user_content, api_url)
            try:
                response = future.result(timeout=timeout_duration)
                if 'json' in response:
                    json_response = response['json']
                    return validate_response(json_response, valid_entities, valid_items)
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