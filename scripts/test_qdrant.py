import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    # Try different URL formats
    url = os.getenv("Quadrant_Endpoint")
    api_key = os.getenv("Quadrant_API_KEY")
    
    print(f"Testing URL: {url}")
    
    # Method 1: Full URL
    print("\n--- Method 1: Full URL ---")
    try:
        client = QdrantClient(url=url, api_key=api_key)
        print(f"Success! Collections: {client.get_collections()}")
    except Exception as e:
        print(f"Failed: {e}")

    # Method 2: Host + Port (Stripping protocol)
    print("\n--- Method 2: Host + Port (No protocol) ---")
    try:
        host = url.replace("https://", "").split(":")[0]
        print(f"Testing Host: {host} on port 6333")
        client = QdrantClient(host=host, port=6333, api_key=api_key, https=True)
        print(f"Success! Collections: {client.get_collections()}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_connection()
