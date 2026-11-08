"""Run agents with a per-tick deadline.

Each agent gets its own persistent daemon thread. The game hands it a state,
waits until the deadline, and moves on with a default action if the agent has
not answered. A slow agent keeps its thread busy and is skipped on later ticks
until it finishes, so it can never stall the game loop. Daemon threads also mean
a hung agent cannot block interpreter exit.

Limitation: Python threads cannot be killed, so an agent whose get_action never
returns keeps its thread (and itself) alive until the process exits. That is
fine for in-repo agents; untrusted agents need process isolation.
"""

import threading
import time
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from agents.base import Action

if TYPE_CHECKING:
    from agents.base import BaseAgent
    from game.state import GameState


class _AgentWorker:
    def __init__(self, agent: 'BaseAgent'):
        self.agent = agent
        self.key = (agent.team_id, agent.player_id)
        self._cond = threading.Condition()
        self._request: Optional['GameState'] = None
        self._result: Optional[Action] = None
        self._done_at = 0.0
        self._busy = False
        self._reset_pending = False
        self._closed = False
        self._thread = threading.Thread(
            target=self._loop,
            name=f"agent-{agent.team_id}-{agent.player_id}",
            daemon=True,
        )
        self._thread.start()

    def submit(self, state: 'GameState') -> bool:
        """Hand a state to the agent. Returns False if it is still busy."""
        with self._cond:
            if self._busy or self._closed:
                return False
            self._busy = True
            self._request = state
            self._result = None
            self._cond.notify_all()
            return True

    def wait(self, deadline: float) -> Optional[Action]:
        """Wait until `deadline` (time.monotonic) for the submitted state's action.

        Results that completed after the deadline are rejected even if they are
        already stored by the time this worker is polled.
        """
        with self._cond:
            self._cond.wait_for(
                lambda: not self._busy, max(0.0, deadline - time.monotonic())
            )
            if self._busy:
                return None
            result, self._result = self._result, None
            return result if self._done_at <= deadline else None

    def reset(self) -> None:
        """Reset the agent without racing an in-flight get_action call."""
        with self._cond:
            if self._busy:
                # Worker resets the agent once the late call returns.
                self._reset_pending = True
                return
        # Idle: only the game thread submits work, so the worker stays idle.
        self._reset_agent()

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()

    def _reset_agent(self) -> None:
        try:
            self.agent.reset()
        except Exception:
            pass

    def _loop(self) -> None:
        while True:
            with self._cond:
                self._cond.wait_for(lambda: self._request is not None or self._closed)
                if self._closed:
                    return
                state, self._request = self._request, None
            if state is None:
                continue
            try:
                result = self.agent.get_action(state)
                if not isinstance(result, Action):
                    result = None
            except Exception:
                result = None
            # Apply resets requested mid-call before going idle. The check and
            # the busy=False transition share the lock so none can be missed.
            while True:
                with self._cond:
                    if not self._reset_pending:
                        self._result = result
                        self._done_at = time.monotonic()
                        self._busy = False
                        self._cond.notify_all()
                        break
                    self._reset_pending = False
                self._reset_agent()
                result = None  # Computed before the reset; stale.


class AgentRunner:
    """Collects actions from all agents within a shared deadline."""

    def __init__(self, agents: List['BaseAgent']):
        self._workers = [_AgentWorker(agent) for agent in agents]

    def get_actions(
        self, state: 'GameState', timeout_sec: float
    ) -> Dict[Tuple[int, int], Action]:
        deadline = time.monotonic() + timeout_sec
        submitted = [w for w in self._workers if w.submit(state)]

        actions: Dict[Tuple[int, int], Action] = {}
        for worker in submitted:
            action = worker.wait(deadline)
            if action is not None:
                actions[worker.key] = action

        # Timed out, still busy from an earlier tick, raised, or returned junk.
        for worker in self._workers:
            if worker.key not in actions:
                actions[worker.key] = Action(0.0, 0.0)
        return actions

    def reset_agents(self) -> None:
        for worker in self._workers:
            worker.reset()

    def close(self) -> None:
        for worker in self._workers:
            worker.close()
