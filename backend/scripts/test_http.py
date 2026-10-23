import requests
try:
    response = requests.get("https://146032ba-7ee7-4318-a310-5ca7d59d27a4.us-west-2-0.aws.cloud.qdrant.io/healthz", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
