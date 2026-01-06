
import requests
import json

ports = [5000, 5001, 8000, 8080, 8888]

for port in ports:
    try:
        url = f"http://127.0.0.1:{port}/api/roles"
        print(f"Testing {url}...")
        response = requests.get(url, timeout=1)
        print(f"Status Code: {response.status_code}")
        
        try:
            data = response.json()
            print("JSON Decode Success")
            print(f"Success: {data.get('success')}")
        except json.JSONDecodeError:
            print("JSON Decode Failed")
            
        break # Stop if we found a server
    except Exception as e:
        print(f"Port {port} failed: {e}")
