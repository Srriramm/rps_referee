# Rock-Paper-Scissors-Plus AI Game Referee

A minimal AI game referee built with Python and Google ADK that enforces rules, tracks state, and manages a 3-round Rock-Paper-Scissors-Plus game.

## Overview

This chatbot acts as a referee for Rock-Paper-Scissors-Plus, a variant where players have a special "bomb" move that beats everything but can only be used once per game. The game runs exactly 3 rounds in a simple CLI interface.

## Architecture

### State Model

The game state is managed through a **GameState dataclass** (`state.py`) that persists across turns:

```python
@dataclass
class GameState:
    round: int = 1                    # Current round (1-3)
    user_score: int = 0               # User wins
    bot_score: int = 0                # Bot wins
    draws: int = 0                    # Draw count
    user_bomb_used: bool = False      # Tracks if user used bomb
    bot_bomb_used: bool = False       # Tracks if bot used bomb
    history: List[RoundHistory] = []  # Complete round history
    game_over: bool = False           # Set to True after round 3
```

**Why this design?**
- State lives in a Python object, **not in the conversation context**
- Prevents hallucination - LLM can't "forget" the score
- Immutable history provides audit trail
- Single source of truth for game state

### Agent/Tool Design

The architecture cleanly separates three concerns:

**1. Intent Understanding** (Agent in `main.py`)
- Gemini agent interprets user input ("rock", "ROCK", "r", etc.)
- Decides which tools to call based on conversation flow
- Never makes game logic decisions

**2. Game Logic** (Tools in `tools.py`)

Three explicit tools handle all deterministic logic:

| Tool | Purpose | Why? |
|------|---------|------|
| `validate_move` | Check if input is valid and bomb is available | Prevents invalid state transitions |
| `resolve_round` | Apply game rules and determine winner | **Contains ALL winner logic** - LLM never decides |
| `update_game_state` | Mutate state (scores, history, round counter) | Single responsibility for state changes |

**Critical design principle**: The LLM agent **never determines winners**. All game logic is in deterministic Python functions. The agent only:
- Calls tools in the right order
- Generates natural language responses
- Handles conversation flow

**3. Response Generation** (Agent in `main.py`)
- Agent receives tool results as structured data
- Generates clear, concise natural language feedback
- Announces round results and final winner

### Tool Flow

```
User Input → validate_move → resolve_round → update_game_state → Agent Response
             (Is it valid?)   (Who won?)     (Update state)      (Tell user)
```

### Tradeoffs Made

**1. "Best of 3 rounds" interpretation**
- **Chosen**: Exactly 3 rounds are played, all outcomes (win/loss/draw) count as rounds
- **Alternative**: First to 2 wins (traditional), where draws don't count
- **Rationale**: Task says "After 3 rounds, the game must end automatically" - this implies a hard limit of 3 rounds

**2. Random bot moves**
- **Chosen**: Bot selects moves randomly
- **Alternative**: Strategic AI that learns from user patterns
- **Rationale**: Keeps logic simple and testable; focus is on referee architecture, not bot intelligence

**3. Invalid input handling**
- **Chosen**: Invalid input wastes the round (per spec)
- **Alternative**: Allow retry without penalty
- **Rationale**: Task explicitly states "Invalid input wastes the round"

**4. Manual tool calling**
- **Chosen**: Explicit tool call handling in conversation loop
- **Alternative**: Automatic tool calling mode
- **Rationale**: Better control over execution flow and debugging

### What Would I Improve with More Time

**Architecture improvements:**
- Make GameState immutable (use `replace()` method instead of mutation)
- Add comprehensive unit tests for each tool
- Implement proper logging instead of print statements
- Add type validation for tool inputs/outputs

**Feature improvements:**
- Strategic bot AI that adapts to user patterns
- Support for configurable round counts (best of 5, 7, etc.)
- Save/load game state for interrupted sessions
- Move history analysis and statistics

**User experience improvements:**
- Better error messages explaining why moves are invalid
- Hint system suggesting valid moves
- Colorized terminal output (if allowed)
- Game replay functionality

## Installation & Usage

```bash
# Install dependencies
pip install google-genai python-dotenv

# Set up API key in .env file
echo "GOOGLE_API_KEY=your_key_here" > .env

# Run the game
python main.py
```

Get your API key from: https://aistudio.google.com/apikey

## Example Game Session

```
============================================================
ROCK-PAPER-SCISSORS-PLUS GAME REFEREE
============================================================

Referee: Okay, let's play Rock-Paper-Scissors-Plus!
         Here's how it works: We'll play 3 rounds. You can pick rock, 
         paper, scissors, or bomb. Bomb beats everything but can only 
         be used once. Highest score after 3 rounds wins. Good luck!

Your move: bomb
Referee: Round 1: You played bomb, I played scissors. You win!
         Current score: User 1, Bot 0.

Your move: rock
Referee: Round 2: You played rock, I played rock. It's a draw!
         Current score: User 1, Bot 0.

Your move: paper
Referee: Round 3: You played paper, I played scissors. I win!
         Current score: User 1, Bot 1.

=== GAME OVER ===
Final Score: You 1 - 1 Bot (Draws: 1)
🤝 IT'S A DRAW! 🤝
```

## Technical Implementation

- **SDK**: Google ADK (`google-genai`)
- **Model**: `gemini-2.0-flash-exp`
- **State Management**: Python dataclasses
- **Tool Calling**: Manual mode with explicit function execution
- **Error Handling**: Graceful handling of invalid inputs (no crashes)

## Project Structure

```
rps_referee/
├── main.py          # ADK agent setup and game loop
├── tools.py         # Game logic tools (validate, resolve, update)
├── state.py         # GameState and RoundHistory dataclasses
├── .env             # API key (not committed)
├── requirements.txt # Dependencies
└── README.md        # This file
```

## Key Design Decisions

✅ **Deterministic tools** - All game logic is testable and predictable  
✅ **Stateful Python objects** - State persists reliably across turns  
✅ **Agent-tool separation** - Clear boundaries prevent logic leakage  
✅ **No external dependencies** - Only ADK, no databases or APIs  
✅ **Automatic termination** - Game enforces 3-round limit programmatically