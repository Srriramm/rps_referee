"""
Game logic tools for Rock-Paper-Scissors-Plus.

All game logic is deterministic and lives in these tools.
The LLM agent calls these tools but does NOT decide winners.
"""

import random
from typing import Dict, Literal
from state import GameState, RoundHistory


VALID_MOVES = {"rock", "paper", "scissors", "bomb"}


def validate_move(user_input: str, state: GameState) -> Dict:
    """
    Validate and normalize user input.
    
    Args:
        user_input: Raw user input string
        state: Current game state
        
    Returns:
        {
            "valid": bool,
            "move": str | None,
            "reason": str | None
        }
    """
    # Normalize input
    normalized = user_input.strip().lower()
    
    # Check if move is valid
    if normalized not in VALID_MOVES:
        return {
            "valid": False,
            "move": None,
            "reason": f"Invalid move. Valid moves are: {', '.join(VALID_MOVES)}"
        }
    
    # Check bomb usage rule
    if normalized == "bomb" and state.user_bomb_used:
        return {
            "valid": False,
            "move": None,
            "reason": "You have already used your bomb this game!"
        }
    
    return {
        "valid": True,
        "move": normalized,
        "reason": None
    }


def resolve_round(user_move: str, state: GameState) -> Dict:
    """
    Resolve a round by choosing bot move and determining winner.
    
    This function contains ALL game logic. The LLM does NOT decide winners.
    
    Args:
        user_move: Validated user move
        state: Current game state
        
    Returns:
        {
            "bot_move": str,
            "winner": "user" | "bot" | "draw"
        }
    """
    # Choose bot move (respect bomb usage)
    available_moves = list(VALID_MOVES)
    if state.bot_bomb_used:
        available_moves.remove("bomb")
    
    bot_move = random.choice(available_moves)
    
    # Determine winner using game rules
    winner = _determine_winner(user_move, bot_move)
    
    return {
        "bot_move": bot_move,
        "winner": winner
    }


def _determine_winner(user_move: str, bot_move: str) -> Literal["user", "bot", "draw"]:
    """
    Apply Rock-Paper-Scissors-Plus rules to determine winner.
    
    Rules:
    - bomb beats all other moves
    - bomb vs bomb → draw
    - Standard RPS rules otherwise
    """
    # Handle bomb cases
    if user_move == "bomb" and bot_move == "bomb":
        return "draw"
    if user_move == "bomb":
        return "user"
    if bot_move == "bomb":
        return "bot"
    
    # Same move → draw
    if user_move == bot_move:
        return "draw"
    
    # Standard RPS rules
    winning_combinations = {
        ("rock", "scissors"),
        ("paper", "rock"),
        ("scissors", "paper")
    }
    
    if (user_move, bot_move) in winning_combinations:
        return "user"
    else:
        return "bot"


def update_game_state(
    state: GameState,
    user_move: str,
    bot_move: str,
    winner: Literal["user", "bot", "draw", "invalid"]
) -> GameState:
    """
    Update game state after a round.
    
    Args:
        state: Current game state
        user_move: User's move
        bot_move: Bot's move
        winner: Round winner
        
    Returns:
        Updated GameState
    """
    # Update bomb usage (only for valid moves)
    if user_move == "bomb":
        state.user_bomb_used = True
    if bot_move == "bomb":
        state.bot_bomb_used = True
    
    # Update scores
    if winner == "user":
        state.user_score += 1
    elif winner == "bot":
        state.bot_score += 1
    elif winner == "draw":
        state.draws += 1
    # Note: invalid inputs don't increment any score
    
    # Add to history
    state.history.append(RoundHistory(
        round=state.round,
        user_move=user_move,
        bot_move=bot_move,
        winner=winner
    ))
    
    # ALWAYS increment round (draws and invalid inputs count as rounds)
    state.round += 1
    
    # Check if game is over (after 3 rounds)
    if state.round > 3:
        state.game_over = True
    
    return state


def get_game_summary(state: GameState) -> str:
    """
    Generate a human-readable game summary.
    
    Args:
        state: Current game state
        
    Returns:
        Formatted summary string
    """
    summary = f"\n=== GAME OVER ===\n"
    summary += f"Final Score: You {state.user_score} - {state.bot_score} Bot (Draws: {state.draws})\n\n"
    
    if state.user_score > state.bot_score:
        summary += "🎉 YOU WIN! 🎉\n"
    elif state.bot_score > state.user_score:
        summary += "🤖 BOT WINS! 🤖\n"
    else:
        summary += "🤝 IT'S A DRAW! 🤝\n"
    
    summary += "\nRound History:\n"
    for h in state.history:
        winner_text = h.winner.upper() if h.winner != "draw" else "DRAW"
        summary += f"  Round {h.round}: You played {h.user_move}, Bot played {h.bot_move} → {winner_text}\n"
    
    return summary