#!/usr/bin/env python3
"""
Test script to test a single command with longer timeout.
"""

import json
import socket
import struct
import time

def send_mcp_message(sock, message):
    """Send a message using MCP protocol (4-byte length + JSON payload)."""
    message_bytes = json.dumps(message).encode('utf-8')
    length_bytes = struct.pack('<I', len(message_bytes))  # Note: Unreal uses little-endian
    sock.send(length_bytes + message_bytes)

def receive_mcp_message(sock, timeout=10):
    """Receive a message using MCP protocol with timeout."""
    try:
        sock.settimeout(timeout)
        
        # Read 4-byte length
        length_bytes = sock.recv(4)
        if len(length_bytes) != 4:
            return None
        
        message_length = struct.unpack('<I', length_bytes)[0]  # Note: Unreal uses little-endian
        print(f"Expecting message of length: {message_length}")
        
        # Read the message payload
        message_bytes = b''
        while len(message_bytes) < message_length:
            chunk = sock.recv(message_length - len(message_bytes))
            if not chunk:
                break
            message_bytes += chunk
        
        if len(message_bytes) == message_length:
            message = json.loads(message_bytes.decode('utf-8'))
            return message
        else:
            print(f"Received {len(message_bytes)} bytes, expected {message_length}")
            return None
            
    except socket.timeout:
        print(f"Timeout after {timeout} seconds")
        return None
    except Exception as e:
        print(f"Error receiving message: {e}")
        return None

def main():
    print("Testing single command with longer timeout...")
    
    # Connect to Unreal Engine
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('localhost', 55557))
        print("✓ Connected to Unreal Engine MCP plugin")
        
        # Test spawn_actor command with longer timeout
        request = {
            "type": "spawn_actor",
            "params": {
                "ctx": {},
                "name": "TestCube5",
                "type": "StaticMeshActor",
                "location": [400, 0, 100],
                "rotation": [0, 0, 0]
            }
        }
        
        print(f"Sending request: {json.dumps(request, indent=2)}")
        send_mcp_message(sock, request)
        
        # Wait for response with longer timeout
        response = receive_mcp_message(sock, timeout=15)
        
        if response:
            print(f"✓ Received response: {json.dumps(response, indent=2)}")
        else:
            print("✗ No response received")
            
    except Exception as e:
        print(f"✗ Error during communication: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    main() 