"""Server-side network agent wrapper."""

import asyncio
from typing import Optional, TYPE_CHECKING

from agents.base import BaseAgent, Action

if TYPE_CHECKING:
    from game.state import GameState
    import websockets


class NetworkAgent(BaseAgent):
    """
    Server-side agent wrapper that communicates with a remote client.

    Implements the BaseAgent interface, sending state to the remote client
    and receiving actions back via WebSocket.
    """

    def __init__(
        self,
        team_id: int,
        player_id: int,
        websocket: 'websockets.WebSocketServerProtocol',
        timeout_ms: float = 100.0,
    ):
        super().__init__(team_id, player_id)
        self.websocket = websocket
        self.timeout_sec = timeout_ms / 1000.0
        self._pending_action: Optional[Action] = None
        self._action_event: Optional[asyncio.Event] = None

    def set_pending_action(self, action: Action) -> None:
        """Set the pending action received from the client."""
        self._pending_action = action
        if self._action_event:
            self._action_event.set()

    def clear_pending_action(self) -> None:
        """Clear the pending action."""
        self._pending_action = None

    def get_action(self, state: 'GameState') -> Action:
        """
        Get action for the current game state.

        This is called synchronously by the game engine. Since network
        communication is async, we return the previously received action
        or a default action if none is available.

        The server should have already sent the state and received the
        action before this is called.
        """
        if self._pending_action is not None:
            action = self._pending_action
            self._pending_action = None
            return action
        # Default action if no response received
        return Action(0.0, 0.0, False)

    def is_connected(self) -> bool:
        """Check if the websocket is still connected."""
        # websockets 12+ uses close_code (None means still open)
        return getattr(self.websocket, 'close_code', None) is None

    def reset(self) -> None:
        """Called when game resets (after goal scored)."""
        self._pending_action = None
