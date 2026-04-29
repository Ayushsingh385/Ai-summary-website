import time
import requests

text = "This is a dummy legal text. The Supreme Court ordered that the petitioner must be compensated. It was a clear breach of contract. Section 420 of the IPC is invoked. The amount of 50000 rupees is to be paid."

print("Testing endpoints...")

for endpoint in ['classify', 'analyze', 'keywords', 'summarize']:
    start = time.time()
    try:
        if endpoint == 'summarize':
            res = requests.post(f"http://127.0.0.1:8000/api/{endpoint}", json={"text": text, "length": "short", "language": "en"})
        elif endpoint == 'keywords':
            res = requests.post(f"http://127.0.0.1:8000/api/{endpoint}", json={"text": text, "top_n": 5})
        else:
            res = requests.post(f"http://127.0.0.1:8000/api/{endpoint}", json={"text": text})
        
        elapsed = time.time() - start
        print(f"[{endpoint}] Status: {res.status_code}, Time: {elapsed:.2f}s")
    except Exception as e:
        print(f"[{endpoint}] Error: {e}")
