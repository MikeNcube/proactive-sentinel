import os
import json
import requests
from datetime import datetime

def query_ollama(prompt, model="llama3"):
    '''Send a prompt to local Ollama and get response'''
    try:
        response = requests.post('http://localhost:11434/api/generate', 
                                json={
                                    "model": model,
                                    "prompt": prompt,
                                    "stream": False
                                })
        return response.json()['response']
    except Exception as e:
        return f"Error querying Ollama: {str(e)}"

def load_prompt(agent_name, **kwargs):
    '''Load a prompt template and fill in variables'''
    prompt_path = f"agents/prompts/{agent_name}_agent.txt"
    try:
        with open(prompt_path, 'r') as f:
            prompt = f.read()
        return prompt.format(**kwargs)
    except FileNotFoundError:
        return f"Prompt file not found: {prompt_path}"
    except KeyError as e:
        return f"Missing template variable: {e}"

def save_to_memory(content, category):
    '''Save content to memory (for future reference)'''
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"agents/memory/{category}_{timestamp}.json"
    try:
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "category": category,
                "content": content
            }, f, indent=2)
        return filename
    except Exception as e:
        return f"Error saving to memory: {str(e)}"
