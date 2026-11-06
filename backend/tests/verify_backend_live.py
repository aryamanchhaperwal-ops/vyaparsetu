import asyncio
import socket
import time
import threading
import httpx
import uvicorn
from backend.app.main import app
from backend.app.llm.client import bharatcode_client

def test_uvicorn_live_server():
    # Find free port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    time.sleep(1.5)  # Allow server to bind

    base_url = f"http://127.0.0.1:{port}"
    print(f"Uvicorn live server started on {base_url}")

    with httpx.Client(base_url=base_url, timeout=5.0) as client:
        # 1. Health check
        res = client.get("/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print(f"[PASS] Health check returned 200: {res.json()['status']}")

        # 2. OpenAPI JSON
        res = client.get("/api/v1/openapi.json")
        assert res.status_code == 200, f"OpenAPI failed: {res.text}"
        print(f"[PASS] OpenAPI spec loaded with {len(res.json()['paths'])} routes")

        # 3. GST Compute endpoint
        res = client.post("/api/v1/gst/compute", json={
            "amount": 50000.0,
            "rate_percent": 18.0,
            "is_interstate": False,
            "is_inclusive": False
        })
        assert res.status_code == 200
        data = res.json()
        assert data["cgst"] == "4500.00"
        assert data["sgst"] == "4500.00"
        print("[PASS] Deterministic GST compute endpoint live verification")

    server.should_exit = True
    print("Live server test passed successfully!")

async def test_bharatcode_authenticated_call():
    print("Testing BharatCode authenticated client with local .env credentials...")
    messages = [
        {"role": "system", "content": "You are BharatCode assistant."},
        {"role": "user", "content": "Analyze narration: 'Dukaan rent 15000 paid to Sharma'"}
    ]
    resp = await bharatcode_client.chat_completion(messages)
    assert "content" in resp
    print("[PASS] BharatCode client completed authenticated call flow!")
    print(f"       Response Preview: {resp['content'][:80]}...")

if __name__ == "__main__":
    test_uvicorn_live_server()
    asyncio.run(test_bharatcode_authenticated_call())

