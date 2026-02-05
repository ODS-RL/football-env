#!/usr/bin/env python3
"""
Football Game Server

Hosts a network game that remote clients can connect to.

Usage:
    python server.py --players 2
    python server.py --players 3 --port 8765 --ticks 5000
"""

import argparse
import asyncio
import random
from typing import Any, Dict, List, Optional

import websockets

from game.config import GameConfig
from game.engine import Game
from game.state import GameStatus
from agents.base import Action
from agents.random_agent import ChaserAgent
from network.protocol import (
    MessageType,
    decode_message,
    decode_action,
    encode_config,
    encode_state,
    encode_assign,
    encode_game_over,
    encode_error,
)
from network.network_agent import NetworkAgent


class GameServer:
    """Server that hosts a network football game."""

    def __init__(
        self,
        config: GameConfig,
        host: str = "0.0.0.0",
        port: int = 8765,
        tick_rate: int = 30,
    ):
        self.config = config
        self.host = host
        self.port = port
        self.tick_rate = tick_rate
        self.tick_interval = 1.0 / tick_rate

        # Player slots: (team_id, player_id) -> NetworkAgent or None
        self.total_players = config.players_per_team * 2
        self.player_slots: Dict[tuple[int, int], Optional[NetworkAgent]] = {}
        self.websocket_to_slot: Dict[Any, tuple[int, int]] = {}

        # Initialize all slots as empty
        for team_id in range(2):
            for player_id in range(config.players_per_team):
                self.player_slots[(team_id, player_id)] = None

        self.game: Optional[Game] = None
        self.game_started = False
        self.start_event = asyncio.Event()

    def get_open_slot(self) -> Optional[tuple[int, int]]:
        """Find an open player slot. Returns (team_id, player_id) or None."""
        for slot, agent in self.player_slots.items():
            if agent is None:
                return slot
        return None

    def count_connected(self) -> int:
        """Count connected players."""
        return sum(1 for agent in self.player_slots.values() if agent is not None)

    async def handle_client(self, websocket) -> None:
        """Handle a new client connection."""
        slot = self.get_open_slot()

        if slot is None:
            await websocket.send(encode_error("Server is full"))
            await websocket.close()
            return

        team_id, player_id = slot
        agent = NetworkAgent(team_id, player_id, websocket, self.config.agent_timeout_ms)
        self.player_slots[slot] = agent
        self.websocket_to_slot[websocket] = slot

        print(f"Player connected: Team {team_id}, Player {player_id} ({self.count_connected()}/{self.total_players})")

        try:
            # Send config and assignment
            await websocket.send(encode_config(self.config))
            await websocket.send(encode_assign(team_id, player_id))

            # Check if we should start the game
            if self.count_connected() == self.total_players and not self.game_started:
                self.start_event.set()

            # Handle messages from client
            async for message in websocket:
                try:
                    msg_type, data = decode_message(message)

                    if msg_type == MessageType.ACTION:
                        action = decode_action(data)
                        agent.set_pending_action(action)

                except Exception as e:
                    print(f"Error processing message from {slot}: {e}")

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Clean up disconnected player
            self.player_slots[slot] = None
            del self.websocket_to_slot[websocket]
            print(f"Player disconnected: Team {team_id}, Player {player_id}")

    async def broadcast_state(self) -> None:
        """Send current game state to all connected clients."""
        if not self.game:
            return

        state = self.game.get_state()
        message = encode_state(state)

        # Send to all connected clients
        tasks = []
        for agent in self.player_slots.values():
            if agent is not None and agent.is_connected():
                tasks.append(agent.websocket.send(message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def collect_actions(self, timeout: float = 0.1) -> None:
        """Wait briefly for clients to respond with actions."""
        await asyncio.sleep(timeout)

    async def run_game(self) -> None:
        """Run the game loop."""
        print(f"Starting game with {self.total_players} players!")

        # Build agent lists for the Game engine
        team0_agents: List = []
        team1_agents: List = []

        for player_id in range(self.config.players_per_team):
            agent0 = self.player_slots.get((0, player_id))
            agent1 = self.player_slots.get((1, player_id))

            # Use network agent if connected, otherwise AI fallback
            if agent0 is not None:
                team0_agents.append(agent0)
            else:
                team0_agents.append(ChaserAgent(0, player_id))
                print(f"Using AI for Team 0, Player {player_id}")

            if agent1 is not None:
                team1_agents.append(agent1)
            else:
                team1_agents.append(ChaserAgent(1, player_id))
                print(f"Using AI for Team 1, Player {player_id}")

        # Create game
        self.game = Game(self.config, team0_agents, team1_agents)
        self.game_started = True

        # Game loop
        while self.game.status == GameStatus.RUNNING:
            # Broadcast current state to all clients
            await self.broadcast_state()

            # Wait for actions (with timeout)
            await self.collect_actions(self.tick_interval * 0.8)

            # Step the game
            self.game.step()

            # Maintain tick rate
            await asyncio.sleep(self.tick_interval * 0.2)

        # Game over - send final results
        final_state = self.game.get_state()
        winner = self.game.get_winner()
        score = tuple(self.game.score)

        print(f"\nGame Over! Score: {score[0]} - {score[1]}")
        if winner is not None:
            print(f"Team {winner} wins!")
        else:
            print("Draw!")

        # Send game over to all clients
        message = encode_game_over(score, winner)
        for agent in self.player_slots.values():
            if agent is not None and agent.is_connected():
                try:
                    await agent.websocket.send(message)
                except Exception:
                    pass

    async def start(self) -> None:
        """Start the server and wait for game to complete."""
        print(f"Football Server starting on {self.host}:{self.port}")
        print(f"Waiting for {self.total_players} players to connect...")
        print(f"Players per team: {self.config.players_per_team}")
        print()

        async with websockets.serve(self.handle_client, self.host, self.port):
            # Wait for all players to connect
            await self.start_event.wait()

            # Small delay to ensure all clients are ready
            await asyncio.sleep(0.5)

            # Run the game
            await self.run_game()


def main():
    parser = argparse.ArgumentParser(
        description="Football Game Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python server.py --players 2         # 2v2 game, wait for 4 players
  python server.py --players 1         # 1v1 game, wait for 2 players
  python server.py --port 9000         # Use custom port
  python server.py --tick-rate 60      # Higher tick rate
        """,
    )

    parser.add_argument(
        "--players",
        type=int,
        default=2,
        help="Players per team (default: 2)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Server port (default: 8765)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Server host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--tick-rate",
        type=int,
        default=30,
        help="Game tick rate in Hz (default: 30)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=3000,
        help="Max game ticks (default: 3000)",
    )
    parser.add_argument(
        "--win-score",
        type=int,
        default=5,
        help="Score to win (default: 5)",
    )

    args = parser.parse_args()

    config = GameConfig(
        players_per_team=args.players,
        max_ticks=args.ticks,
        win_score=args.win_score,
        ticks_per_second=args.tick_rate,
    )

    server = GameServer(
        config,
        host=args.host,
        port=args.port,
        tick_rate=args.tick_rate,
    )

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
