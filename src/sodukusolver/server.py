import asyncio

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
from .solver import parse_sudoku_text, solveSudoku, format_sudoku_grid

# Store notes as a simple key-value dict to demonstrate state management
notes: dict[str, str] = {}

# Store Sudoku puzzles
sudoku_puzzles: dict[str, list] = {}

server = Server("sodukusolver")

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available note resources.
    Each note is exposed as a resource with a custom note:// URI scheme.
    """
    resources = [
        types.Resource(
            uri=AnyUrl(f"note://internal/{name}"),
            name=f"Note: {name}",
            description=f"A simple note named {name}",
            mimeType="text/plain",
        )
        for name in notes
    ]
    
    # Add Sudoku puzzle resources
    resources.extend([
        types.Resource(
            uri=AnyUrl(f"sudoku://puzzle/{name}"),
            name=f"Sudoku Puzzle: {name}",
            description=f"A Sudoku puzzle named {name}",
            mimeType="text/plain",
        )
        for name in sudoku_puzzles
    ])
    
    return resources

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read a specific note's content by its URI.
    The note name is extracted from the URI host component.
    """
    if uri.scheme == "note":
        name = uri.path
        if name is not None:
            name = name.lstrip("/")
            return notes[name]
        raise ValueError(f"Note not found: {name}")
    elif uri.scheme == "sudoku":
        name = uri.path
        if name is not None:
            name = name.lstrip("/")
            if name in sudoku_puzzles:
                # Return formatted Sudoku grid
                return format_sudoku_grid(sudoku_puzzles[name])
            raise ValueError(f"Sudoku puzzle not found: {name}")
    else:
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    Each prompt can have optional arguments to customize its behavior.
    """
    return [
        types.Prompt(
            name="summarize-notes",
            description="Creates a summary of all notes",
            arguments=[
                types.PromptArgument(
                    name="style",
                    description="Style of the summary (brief/detailed)",
                    required=False,
                )
            ],
        )
    ]

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """
    Generate a prompt by combining arguments with server state.
    The prompt includes all current notes and can be customized via arguments.
    """
    if name != "summarize-notes":
        raise ValueError(f"Unknown prompt: {name}")

    style = (arguments or {}).get("style", "brief")
    detail_prompt = " Give extensive details." if style == "detailed" else ""

    return types.GetPromptResult(
        description="Summarize the current notes",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"Here are the current notes to summarize:{detail_prompt}\n\n"
                    + "\n".join(
                        f"- {name}: {content}"
                        for name, content in notes.items()
                    ),
                ),
            )
        ],
    )

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="add-note",
            description="Add a new note",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["name", "content"],
            },
        ),
        types.Tool(
            name="add-sudoku",
            description="Add a new Sudoku puzzle",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "puzzle": {"type": "string", "description": "The Sudoku puzzle in text format"},
                },
                "required": ["name", "puzzle"],
            },
        ),
        types.Tool(
            name="solve-sudoku",
            description="Solve a Sudoku puzzle",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the puzzle to solve"},
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="solve-sudoku-text",
            description="Solve a Sudoku puzzle from text input",
            inputSchema={
                "type": "object",
                "properties": {
                    "puzzle": {"type": "string", "description": "The Sudoku puzzle in text format"},
                },
                "required": ["puzzle"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    if not arguments:
        raise ValueError("Missing arguments")

    if name == "add-note":
        note_name = arguments.get("name")
        content = arguments.get("content")

        if not note_name or not content:
            raise ValueError("Missing name or content")

        # Update server state
        notes[note_name] = content

        # Notify clients that resources have changed
        await server.request_context.session.send_resource_list_changed()

        return [
            types.TextContent(
                type="text",
                text=f"Added note '{note_name}' with content: {content}",
            )
        ]
        
    elif name == "add-sudoku":
        puzzle_name = arguments.get("name")
        puzzle_text = arguments.get("puzzle")

        if not puzzle_name or not puzzle_text:
            raise ValueError("Missing name or puzzle")

        try:
            # Parse the puzzle
            grid = parse_sudoku_text(puzzle_text)
            
            # Store the puzzle
            sudoku_puzzles[puzzle_name] = grid
            
            # Notify clients that resources have changed
            await server.request_context.session.send_resource_list_changed()
            
            # Return formatted grid
            formatted_grid = format_sudoku_grid(grid)
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Added Sudoku puzzle '{puzzle_name}':\n\n{formatted_grid}",
                )
            ]
        except ValueError as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error parsing Sudoku puzzle: {str(e)}",
                )
            ]
            
    elif name == "solve-sudoku":
        puzzle_name = arguments.get("name")
        
        if not puzzle_name:
            raise ValueError("Missing puzzle name")
            
        if puzzle_name not in sudoku_puzzles:
            return [
                types.TextContent(
                    type="text",
                    text=f"Sudoku puzzle '{puzzle_name}' not found",
                )
            ]
            
        # Make a copy of the grid to solve
        grid = [row[:] for row in sudoku_puzzles[puzzle_name]]
        
        # Solve the puzzle
        if solveSudoku(grid):
            # Store the solved puzzle with a new name
            solved_name = f"{puzzle_name}_solved"
            sudoku_puzzles[solved_name] = grid
            
            # Notify clients that resources have changed
            await server.request_context.session.send_resource_list_changed()
            
            # Return formatted solution
            formatted_grid = format_sudoku_grid(grid)
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Solved Sudoku puzzle '{puzzle_name}':\n\n{formatted_grid}",
                )
            ]
        else:
            return [
                types.TextContent(
                    type="text",
                    text=f"No solution found for Sudoku puzzle '{puzzle_name}'",
                )
            ]
            
    elif name == "solve-sudoku-text":
        puzzle_text = arguments.get("puzzle")
        
        if not puzzle_text:
            raise ValueError("Missing puzzle")
            
        try:
            # Parse the puzzle
            grid = parse_sudoku_text(puzzle_text)
            
            # Make a copy of the grid to solve
            original_grid = [row[:] for row in grid]
            
            # Solve the puzzle
            if solveSudoku(grid):
                # Store both the original and solved puzzles
                timestamp = asyncio.get_event_loop().time()
                puzzle_name = f"puzzle_{int(timestamp)}"
                sudoku_puzzles[puzzle_name] = original_grid
                sudoku_puzzles[f"{puzzle_name}_solved"] = grid
                
                # Notify clients that resources have changed
                await server.request_context.session.send_resource_list_changed()
                
                # Return formatted solution
                original_formatted = format_sudoku_grid(original_grid)
                solution_formatted = format_sudoku_grid(grid)
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"Original Sudoku puzzle:\n\n{original_formatted}\n\nSolution:\n\n{solution_formatted}",
                    )
                ]
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No solution found for the given Sudoku puzzle",
                    )
                ]
        except ValueError as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error parsing Sudoku puzzle: {str(e)}",
                )
            ]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sodukusolver",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )