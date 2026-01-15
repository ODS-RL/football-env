from typing import Optional

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from game.config import GameConfig
from game.state import GameState
from game_logging.logger import load_game_log
from .renderer import Renderer


class ReplayViewer:
    """Viewer for replaying game logs."""

    def __init__(self, log_path: str, scale: float = 1.0):
        """
        Initialize replay viewer.

        Args:
            log_path: Path to game log file
            scale: Display scale factor
        """
        if not PYGAME_AVAILABLE:
            raise ImportError("pygame is required for replay. Install with: pip install pygame")

        self.log_data = load_game_log(log_path)
        self.config = GameConfig.from_dict(self.log_data['config'])
        self.states = [
            GameState.from_dict(s) for s in self.log_data['states']
        ]
        self.current_frame = 0
        self.playing = False
        self.speed = 1.0

        self.renderer = Renderer(self.config, scale=scale, title="AI Football Replay")

    def run(self) -> None:
        """Run the replay viewer."""
        running = True

        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._handle_key(event.key)

            # Auto-advance if playing
            if self.playing and self.current_frame < len(self.states) - 1:
                self.current_frame += 1

            # Render current frame
            state = self.states[self.current_frame]
            self.renderer.render(state)

            # Draw replay controls
            self._draw_controls()

            pygame.display.flip()
            self.renderer.tick(int(self.config.ticks_per_second * self.speed))

        self.renderer.close()

    def _handle_key(self, key: int) -> bool:
        """Handle keyboard input. Returns False to quit."""
        if key == pygame.K_ESCAPE:
            return False
        elif key == pygame.K_SPACE:
            self.playing = not self.playing
        elif key == pygame.K_RIGHT:
            self.current_frame = min(self.current_frame + 1, len(self.states) - 1)
        elif key == pygame.K_LEFT:
            self.current_frame = max(self.current_frame - 1, 0)
        elif key == pygame.K_UP:
            self.speed = min(self.speed * 1.5, 4.0)
        elif key == pygame.K_DOWN:
            self.speed = max(self.speed / 1.5, 0.25)
        elif key == pygame.K_HOME:
            self.current_frame = 0
        elif key == pygame.K_END:
            self.current_frame = len(self.states) - 1
        return True

    def _draw_controls(self) -> None:
        """Draw replay control info."""
        font = pygame.font.Font(None, 20)
        screen = self.renderer.screen

        # Control info
        controls = [
            "SPACE: Play/Pause",
            "LEFT/RIGHT: Step frame",
            "UP/DOWN: Speed",
            "HOME/END: Start/End",
            "ESC: Quit",
        ]

        y = self.renderer.height - 20 * len(controls) - 10
        for line in controls:
            text = font.render(line, True, (200, 200, 200))
            screen.blit(text, (self.renderer.padding + 10, y))
            y += 20

        # Speed indicator
        speed_text = f"Speed: {self.speed:.2f}x"
        text = font.render(speed_text, True, (200, 200, 200))
        screen.blit(text, (self.renderer.width - 120, self.renderer.height - 30))

        # Frame counter
        frame_text = f"Frame: {self.current_frame + 1}/{len(self.states)}"
        text = font.render(frame_text, True, (200, 200, 200))
        screen.blit(text, (self.renderer.width - 150, 10))

        # Playing indicator
        status = "Playing" if self.playing else "Paused"
        text = font.render(status, True, (200, 200, 200))
        screen.blit(text, (self.renderer.width - 80, 30))


def replay_game(log_path: str, scale: float = 1.0) -> None:
    """Convenience function to replay a game log."""
    viewer = ReplayViewer(log_path, scale=scale)
    viewer.run()
