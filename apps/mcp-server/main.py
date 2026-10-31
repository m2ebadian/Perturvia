from mcp.server import MCPServer


server = MCPServer("Perturvia Test Server")


@server.tool()
def echo(message: str) -> str:
    """Echoes the message back to the user."""

    return message

@server.tool()
def fail() -> None:
    """Raises an exception to test error handling."""

    raise ValueError("Simulated tool failure")



if __name__ == "__main__":
    server.run()
