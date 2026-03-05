
import os
from google import genai

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("GOOGLE_API_KEY not found.")
    exit(1)

client = genai.Client(api_key=api_key)

try:
    print("Fetching model list from Google API...")
    # The new google-genai library usage might differ slightly, let's try the standard list_models
    # or iterate if it returns a pager.
    # Based on recent library updates, client.models.list() is likely correct.
    
    # We'll print name, display_name, and supported methods
    for model in client.models.list():
        print(f"- {model.name} ({model.display_name})")
        
except Exception as e:
    print(f"Error fetching models: {e}")
