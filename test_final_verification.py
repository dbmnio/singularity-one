#!/usr/bin/env python3
"""
Final verification test for UnrealMCP plugin fixes.
Tests each command individually with fresh connections.
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
            print(f"Received {len(message_bytes)} bytes, expected {message_length}")
            return None
            
    except socket.timeout:
        print(f"Error receiving message: timed out after {timeout} seconds")
        return None
    except Exception as e:
        print(f"Error receiving message: {e}")
        return None

def test_command(command_type, params, description):
    """Test a single command with a fresh connection."""
    print(f"\n--- {description} ---")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('localhost', 55557))
        
        request = {
            "type": command_type,
            "params": params
        }
        
        print(f"Sending request: {json.dumps(request, indent=2)}")
        send_mcp_message(sock, request)
        
        response = receive_mcp_message(sock, timeout=15)
        
        if response:
            print(f"✓ Received response: {json.dumps(response, indent=2)}")
            return True
        else:
            print("✗ No response received")
            return False
            
    except Exception as e:
        print(f"✗ Error during communication: {e}")
        return False
    finally:
        sock.close()

def main():
    print("Final verification test for UnrealMCP plugin fixes")
    print("Testing each command individually with fresh connections...")
    
    # Test ping command
    test_command("ping", {}, "Test 1: Ping command")
    
    # Test get_actors_in_level command
    test_command("get_actors_in_level", {"ctx": {}}, "Test 2: Get actors in level")
    
    # Test find_actors_by_name command
    test_command("find_actors_by_name", {"ctx": {}, "pattern": "Cube"}, "Test 3: Find actors by name")
    
    # Test spawn_actor command
    test_command("spawn_actor", {
        "ctx": {},
        "name": "TestCube2",
        "type": "StaticMeshActor",
        "location": [0, 0, 200],
        "rotation": [0, 0, 0]
    }, "Test 4: Spawn test actor")
    
    print("\n✓ All tests completed!")

if __name__ == "__main__":
    main() 