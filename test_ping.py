#!/usr/bin/env python3
"""
Simple ping test to verify basic communication with Unreal Engine MCP plugin.
"""

import json
import socket
import struct

def send_mcp_message(sock, message):
    """Send a message using MCP protocol (4-byte length + JSON payload)."""
    message_bytes = json.dumps(message).encode('utf-8')
    length_bytes = struct.pack('<I', len(message_bytes))  # Note: Unreal uses little-endian
    sock.send(length_bytes + message_bytes)

def receive_mcp_message(sock):
    """Receive a message using MCP protocol."""
    try:
        # Read 4-byte length
        length_bytes = sock.recv(4)
        if len(length_bytes) != 4:
            return None
        
        message_length = struct.unpack('<I', length_bytes)[0]  # Note: Unreal uses little-endian
        print(f"Expecting message of length: {message_length}")
        
        # Read the message payload
        message_bytes = sock.recv(message_length)
        if len(message_bytes) != message_length:
            print(f"Received {len(message_bytes)} bytes, expected {message_length}")
            return None
        
        return json.loads(message_bytes.decode('utf-8'))
    except Exception as e:
        print(f"Error receiving message: {e}")
        return None

def test_ping():
    """Test basic ping command."""
    print("Testing ping command with Unreal Engine MCP plugin...")
    
    try:
        # Connect to the Unreal Engine MCP plugin
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)  # 10 second timeout
        sock.connect(('127.0.0.1', 55557))
        
        print("✓ Connected to Unreal Engine MCP plugin")
        
        # Test ping command
        request = {
            "type": "ping",
            "params": {}
        }
        
        print(f"Sending ping request: {json.dumps(request, indent=2)}")
        send_mcp_message(sock, request)
        
        response = receive_mcp_message(sock)
        if response:
            print(f"✓ Received response: {json.dumps(response, indent=2)}")
        else:
            print("✗ No response received")
        
        sock.close()
        
    except socket.timeout:
        print("✗ Connection timeout")
    except ConnectionRefusedError:
        print("✗ Connection refused")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_ping() 