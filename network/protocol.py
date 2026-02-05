"""Network protocol for football game multiplayer."""

import json
from enum import Enum
from typing import Any, Dict, Optional

from agents.base import Action
from game.config import GameConfig
from game.state import GameState


class MessageType(Enum):
    """Types of messages exchanged between server and client."""
    CONFIG = "config"        # Server -> Client: game configuration
    STATE = "state"          # Server -> Client: current game state
    ACTION = "action"        # Client -> Server: agent action
    ASSIGN = "assign"        # Server -> Client: player assignment (team_id, player_id)
    GAME_OVER = "game_over"  # Server -> Client: game ended with final score
    ERROR = "error"          # Either direction: error message


def encode_message(msg_type: MessageType, data: Any) -> str:
    """Encode a message as JSON string."""
    return json.dumps({
        'type': msg_type.value,
        'data': data,
    })


def decode_message(msg: str) -> tuple[MessageType, Any]:
    """Decode a JSON message. Returns (message_type, data)."""
    parsed = json.loads(msg)
    return MessageType(parsed['type']), parsed['data']


def encode_config(config: GameConfig) -> str:
    """Encode game config for transmission."""
    return encode_message(MessageType.CONFIG, config.to_dict())


def encode_state(state: GameState) -> str:
    """Encode game state for transmission."""
    return encode_message(MessageType.STATE, state.to_dict())


def encode_action(action: Action) -> str:
    """Encode agent action for transmission."""
    return encode_message(MessageType.ACTION, action.to_dict())


def encode_assign(team_id: int, player_id: int) -> str:
    """Encode player assignment for transmission."""
    return encode_message(MessageType.ASSIGN, {
        'team_id': team_id,
        'player_id': player_id,
    })


def encode_game_over(score: tuple[int, int], winner: Optional[int]) -> str:
    """Encode game over message."""
    return encode_message(MessageType.GAME_OVER, {
        'score': list(score),
        'winner': winner,
    })


def encode_error(message: str) -> str:
    """Encode error message."""
    return encode_message(MessageType.ERROR, {'message': message})


def decode_action(data: dict) -> Action:
    """Decode action from message data."""
    return Action.from_dict(data)


def decode_config(data: dict) -> GameConfig:
    """Decode config from message data."""
    return GameConfig.from_dict(data)


def decode_state(data: dict) -> GameState:
    """Decode game state from message data."""
    return GameState.from_dict(data)
