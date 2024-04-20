# llama3_70B.py
import openai
import sqlite3
import json
import re

# API Key and Base URL for the local server
API_KEY = 'lm-studio'
BASE_URL = "http://127.0.0.1:1234/v1"

# Initialize OpenAI client for the local server
client = openai.OpenAI(base_url=BASE_URL, api_key=API_KEY)

directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

def read_file(filename):
    """Helper function to read content from a given filename."""
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read()

def fetch_schema_from_db():
    """Fetch rows from the SQLite database 'output_format' table and construct the JSON schema."""
    conn = sqlite3.connect('aiworld.db')
    cursor = conn.cursor()
    cursor.execute('SELECT property, type, description FROM output_format')
   
    schema = {"type": "object", "properties": {}, "required": []}
    for property, type, description in cursor.fetchall():
        schema["properties"][property] = {"type": type, "description": description}
        schema["required"].append(property)
   
    conn.close()
    return json.dumps(schema, indent=2)

def create_system_prompt():
    """Construct the complete system prompt from files and the DB schema."""
    system_prompt = read_file("system_prompt.txt")
    output_format = read_file("output_format.txt")
    db_schema = fetch_schema_from_db()
   
    complete_prompt = f"{system_prompt}\n{output_format}\n\n```json\n{db_schema}\n```"
    return complete_prompt

def extract_json(content):
    """Extract JSON from the response content, even if mixed with other text."""
    try:
        # Directly return if the entire content is valid JSON
        return json.loads(content)
    except json.JSONDecodeError:
        # Attempt to find JSON objects within the text
        pattern = re.compile(r'({.*?})', re.DOTALL)
        matches = pattern.findall(content)
        for match in matches:
            try:
                # Check if the extracted string is valid JSON
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        raise ValueError("No valid JSON found in the response")

def get_llama3_response(user_content, valid_entities, max_retries=3):
    system_prompt = create_system_prompt()
    db_schema = json.loads(fetch_schema_from_db())
    type_map = {
        "string": str,
        "number": int,
        "boolean": bool,
        "array": list,
        "object": dict
    }
    for attempt in range(max_retries):
        response = client.chat.completions.create(
            model="lmstudio-community/Meta-Llama-3-70B-Instruct-GGUF",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7,
            max_tokens=321,
            top_p=1,
            frequency_penalty=0.4,
            presence_penalty=0.4
        )
        content = response.choices[0].message.content
        print("API Raw Response:", content)
        try:
            json_response = extract_json(content)
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
                    if value not in directions:
                        json_response["move"] = "N"
                if property == "ability":
                    if value == '' or value is None or value == '0':
                        json_response["ability"] = '0'
                    elif value not in ["attack", "heal"]:
                        raise ValueError("Invalid ability")
                if property == "ability_target":
                    if value == '' or value is None or value == '0':
                        json_response["ability_target"] = '0'
                    else:
                        found_valid_entity = False
                        for entity in valid_entities:
                            if entity == value:
                                found_valid_entity = True
                                break
                        if not found_valid_entity:
                            json_response["ability_target"] = '0'
            return json_response
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise e
    raise RuntimeError("Failed to get a conforming response after max retries.")

# Example usage and testing:
if __name__ == "__main__":
    user_input = """What are the best strategies for managing time?"""
    result = get_llama3_response(user_input, ["Alice", "Bob"])
    print("Content part of the response:")
    print(result)