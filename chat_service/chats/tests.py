from django.test import TestCase

# backend/chat_service/test_websocket.py
import websocket 
import json
import time

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Closed: {close_status_code}, {close_msg}")

def on_open(ws):
    print("Connected")
    ws.send(json.dumps({
        "type": "message",
        "content": "Hello from test10 via WebSocket!",
        "message_type": "text"
    }))

if __name__ == "__main__":
    group_id = "123e4567-e89b-12d3-a456-426614174000"
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    ws_url = f"ws://localhost:8002/ws/chats/{group_id}/?token={token}"
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()