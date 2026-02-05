#!/usr/bin/env python3
"""
Football Game Client

Connects to a game server and controls an agent.

Usage:
    python client.py localhost --agent striker
    python client.py 192.168.1.50 --agent goalie
    python client.py localhost --keyboard
"""

import argparse
import asyncio
import sys
from typing import Optional

import websockets

from agents.base import Action
from agents.random_agent import (
    RandomAgent, ChaserAgent, GoalieAgent,
    StrikerAgent, DefenderAgent, InterceptorAgent,
    MidfielderAgent, AggressorAgent, WingerAgent,
)
from game.config import GameConfig
from game.state import GameState
from network.protocol import (
    MessageType,
    decode_message,
    decode_config,
    decode_state,
    encode_action,
)


# Agent type mapping
AGENT_CLASSES = {
    "random": RandomAgent,
    "chaser": ChaserAgent,
    "goalie": GoalieAgent,
    "striker": StrikerAgent,
    "defender": DefenderAgent,
    "interceptor": InterceptorAgent,
    "midfielder": MidfielderAgent,
    "aggressor": AggressorAgent,
    "winger": WingerAgent,
}


class KeyboardClient:
    """Handles keyboard input for manual control."""

    def __init__(self):
        self.keys_pressed = set()
        self._running = True

    def get_action(self) -> Action:
        """Get action based on current key state."""
        ax, ay = 0.0, 0.0
        kick = False

        # WASD movement
        if 'w' in self.keys_pressed:
            ay = -1.0
        if 's' in self.keys_pressed:
            ay = 1.0
        if 'a' in self.keys_pressed:
            ax = -1.0
        if 'd' in self.keys_pressed:
            ax = 1.0

        # Space to kick
        if ' ' in self.keys_pressed:
            kick = True

        return Action(ax * 0.5, ay * 0.5, kick)


class GameClient:
    """Client that connects to a football game server."""

    def __init__(
        self,
        host: str,
        port: int = 8765,
        agent_type: str = "chaser",
        keyboard: bool = False,
    ):
        self.host = host
        self.port = port
        self.agent_type = agent_type
        self.keyboard = keyboard

        self.config: Optional[GameConfig] = None
        self.team_id: Optional[int] = None
        self.player_id: Optional[int] = None
        self.agent = None
        self.keyboard_client: Optional[KeyboardClient] = None

        if keyboard:
            self.keyboard_client = KeyboardClient()

    def create_agent(self, team_id: int, player_id: int):
        """Create the local agent."""
        if self.keyboard:
            return None  # Keyboard control, no AI agent

        agent_class = AGENT_CLASSES.get(self.agent_type, ChaserAgent)
        return agent_class(team_id, player_id)

    def get_action(self, state: GameState) -> Action:
        """Get action for the current state."""
        if self.keyboard_client:
            return self.keyboard_client.get_action()
        elif self.agent:
            return self.agent.get_action(state)
        else:
            return Action(0.0, 0.0, False)

    async def run(self) -> None:
        """Connect to server and run the game loop."""
        uri = f"ws://{self.host}:{self.port}"
        print(f"Connecting to {uri}...")

        try:
            async with websockets.connect(uri) as websocket:
                print("Connected!")

                async for message in websocket:
                    try:
                        msg_type, data = decode_message(message)

                        if msg_type == MessageType.CONFIG:
                            self.config = decode_config(data)
                            print(f"Received config: {self.config.players_per_team}v{self.config.players_per_team}")

                        elif msg_type == MessageType.ASSIGN:
                            self.team_id = data['team_id']
                            self.player_id = data['player_id']
                            print(f"Assigned to Team {self.team_id}, Player {self.player_id}")

                            # Create agent now that we know our assignment
                            self.agent = self.create_agent(self.team_id, self.player_id)
                            if self.keyboard:
                                print("Keyboard control active: WASD=move, Space=kick")
                            else:
                                print(f"Using agent: {self.agent_type}")

                        elif msg_type == MessageType.STATE:
                            # Game state update - compute and send action
                            state = decode_state(data)
                            action = self.get_action(state)
                            await websocket.send(encode_action(action))

                            # Print score occasionally
                            if state.tick % 60 == 0:
                                print(f"Tick {state.tick}: Score {state.score[0]} - {state.score[1]}", end='\r')

                        elif msg_type == MessageType.GAME_OVER:
                            score = data['score']
                            winner = data['winner']
                            print(f"\nGame Over! Final Score: {score[0]} - {score[1]}")
                            if winner is not None:
                                if winner == self.team_id:
                                    print("Your team wins!")
                                else:
                                    print("Your team loses!")
                            else:
                                print("Draw!")
                            break

                        elif msg_type == MessageType.ERROR:
                            print(f"Error from server: {data['message']}")
                            break

                    except Exception as e:
                        print(f"Error processing message: {e}")

        except ConnectionRefusedError:
            print(f"Could not connect to {uri}. Is the server running?")
            sys.exit(1)
        except websockets.exceptions.ConnectionClosed as e:
            print(f"\nConnection closed: {e}")


async def run_with_keyboard(client: GameClient) -> None:
    """Run client with keyboard input handling."""
    try:
        import sys
        import tty
        import termios
        import select

        # Save terminal settings
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            # Set terminal to raw mode for character-by-character input
            tty.setcbreak(sys.stdin.fileno())

            async def keyboard_input():
                """Handle keyboard input in a separate task."""
                while True:
                    # Check if input is available
                    if select.select([sys.stdin], [], [], 0.01)[0]:
                        char = sys.stdin.read(1).lower()
                        if char in ('w', 'a', 's', 'd', ' '):
                            client.keyboard_client.keys_pressed.add(char)
                        elif char == 'q':
                            # Quit
                            break
                    else:
                        # Clear keys when not pressed (simple approach)
                        await asyncio.sleep(0.05)
                        client.keyboard_client.keys_pressed.clear()

            # Run both tasks
            keyboard_task = asyncio.create_task(keyboard_input())
            client_task = asyncio.create_task(client.run())

            # Wait for either to complete
            done, pending = await asyncio.wait(
                [keyboard_task, client_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    except ImportError:
        # Windows or no termios - fall back to simple mode
        print("Note: Keyboard mode works best on Unix systems.")
        print("Running without real-time keyboard input.")
        await client.run()


def main():
    parser = argparse.ArgumentParser(
        description="Football Game Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python client.py localhost --agent striker    # Connect with striker agent
  python client.py 192.168.1.50 --agent goalie  # Connect to remote server
  python client.py localhost --keyboard          # Manual keyboard control

Available agents: random, chaser, goalie, striker, defender, interceptor, midfielder, aggressor, winger
        """,
    )

    parser.add_argument(
        "host",
        help="Server hostname or IP address",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Server port (default: 8765)",
    )
    parser.add_argument(
        "--agent",
        default="chaser",
        choices=list(AGENT_CLASSES.keys()),
        help="Agent type to use (default: chaser)",
    )
    parser.add_argument(
        "--keyboard",
        action="store_true",
        help="Use keyboard control (WASD + Space)",
    )

    args = parser.parse_args()

    client = GameClient(
        host=args.host,
        port=args.port,
        agent_type=args.agent,
        keyboard=args.keyboard,
    )

    try:
        if args.keyboard:
            asyncio.run(run_with_keyboard(client))
        else:
            asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nDisconnected.")


if __name__ == "__main__":
    main()
