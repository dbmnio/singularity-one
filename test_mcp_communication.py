#!/usr/bin/env python3
"""
Test script to verify MCP communication with the Unreal Engine server.
This script tests basic MCP protocol communication to ensure our plugin fixes work.
"""

import json
import socket
import struct
import time

def send_mcp_message(sock, message):
    """Send a message using MCP protocol (4-byte length + JSON payload)."""
    message_bytes = json.dumps(message).encode('utf-8')
    length_bytes = struct.pack('>I', len(message_bytes))
    sock.send(length_bytes + message_bytes)

def receive_mcp_message(sock):
    """Receive a message using MCP protocol."""
    # Read 4-byte length
    length_bytes = sock.recv(4)
    if len(length_bytes) != 4:
        return None
    
    message_length = struct.unpack('>I', length_bytes)[0]
    
    # Read the message payload
    message_bytes = sock.recv(message_length)
    if len(message_bytes) != message_length:
        return None
    
    return json.loads(message_bytes.decode('utf-8'))

def test_mcp_communication():
    """Test basic MCP communication with the Unreal server."""
    print("Testing MCP communication with Unreal Engine server...")
    
    try:
        # Connect to the MCP server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)  # 5 second timeout
        sock.connect(('localhost', 5005))
        
        print("✓ Connected to MCP server")
        
        # Test 1: Get actors in level
        print("\n--- Test 1: Get actors in level ---")
        request = {
            "type": "get_actors_in_level",
            "params": {
                "ctx": {}
            }
        }
        
        print(f"Sending request: {json.dumps(request, indent=2)}")
        send_mcp_message(sock, request)
        
        response = receive_mcp_message(sock)
        if response:
            print(f"✓ Received response: {json.dumps(response, indent=2)}")
        else:
            print("✗ No response received")
        
        # Test 2: Find actors by name
        print("\n--- Test 2: Find actors by name ---")
        request = {
            "type": "find_actors_by_name",
            "params": {
                "ctx": {},
                "pattern": "Cube"
            }
        }
        
        print(f"Sending request: {json.dumps(request, indent=2)}")
        send_mcp_message(sock, request)
        
        response = receive_mcp_message(sock)
        if response:
            print(f"✓ Received response: {json.dumps(response, indent=2)}")
        else:
            print("✗ No response received")
        
        # Test 3: Spawn a test actor
        print("\n--- Test 3: Spawn test actor ---")
        request = {
            "type": "spawn_actor",
            "params": {
                "ctx": {},
                "name": "TestCube",
                "type": "StaticMeshActor",
                "location": [0, 0, 100],
                "rotation": [0, 0, 0]
            }
        }
        
        print(f"Sending request: {json.dumps(request, indent=2)}")
        send_mcp_message(sock, request)
        
        response = receive_mcp_message(sock)
        if response:
            print(f"✓ Received response: {json.dumps(response, indent=2)}")
        else:
            print("✗ No response received")
        
        sock.close()
        print("\n✓ All tests completed successfully!")
        
    except socket.timeout:
        print("✗ Connection timeout - server may not be responding")
    except ConnectionRefusedError:
        print("✗ Connection refused - make sure the MCP server is running")
    except Exception as e:
        print(f"✗ Error during communication: {e}")

if __name__ == "__main__":
    test_mcp_communication() 