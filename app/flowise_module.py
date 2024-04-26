import requests
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# API URLs mapped by model names
API_URLS = {
    "flowise_llama3_8B": "http://192.168.5.218:3000/api/v1/prediction/f638d90b-3212-4f5d-948d-9538309a1019",
    "flowise_llama3_70B": "http://192.168.5.218:3000/api/v1/prediction/86cb151e-3171-4854-9304-af5f3469edc0",
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
        "move": {"type": ["string", "null"]},
        "distance": {"type": ["number", "null"]},
        "action": {"type": ["string", "null"]},
        "action_target": {"type": ["string", "null"]},
        "pickup_item": {"type": ["string", "null"]}
    },
    "required": ["thought", "talk", "move", "distance", "action", "action_target", "pickup_item"]
}

def read_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read()

def query_new_api(question, url):
    response = requests.post(url, json={"question": question})
    return response.json()

def get_flowise_response(user_content, valid_entities, model_name, max_retries=3, timeout_duration=30):
    if model_name not in API_URLS:
        raise ValueError("Invalid model name provided.")
    api_url = API_URLS[model_name]
    
    type_map = {
        "string": str,
        "number": int,
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None)
    }

    for attempt in range(max_retries):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(query_new_api, user_content, api_url)
            try:
                response = future.result(timeout=timeout_duration)
                if 'json' in response:
                    json_response = response['json']
                    for property, value in json_response.items():
                        if property not in OUTPUT_FORMAT["properties"]:
                            raise ValueError(f"Unexpected property: {property}")
                        expected_types = OUTPUT_FORMAT["properties"][property]["type"]
                        if not any(isinstance(value, type_map[t]) for t in expected_types):
                            raise ValueError(f"Incorrect type for property {property}")
                        if property == "move":
                            if value == '0' or value is None:
                                json_response["move"] = 'N'  # Default to North if '0' or None
                            elif value not in directions:
                                raise ValueError("Invalid direction for move")
                        if property == "action":
                            if json_response["action"] != '0' and json_response["action"] not in ["attack", "heal"]:
                                raise ValueError("Invalid action")
                        if property == "action_target":
                            if json_response["action_target"] != '0' and json_response["action_target"] is not None:
                                found_valid_entity = False
                                for entity in valid_entities:
                                    if entity == json_response["action_target"]:
                                        found_valid_entity = True
                                        break
                                if not found_valid_entity:
                                    json_response["action_target"] = '0'  # Set to '0' if no valid entity is found
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
    "your_personality": "xxxxx"""
    valid_entities = ["Lilith", "Thorn", "Voltan"]  # Example list of valid entities
    model_name = "flowise_llama3_8B"  # Select the model
    result = get_flowise_response(user_input, valid_entities, model_name)
    print("Content part of the response:")
    print(result)