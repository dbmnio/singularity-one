#!/usr/bin/env python3
"""
Test script to verify MCP communication with the Unreal Engine server.
This script tests basic MCP protocol communication to ensure our plugin fixes work.
Updated to match the expected behavior: one command per connection.
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

def receive_mcp_message(sock, timeout=15):
    """Receive a message using MCP protocol with longer timeout."""
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
            print(f"Received incomplete message: {len(message_bytes)}/{message_length} bytes")
            return None
            
    except socket.timeout:
        print("Socket timeout")
        return None
    except Exception as e:
        print(f"Error receiving message: {e}")
        return None

def create_connection():
    """Create a new connection to the Unreal Engine MCP plugin."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(('127.0.0.1', 55557))
        return sock
    except Exception as e:
        print(f"Failed to create connection: {e}")
        return None

def test_command(command_type, params=None):
    """Test a single command with a fresh connection."""
    print(f"\n=== Testing {command_type} ===")
    
    # Create a fresh connection for each command
    sock = create_connection()
    if not sock:
        print(f"Failed to connect for {command_type}")
        return False
    
    try:
        # Prepare the request
        request = {
            "type": command_type,
            "params": params or {}
        }
        
        print(f"Sending request: {json.dumps(request, indent=2)}")
        
        # Send the request
        send_mcp_message(sock, request)
        
        # Receive the response
        response = receive_mcp_message(sock)
        
        if response:
            print(f"Response: {json.dumps(response, indent=2)}")
            return True
        else:
            print(f"No response received for {command_type}")
            return False
            
    except Exception as e:
        print(f"Error testing {command_type}: {e}")
        return False
    finally:
        # Always close the connection after each command
        sock.close()

def main():
    """Test various MCP commands with fresh connections."""
    print("Testing Unreal Engine MCP Plugin Communication")
    print("=" * 50)
    
    # Test ping command
    success1 = test_command("ping")
    
    # Test get_actors_in_level command
    success2 = test_command("get_actors_in_level")
    
    # Test find_actors_by_name command
    success3 = test_command("find_actors_by_name", {"ctx": {}, "pattern": "Cube"})
    
    # Test spawn_actor command
    success4 = test_command("spawn_actor", {
        "ctx": {},
        "name": "TestCube2",
        "type": "StaticMeshActor",
        "location": [100, 0, 100],
        "rotation": [0, 0, 0]
    })
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Ping: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Get Actors: {'✅ PASS' if success2 else '❌ FAIL'}")
    print(f"Find Actors: {'✅ PASS' if success3 else '❌ FAIL'}")
    print(f"Spawn Actor: {'✅ PASS' if success4 else '❌ FAIL'}")
    
    all_passed = success1 and success2 and success3 and success4
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

if __name__ == "__main__":
    main() 