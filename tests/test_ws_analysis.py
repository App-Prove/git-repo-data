import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from app.main import app  # Adjust import path as needed

client = TestClient(app)

def test_ws_test_endpoint():
    with client.websocket_connect("/ws/analysis/test") as websocket:
        # Should receive 10 messages
        for i in range(10):
            data = websocket.receive_json()
            assert data == {"success": f"Message {i}"}

def test_ws_message_endpoint():
    with client.websocket_connect("/ws/analysis/message") as websocket:
        test_message = "Hello WebSocket!"
        websocket.send_text(test_message)
        data = websocket.receive_json()
        assert data == {"success": f"Message text was: {test_message}"}

def test_ws_analysis_endpoint():
    with client.websocket_connect("/ws/analysis/analysis") as websocket:
        # Send repository data
        websocket.send_json({
            "repositoryURL": "https://github.com/username/repo"
        })
        
        # Check connecting step
        data = websocket.receive_json()
        assert data["step_name"] == "connecting"
        assert data["status"] == "inProgress"
        
        # Check success connection
        data = websocket.receive_json()
        assert data["step_name"] == "connecting"
        assert data["status"] == "success"
        
        # Continue receiving messages until websocket closes
        try:
            while True:
                data = websocket.receive_json()
                # You can add more specific assertions here
        except:
            pass 