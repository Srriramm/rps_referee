"""
Rock-Paper-Scissors-Plus Game Referee using Google ADK.

This is the main entry point that creates an ADK agent and runs the game loop.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from google import genai
from google.genai import types
from state import initialize_game, GameState
from tools import validate_move, resolve_round, update_game_state, get_game_summary


# System prompt for the agent
SYSTEM_PROMPT = """You are a Rock-Paper-Scissors-Plus game referee.

GAME RULES (explain these briefly at start):
- Exactly 3 rounds will be played
- Valid moves: rock, paper, scissors, bomb
- Bomb beats all moves but can only be used once per player
- Bomb vs bomb = draw
- Standard RPS rules otherwise (rock beats scissors, scissors beats paper, paper beats rock)
- Invalid input wastes the round
- After 3 rounds, whoever has more wins is the winner

YOUR RESPONSIBILITIES:
1. Explain rules in ≤5 lines at game start
2. Prompt user for their move each round
3. Call validate_move to check user input
4. If valid, call resolve_round to get bot move and winner
5. Call update_game_state to update scores and history
6. Provide clear feedback after each round:
   - Round number
   - User's move
   - Bot's move
   - Round winner
   - Current score
7. After 3 rounds, announce final result

CRITICAL RULES:
- NEVER decide winners yourself - always use resolve_round tool
- NEVER track state in conversation - state lives in GameState object
- Game ends automatically after exactly 3 rounds
- All rounds count (including draws and invalid inputs)

Be concise, friendly, and clear. Keep responses short."""


def create_agent(api_key: str):
    """
    Create and configure the ADK agent with tools.
    
    Args:
        api_key: Google API key for Gemini
        
    Returns:
        Configured client
    """
    client = genai.Client(api_key=api_key)
    return client


def execute_tool_call(tool_name: str, args: dict, state: GameState) -> dict:
    """
    Execute a tool call and return the result.
    
    Args:
        tool_name: Name of the tool to execute
        args: Tool arguments
        state: Current game state
        
    Returns:
        Tool execution result
    """
    if tool_name == "validate_move":
        return validate_move(args["user_input"], state)
    
    elif tool_name == "resolve_round":
        return resolve_round(args["user_move"], state)
    
    elif tool_name == "update_game_state":
        update_game_state(
            state,
            args["user_move"],
            args["bot_move"],
            args["winner"]
        )
        return {
            "success": True,
            "current_state": state.to_dict()
        }
    
    else:
        return {"error": f"Unknown tool: {tool_name}"}


# Define tools
def get_tools():
    """Define tools using correct SDK types."""
    return [types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="validate_move",
                description="Validate user input and check if the move is legal (valid move type, bomb not already used)",
                parameters={
                    "type": "object",
                    "properties": {
                        "user_input": {
                            "type": "string",
                            "description": "Raw user input to validate"
                        }
                    },
                    "required": ["user_input"]
                }
            ),
            types.FunctionDeclaration(
                name="resolve_round",
                description="Choose bot move and determine round winner using game rules. This tool contains all game logic.",
                parameters={
                    "type": "object",
                    "properties": {
                        "user_move": {
                            "type": "string",
                            "description": "Validated user move (rock/paper/scissors/bomb)"
                        }
                    },
                    "required": ["user_move"]
                }
            ),
            types.FunctionDeclaration(
                name="update_game_state",
                description="Update game state after a round (scores, history, round number). Call this after resolve_round.",
                parameters={
                    "type": "object",
                    "properties": {
                        "user_move": {
                            "type": "string",
                            "description": "User's move"
                        },
                        "bot_move": {
                            "type": "string",
                            "description": "Bot's move"
                        },
                        "winner": {
                            "type": "string",
                            "enum": ["user", "bot", "draw", "invalid"],
                            "description": "Round winner"
                        }
                    },
                    "required": ["user_move", "bot_move", "winner"]
                }
            )
        ]
    )]


def run_game():
    """Main game loop."""
    # Get API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set")
        print("Please add it to your .env file")
        return
    
    # Initialize
    client = create_agent(api_key)
    state = initialize_game()
    tool_definitions = get_tools()
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-09-2025")
    
    print("=" * 60)
    print("ROCK-PAPER-SCISSORS-PLUS GAME REFEREE")
    print("=" * 60)
    
    # Start conversation
    messages = [{"role": "user", "parts": [{"text": "Start a new game and explain the rules briefly."}]}]
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=tool_definitions,
                temperature=0.7
            )
        )
        
        print(f"\nReferee: {response.text}\n")
        messages.append({"role": "model", "parts": [{"text": response.text}]})
        
        # Game loop
        while not state.game_over:
            # Get user input
            user_input = input("Your move: ").strip()
            
            if not user_input:
                continue
            
            # Add user message
            messages.append({"role": "user", "parts": [{"text": user_input}]})
            
            # Send to agent
            response = client.models.generate_content(
                model=model_name,
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=tool_definitions,
                    temperature=0.7
                )
            )
            
            # Handle tool calls
            while True:
                # Check for function calls and text in the response
                function_calls = []
                text_parts = []
                
                if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
                    print(f"DEBUG: Response has no candidates or parts. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")
                    break

                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        function_calls.append(part.function_call)
                    if part.text:
                        text_parts.append(part.text)
                
                # Print any text first
                if text_parts:
                    full_text = " ".join(text_parts)
                    print(f"\nReferee: {full_text}\n")
                    
                # If no function calls, we're done with this turn
                if not function_calls:
                    if text_parts:
                        messages.append({"role": "model", "parts": [{"text": " ".join(text_parts)}]})
                    break
                
                # Record the model's tool calls in history
                model_parts = []
                if text_parts:
                    model_parts.append({"text": " ".join(text_parts)})
                for fc in function_calls:
                    model_parts.append({"function_call": {"name": fc.name, "args": fc.args}})
                messages.append({"role": "model", "parts": model_parts})
                
                # Execute all function calls
                user_response_parts = []
                for fc in function_calls:
                    tool_name = fc.name
                    args = dict(fc.args) if fc.args else {}
                    
                    # Execute tool
                    result = execute_tool_call(tool_name, args, state)
                    
                    # Add to response parts
                    user_response_parts.append({
                        "function_response": {
                            "name": tool_name,
                            "response": result
                        }
                    })
                
                # Add results to history
                messages.append({"role": "user", "parts": user_response_parts})
                
                # Get next response from agent
                response = client.models.generate_content(
                    model=model_name,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=tool_definitions,
                        temperature=0.7
                    )
                )
        
        # Game over
        print("\n" + get_game_summary(state))
        
    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_game()