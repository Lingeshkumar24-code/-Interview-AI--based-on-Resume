"""
ai_client.py - Shared AI client utility for InterviewAI
Handles calling the OpenAI-compatible Groq API for text generation.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_KEY = os.getenv('GROQ_API_KEY')
BASE_URL = os.getenv('GROQ_BASE_URL', 'https://api.groq.com/openai/v1')
MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')


def call_ai(prompt, temperature=0.7, max_retries=3):
    """
    Call the OpenAI-compatible Groq API with automatic retries on rate limits or transient errors.
    
    Args:
        prompt (str): The prompt message to send to the model.
        temperature (float): Controls randomness of the output.
        max_retries (int): Number of retries for rate limits or server errors.
        
    Returns:
        str: The response content from the model.
    """
    if not API_KEY:
        raise ValueError('GROQ_API_KEY is not configured.')

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }
    
    delay = 2
    for attempt in range(max_retries + 1):
        try:
            # We use a 45 second timeout because large responses can take time
            response = requests.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=data,
                timeout=45
            )
            
            # If rate limited (429) or temporary server error (502, 503, 504)
            if response.status_code == 429 or response.status_code in [502, 503, 504]:
                if attempt == max_retries:
                    raise Exception(f"AI Service error (status {response.status_code}): {response.text}")
                
                # Retrieve Retry-After header if present, otherwise use exponential delay
                retry_after = response.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after and retry_after.isdigit() else delay
                
                print(f"AI API rate limit or transient error (status {response.status_code}) encountered. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                delay *= 2
                continue
                
            # If other error status
            if response.status_code != 200:
                print(f"AI API error (status {response.status_code}): {response.text}")
                raise Exception(f"AI Service error (status {response.status_code})")
                
            # Success
            response_json = response.json()
            return response_json["choices"][0]["message"]["content"].strip()
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                print(f"AI API connection error: {e}")
                raise Exception(f"AI connection error: {str(e)}")
            print(f"AI API request failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2
            
    raise Exception("AI Service call failed after all retries.")
