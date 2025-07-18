"""
Unreal Engine MCP Server

A simple MCP server for interacting with Unreal Engine.
"""

import logging
import socket
import sys
import json
from pathlib import Path

# Add the script's directory to the Python path to resolve local imports
sys.path.append(str(Path(__file__).parent))

from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, Optional
from fastmcp import FastMCP

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,  # Set to INFO for production, DEBUG for development
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('unreal_mcp.log'),
        # logging.StreamHandler(sys.stdout) # Keep commented out to avoid polluting stdout
    ]
)
logger = logging.getLogger("UnrealMCP")

# Configuration
UNREAL_HOST = "127.0.0.1"
UNREAL_PORT = 55557

class UnrealConnection:
    """Manages the connection to an Unreal Engine instance for sending a single command."""
    
    def __init__(self):
        """Initialize the connection manager."""
        self.socket: Optional[socket.socket] = None
        self.connected = False
    
    def connect(self) -> bool:
        """Create a new socket and connect to the Unreal Engine instance."""
        if self.socket:
            self.disconnect()

        try:
            logger.info(f"Connecting to Unreal at {UNREAL_HOST}:{UNREAL_PORT}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 10 second timeout for connection
            
            # Set socket options
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            
            self.socket.connect((UNREAL_HOST, UNREAL_PORT))
            self.connected = True
            logger.info("Successfully connected to Unreal Engine")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Unreal: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Disconnect from the Unreal Engine instance."""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.warning(f"Error while closing socket: {e}")
        self.socket = None
        self.connected = False

    def receive_full_response(self) -> bytes:
        """Receive a complete response from Unreal, handling chunked data."""
        if not self.socket:
            raise ConnectionError("Socket is not connected.")

        try:
            # First, read the 4-byte length prefix
            raw_msglen = self.socket.recv(4)
            if not raw_msglen:
                logger.error("No data received from Unreal when expecting message length.")
                return b''
            
            msglen = int.from_bytes(raw_msglen, 'little')
            logger.info(f"Expecting message of length: {msglen}")

            # Now, read the full message based on the length
            # Use a loop to handle chunked data
            received_data = b''
            while len(received_data) < msglen:
                chunk = self.socket.recv(msglen - len(received_data))
                if not chunk:
                    logger.error(f"Connection closed while receiving data. Expected {msglen} bytes, got {len(received_data)}")
                    break
                received_data += chunk
            
            logger.info(f"Received {len(received_data)} bytes of response data")
            return received_data
            
        except socket.timeout:
            logger.warning("Socket timeout while receiving response from Unreal.")
            return b''
        except Exception as e:
            logger.error(f"Error receiving data: {e}", exc_info=True)
            return b''

    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a command to Unreal Engine and get the response."""
        # A new connection is established for each command.
        if not self.connect():
            return {"status": "error", "error": "Failed to connect to Unreal Engine for command"}
        
        if not self.socket:
            return {"status": "error", "error": "Socket not initialized."}

        try:
            command_obj = {
                "command": command,
                "params": params or {}
            }
            
            command_json = json.dumps(command_obj)
            logger.info(f"Sending command to Unreal: {command_json}")

            # Encode the message and prefix it with its length
            message = command_json.encode('utf-8')
            msglen = len(message)
            self.socket.sendall(msglen.to_bytes(4, 'little') + message)
            
            response_data = self.receive_full_response()
            if not response_data:
                raise ValueError("Received empty response from Unreal.")

            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Complete response from Unreal: {json.dumps(response, indent=2)}")
            
            # Standardize error checking
            if response.get("status") == "error" or response.get("success") is False:
                error_message = response.get("error") or response.get("message", "Unknown Unreal error")
                logger.error(f"Unreal API Error: {error_message}")
                return {"status": "error", "error": error_message}
            
            return response
            
        except Exception as e:
            logger.error(f"An error occurred while sending command '{command}': {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
        finally:
            # Unreal closes the connection after each command, so we do the same.
            self.disconnect()

# Global connection state is no longer needed, commands will create their own connection.
_unreal_connection: Optional[UnrealConnection] = None

def get_unreal_connection() -> UnrealConnection:
    """Get a fresh connection to Unreal Engine."""
    # This function now simply returns a new connection instance for each call.
    return UnrealConnection()

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Handle server startup and shutdown."""
    logger.info("UnrealMCP server starting up.")
    # No need to manage a global connection here anymore.
    # We can do a one-time check to see if Unreal is available.
    conn = UnrealConnection()
    if conn.connect():
        logger.info("Successfully connected to Unreal Engine on startup. Connection test passed.")
        conn.disconnect()
    else:
        logger.warning("Could not connect to Unreal Engine on startup. Please ensure the editor is running.")
    
    try:
        yield {}
    finally:
        logger.info("Unreal MCP server is shutting down.")

# Initialize server
mcp = FastMCP(
    "UnrealMCP",
    description="Unreal Engine integration via Model Context Protocol",
    lifespan=server_lifespan
)

# Import and register tools
from tools.editor_tools import register_editor_tools
from tools.blueprint_tools import register_blueprint_tools
from tools.node_tools import register_blueprint_node_tools
from tools.project_tools import register_project_tools
from tools.umg_tools import register_umg_tools

# Register tools
register_editor_tools(mcp)
register_blueprint_tools(mcp)
register_blueprint_node_tools(mcp)
register_project_tools(mcp)
register_umg_tools(mcp)  

@mcp.prompt()
def info():
    """Information about available Unreal MCP tools and best practices."""
    return """
    # Unreal MCP Server Tools and Best Practices
    
    ## UMG (Widget Blueprint) Tools
    - `create_umg_widget_blueprint(widget_name, parent_class="UserWidget", path="/Game/UI")` 
      Create a new UMG Widget Blueprint
    - `add_text_block_to_widget(widget_name, text_block_name, text="", position=[0,0], size=[200,50], font_size=12, color=[1,1,1,1])`
      Add a Text Block widget with customizable properties
    - `add_button_to_widget(widget_name, button_name, text="", position=[0,0], size=[200,50], font_size=12, color=[1,1,1,1], background_color=[0.1,0.1,0.1,1])`
      Add a Button widget with text and styling
    - `bind_widget_event(widget_name, widget_component_name, event_name, function_name="")`
      Bind events like OnClicked to functions
    - `add_widget_to_viewport(widget_name, z_order=0)`
      Add widget instance to game viewport
    - `set_text_block_binding(widget_name, text_block_name, binding_property, binding_type="Text")`
      Set up dynamic property binding for text blocks

    ## Editor Tools
    ### Viewport and Screenshots
    - `focus_viewport(target, location, distance, orientation)` - Focus viewport
    - `take_screenshot(filename, show_ui, resolution)` - Capture screenshots

    ### Actor Management
    - `get_actors_in_level()` - List all actors in current level
    - `find_actors_by_name(pattern)` - Find actors by name pattern
    - `spawn_actor(name, type, location=[0,0,0], rotation=[0,0,0], scale=[1,1,1])` - Create actors
    - `delete_actor(name)` - Remove actors
    - `set_actor_transform(name, location, rotation, scale)` - Modify actor transform
    - `get_actor_properties(name)` - Get actor properties
    
    ## Blueprint Management
    - `create_blueprint(name, parent_class)` - Create new Blueprint classes
    - `add_component_to_blueprint(blueprint_name, component_type, component_name)` - Add components
    - `set_static_mesh_properties(blueprint_name, component_name, static_mesh)` - Configure meshes
    - `set_physics_properties(blueprint_name, component_name)` - Configure physics
    - `compile_blueprint(blueprint_name)` - Compile Blueprint changes
    - `set_blueprint_property(blueprint_name, property_name, property_value)` - Set properties
    - `set_pawn_properties(blueprint_name)` - Configure Pawn settings
    - `spawn_blueprint_actor(blueprint_name, actor_name)` - Spawn Blueprint actors
    
    ## Blueprint Node Management
    - `add_blueprint_event_node(blueprint_name, event_type)` - Add event nodes
    - `add_blueprint_input_action_node(blueprint_name, action_name)` - Add input nodes
    - `add_blueprint_function_node(blueprint_name, target, function_name)` - Add function nodes
    - `connect_blueprint_nodes(blueprint_name, source_node_id, source_pin, target_node_id, target_pin)` - Connect nodes
    - `add_blueprint_variable(blueprint_name, variable_name, variable_type)` - Add variables
    - `add_blueprint_get_self_component_reference(blueprint_name, component_name)` - Add component refs
    - `add_blueprint_self_reference(blueprint_name)` - Add self references
    - `find_blueprint_nodes(blueprint_name, node_type, event_type)` - Find nodes
    
    ## Project Tools
    - `create_input_mapping(action_name, key, input_type)` - Create input mappings
    
    ## Best Practices
    
    ### UMG Widget Development
    - Create widgets with descriptive names that reflect their purpose
    - Use consistent naming conventions for widget components
    - Organize widget hierarchy logically
    - Set appropriate anchors and alignment for responsive layouts
    - Use property bindings for dynamic updates instead of direct setting
    - Handle widget events appropriately with meaningful function names
    - Clean up widgets when no longer needed
    - Test widget layouts at different resolutions
    
    ### Editor and Actor Management
    - Use unique names for actors to avoid conflicts
    - Clean up temporary actors
    - Validate transforms before applying
    - Check actor existence before modifications
    - Take regular viewport screenshots during development
    - Keep the viewport focused on relevant actors during operations
    
    ### Blueprint Development
    - Compile Blueprints after changes
    - Use meaningful names for variables and functions
    - Organize nodes logically
    - Test functionality in isolation
    - Consider performance implications
    - Document complex setups
    
    ### Error Handling
    - Check command responses for success
    - Handle errors gracefully
    - Log important operations
    - Validate parameters
    - Clean up resources on errors
    """

# Run the server
if __name__ == "__main__":
    logger.info("Starting MCP server with stdio transport")
    mcp.run(transport='stdio') 