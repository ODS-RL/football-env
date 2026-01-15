from typing import TYPE_CHECKING, Optional

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

if TYPE_CHECKING:
    from game.state import GameState
    from game.config import GameConfig


# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (34, 139, 34)
DARK_GREEN = (0, 100, 0)
RED = (220, 50, 50)
BLUE = (50, 100, 220)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)


class Renderer:
    """Pygame-based game renderer."""

    def __init__(
        self,
        config: 'GameConfig',
        scale: float = 1.0,
        title: str = "AI Football",
    ):
        """
        Initialize renderer.

        Args:
            config: Game configuration
            scale: Scale factor for display (1.0 = actual size)
            title: Window title
        """
        if not PYGAME_AVAILABLE:
            raise ImportError("pygame is required for visualization. Install with: pip install pygame")

        self.config = config
        self.scale = scale
        self.title = title

        # Add padding for goals
        self.padding = int(40 * scale)  # Space for goals on each side
        self.field_width = int(config.field_width * scale)
        self.field_height = int(config.field_height * scale)
        self.width = self.field_width + 2 * self.padding
        self.height = self.field_height

        pygame.init()
        pygame.display.set_caption(title)
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)

    def _scale_pos(self, x: float, y: float) -> tuple:
        """Scale position to screen coordinates with padding offset."""
        return (int(x * self.scale) + self.padding, int(y * self.scale))

    def _scale_val(self, val: float) -> int:
        """Scale a single value."""
        return int(val * self.scale)

    def render(self, state: 'GameState') -> bool:
        """
        Render current game state.

        Returns:
            False if window was closed, True otherwise
        """
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False

        # Clear screen with background color (for goal areas)
        self.screen.fill(DARK_GREEN)

        # Draw field area
        pygame.draw.rect(self.screen, GREEN,
                         (self.padding, 0, self.field_width, self.field_height))

        # Draw field markings
        self._draw_field()

        # Draw goals
        self._draw_goals(state)

        # Draw players
        self._draw_players(state)

        # Draw ball
        self._draw_ball(state)

        # Draw score and info
        self._draw_info(state)

        pygame.display.flip()
        return True

    def _draw_field(self) -> None:
        """Draw field markings with rounded corners."""
        import math

        corner_r = self._scale_val(self.config.corner_radius)
        p = self.padding  # Shorthand for padding
        fw = self.field_width
        fh = self.field_height

        # Draw rounded corner borders
        # Top-left corner arc
        pygame.draw.arc(self.screen, WHITE,
                        (p, 0, corner_r * 2, corner_r * 2),
                        math.pi / 2, math.pi, 3)
        # Top-right corner arc
        pygame.draw.arc(self.screen, WHITE,
                        (p + fw - corner_r * 2, 0, corner_r * 2, corner_r * 2),
                        0, math.pi / 2, 3)
        # Bottom-left corner arc
        pygame.draw.arc(self.screen, WHITE,
                        (p, fh - corner_r * 2, corner_r * 2, corner_r * 2),
                        math.pi, math.pi * 3 / 2, 3)
        # Bottom-right corner arc
        pygame.draw.arc(self.screen, WHITE,
                        (p + fw - corner_r * 2, fh - corner_r * 2, corner_r * 2, corner_r * 2),
                        math.pi * 3 / 2, math.pi * 2, 3)

        # Draw straight border lines (between corners)
        # Top line
        pygame.draw.line(self.screen, WHITE, (p + corner_r, 0), (p + fw - corner_r, 0), 3)
        # Bottom line
        pygame.draw.line(self.screen, WHITE, (p + corner_r, fh - 1), (p + fw - corner_r, fh - 1), 3)
        # Left line
        pygame.draw.line(self.screen, WHITE, (p, corner_r), (p, fh - corner_r), 3)
        # Right line
        pygame.draw.line(self.screen, WHITE, (p + fw - 1, corner_r), (p + fw - 1, fh - corner_r), 3)

        # Center line
        center_x = p + fw // 2
        pygame.draw.line(self.screen, WHITE, (center_x, 0), (center_x, fh), 2)

        # Center circle
        center_radius = self._scale_val(80)
        pygame.draw.circle(self.screen, WHITE, (center_x, fh // 2), center_radius, 2)

        # Center dot
        pygame.draw.circle(self.screen, WHITE, (center_x, fh // 2), 5)

        # Goal areas (penalty boxes)
        box_width = self._scale_val(100)
        box_height = self._scale_val(200)
        box_top = (fh - box_height) // 2

        # Left penalty box
        pygame.draw.rect(self.screen, WHITE, (p, box_top, box_width, box_height), 2)

        # Right penalty box
        pygame.draw.rect(self.screen, WHITE,
                         (p + fw - box_width, box_top, box_width, box_height), 2)

    def _draw_goals(self, state: 'GameState') -> None:
        """Draw goals in the padding area."""
        goal_height = self._scale_val(state.goal_height)
        goal_depth = self.padding - 5  # Goal depth (visual)
        goal_top = (self.field_height - goal_height) // 2
        p = self.padding

        # Left goal (team 0 defends) - blue tint
        pygame.draw.rect(self.screen, (30, 60, 120),
                         (0, goal_top, p, goal_height))
        pygame.draw.rect(self.screen, WHITE,
                         (0, goal_top, p, goal_height), 3)

        # Right goal (team 1 defends) - red tint
        pygame.draw.rect(self.screen, (120, 40, 40),
                         (p + self.field_width, goal_top, p, goal_height))
        pygame.draw.rect(self.screen, WHITE,
                         (p + self.field_width, goal_top, p, goal_height), 3)

    def _draw_players(self, state: 'GameState') -> None:
        """Draw all players."""
        player_radius = self._scale_val(self.config.player_radius)

        for player in state.players:
            pos = self._scale_pos(player.x, player.y)
            color = BLUE if player.team_id == 0 else RED

            # Player circle
            pygame.draw.circle(self.screen, color, pos, player_radius)
            pygame.draw.circle(self.screen, WHITE, pos, player_radius, 2)

            # Player number
            text = self.small_font.render(str(player.player_id), True, WHITE)
            text_rect = text.get_rect(center=pos)
            self.screen.blit(text, text_rect)

    def _draw_ball(self, state: 'GameState') -> None:
        """Draw the ball."""
        ball_radius = self._scale_val(self.config.ball_radius)
        pos = self._scale_pos(state.ball.x, state.ball.y)

        pygame.draw.circle(self.screen, YELLOW, pos, ball_radius)
        pygame.draw.circle(self.screen, BLACK, pos, ball_radius, 2)

    def _draw_info(self, state: 'GameState') -> None:
        """Draw score and game info."""
        # Score
        score_text = f"{state.score[0]} - {state.score[1]}"
        text = self.font.render(score_text, True, WHITE)
        text_rect = text.get_rect(center=(self.width // 2, 25))

        # Background for score
        bg_rect = text_rect.inflate(20, 10)
        pygame.draw.rect(self.screen, DARK_GREEN, bg_rect)
        self.screen.blit(text, text_rect)

        # Tick counter
        tick_text = f"Tick: {state.tick}/{self.config.max_ticks}"
        text = self.small_font.render(tick_text, True, WHITE)
        self.screen.blit(text, (self.padding + 10, 10))

        # Status
        if state.status.value == "ended":
            if state.score[0] > state.score[1]:
                result = "Blue Team Wins!"
            elif state.score[1] > state.score[0]:
                result = "Red Team Wins!"
            else:
                result = "Draw!"

            text = self.font.render(result, True, WHITE)
            text_rect = text.get_rect(center=(self.width // 2, self.height // 2))
            bg_rect = text_rect.inflate(40, 20)
            pygame.draw.rect(self.screen, DARK_GREEN, bg_rect)
            self.screen.blit(text, text_rect)

    def tick(self, fps: int = 60) -> None:
        """Control frame rate."""
        self.clock.tick(fps)

    def close(self) -> None:
        """Close the renderer."""
        pygame.quit()
