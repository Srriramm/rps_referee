"""
Game state management for Rock-Paper-Scissors-Plus.
"""

from dataclasses import dataclass, field
from typing import List, Literal


@dataclass
class RoundHistory:
    """History entry for a single round."""
    round: int
    user_move: str
    bot_move: str
    winner: Literal["user", "bot", "draw", "invalid"]


@dataclass
class GameState:
    """
    Maintains the complete state of a Rock-Paper-Scissors-Plus game.
    
    State persists across turns and is managed by tools, not the LLM.
    """
    round: int = 1
    user_score: int = 0
    bot_score: int = 0
    draws: int = 0
    user_bomb_used: bool = False
    bot_bomb_used: bool = False
    history: List[RoundHistory] = field(default_factory=list)
    game_over: bool = False
    
    def to_dict(self) -> dict:
        """Convert state to dictionary for serialization."""
        return {
            "round": self.round,
            "user_score": self.user_score,
            "bot_score": self.bot_score,
            "draws": self.draws,
            "user_bomb_used": self.user_bomb_used,
            "bot_bomb_used": self.bot_bomb_used,
            "history": [
                {
                    "round": h.round,
                    "user_move": h.user_move,
                    "bot_move": h.bot_move,
                    "winner": h.winner
                }
                for h in self.history
            ],
            "game_over": self.game_over
        }


def initialize_game() -> GameState:
    """Initialize a new game state."""
    return GameState()
