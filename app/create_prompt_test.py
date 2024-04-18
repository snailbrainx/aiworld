# use this to see what the prompt looks like.. good for generating and testing with other models.

import sqlite3
import json

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
   
    # JSON formatted appendage
    complete_prompt = f"{system_prompt}\n{output_format}\n\n```json\n{db_schema}\n```"
    return complete_prompt

# Main execution
if __name__ == "__main__":
    prompt_with_schema = create_system_prompt()
    print(prompt_with_schema)