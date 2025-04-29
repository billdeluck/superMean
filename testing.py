# This script sends a request to the AIML API to generate a one-sentence story about numbers.
import requests

# Set up the endpoint, API key, and payload
api_url = "https://api.aimlapi.com/v1/chat/completions"
api_key = "e3a9cca1cac742af96d97fab15193fd6"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Write a one-sentence story about numbers."}]
}

# Make the API request
response = requests.post(api_url, headers=headers, json=data)

# Print the result
if response.status_code == 200:
    print(response.json().get("choices")[0].get("message").get("content"))
else:
    print(f"Error: {response.status_code}, {response.text}")
