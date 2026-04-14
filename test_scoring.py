import json
import os
import sys
import requests
from dotenv import load_dotenv

def test_scoring(file_path):
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("SCORING_API_KEY")
    # Use the specific IP and port provided by the user
    base_url = "http://88.222.212.15:8011"
    
    if not api_key:
        print("Error: SCORING_API_KEY not found in .env file.")
        return

    # Load input data
    try:
        with open(file_path, 'r') as f:
            payload = json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return

    print(f"--- Sending request to {base_url}/score ---")
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(f"{base_url}/score", json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            dominant = result.get("dominant_risk", {})
            print("\n[SUCCESS] Scoring Complete")
            print(f"Dominant Risk: {dominant.get('label')} ({dominant.get('probability'):.4f})")
            
            print("\nOther Risks:")
            for risk in result.get("other_risks", []):
                print(f" - {risk.get('label')}: {risk.get('probability'):.4f}")
        else:
            print(f"\n[ERROR] API returned status {response.status_code}")
            print(f"Detail: {response.text}")
            
    except Exception as e:
        print(f"Error connecting to API: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_scoring.py <path_to_json_file>")
        # Fallback to example.json if it exists
        if os.path.exists("example.json"):
            print("No file provided. Testing with example.json...")
            test_scoring("example.json")
    else:
        test_scoring(sys.argv[1])
