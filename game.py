"""Crash Bandicoot inspired endless runner built with Pygame."""
from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from typing import List

import pygame

# Screen configuration
WIDTH = 960
HEIGHT = 540
FPS = 60
GROUND_Y = HEIGHT - 90

# Player physics
GRAVITY = 0.55
JUMP_SPEED = -12.5
SPIN_DURATION = 320  # milliseconds
INVINCIBILITY_DURATION = 1500  # milliseconds after taking damage
AKU_AKU_DURATION = 5000

# World behaviour
INITIAL_SCROLL_SPEED = 6.0
MAX_SCROLL_SPEED = 11.5
SPEED_STEP = 0.4
SPEED_STEP_INTERVAL = 20000  # milliseconds
SPAWN_INTERVAL_RANGE = (850, 1550)
COMBO_TIMEOUT = 1300

# Colours
SKY_COLOR = (24, 71, 120)
MOUNTAIN_COLOR = (36, 105, 160)
GROUND_COLORS = ((148, 80, 22), (177, 100, 30))
PLAYER_COLOR = (255, 140, 0)
INVINCIBLE_COLOR = (255, 235, 59)
SPIN_COLOR = (255, 255, 255)
CRATE_COLOR = (210, 120, 30)
AKU_COLOR = (120, 200, 255)
NITRO_COLOR = (88, 255, 100)
TEXT_COLOR = (245, 245, 245)
SHADOW_COLOR = (12, 35, 60)


@dataclass
class Crate:
    """Representation of an obstacle or pickup."""

    rect: pygame.Rect
    kind: str  # "basic", "aku", "hazard"

    def update(self, scroll_speed: float) -> None:
        self.rect.x -= int(scroll_speed)

    def draw(self, surface: pygame.Surface) -> None:
        color = {
            "basic": CRATE_COLOR,
            "aku": AKU_COLOR,
            "hazard": NITRO_COLOR,
        }.get(self.kind, CRATE_COLOR)

        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        inner = self.rect.inflate(-self.rect.width * 0.15, -self.rect.height * 0.15)
        pygame.draw.rect(surface, SHADOW_COLOR, inner, width=2, border_radius=6)

        if self.kind == "hazard":
            # Draw warning stripes
            stripe_height = 10
            for offset in range(0, self.rect.height, stripe_height):
                if (offset // stripe_height) % 2 == 0:
                    segment = pygame.Rect(
                        self.rect.x, self.rect.y + offset, self.rect.width, stripe_height
                    )
                    pygame.draw.rect(surface, (40, 160, 70), segment, border_radius=4)


class Player:
    """Crash-inspired hero with jump and spin abilities."""

    def __init__(self) -> None:
        self.rect = pygame.Rect(160, GROUND_Y - 72, 54, 72)
        self.prev_rect = self.rect.copy()
        self.velocity_y = 0.0
        self.on_ground = True
        self.spinning = False
        self.spin_end_time = 0
        self.invincible = False
        self.invincible_end_time = 0
        self.hit_flash_time = 0
        self.lives = 3

    def update(self) -> None:
        self.prev_rect = self.rect.copy()
        self.velocity_y += GRAVITY
        self.rect.y += int(self.velocity_y)

        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.velocity_y = 0
            self.on_ground = True
        else:
            self.on_ground = False

        now = pygame.time.get_ticks()
        if self.spinning and now >= self.spin_end_time:
            self.spinning = False

        if self.invincible and now >= self.invincible_end_time:
            self.invincible = False

    def jump(self) -> None:
        if self.on_ground:
            self.velocity_y = JUMP_SPEED
            self.on_ground = False

    def start_spin(self) -> None:
        now = pygame.time.get_ticks()
        self.spinning = True
        self.spin_end_time = now + SPIN_DURATION

    def grant_invincibility(self, duration: int) -> None:
        now = pygame.time.get_ticks()
        self.invincible = True
        self.invincible_end_time = now + duration

    def take_damage(self) -> bool:
        if self.invincible:
            return False

        self.lives -= 1
        self.invincible = True
        now = pygame.time.get_ticks()
        self.invincible_end_time = now + INVINCIBILITY_DURATION
        self.hit_flash_time = now + 400
        self.velocity_y = JUMP_SPEED * 0.6
        return True

    def draw(self, surface: pygame.Surface) -> None:
        now = pygame.time.get_ticks()
        color = PLAYER_COLOR

        if self.invincible:
            if (now // 120) % 2 == 0:
                color = INVINCIBLE_COLOR
        elif now < self.hit_flash_time and (now // 80) % 2 == 0:
            color = (255, 255, 255)

        pygame.draw.rect(surface, color, self.rect, border_radius=8)

        # Mask/jeans like details
        belt_rect = pygame.Rect(self.rect.x, self.rect.bottom - 18, self.rect.width, 12)
        pygame.draw.rect(surface, (70, 45, 19), belt_rect, border_radius=8)

        if self.spinning:
            radius = int(self.rect.width * 0.75)
            pygame.draw.circle(surface, SPIN_COLOR, self.rect.center, radius, width=3)


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Temple Dash - Crash Tribute")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("futura", 26)
        self.big_font = pygame.font.SysFont("futura", 54)

        self.player = Player()
        self.crates: List[Crate] = []
        self.scroll_speed = INITIAL_SCROLL_SPEED
        self.spawn_timer = 0
        self.spawn_interval = random.randint(*SPAWN_INTERVAL_RANGE)
        self.elapsed_since_speedup = 0
        self.score = 0
        self.high_score = 0
        self.combo = 0
        self.combo_timeout = 0
        self.game_over = False
        self.running = True
        self.background_offset = 0.0
        self.total_runtime = 0

    def reset(self) -> None:
        self.player = Player()
        self.crates.clear()
        self.scroll_speed = INITIAL_SCROLL_SPEED
        self.spawn_timer = 0
        self.spawn_interval = random.randint(*SPAWN_INTERVAL_RANGE)
        self.elapsed_since_speedup = 0
        self.score = 0
        self.combo = 0
        self.combo_timeout = 0
        self.game_over = False
        self.total_runtime = 0

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS)
            self.total_runtime += dt
            self.handle_events()

            if not self.game_over:
                self.update(dt)

            self.draw()
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif not self.game_over:
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        self.player.jump()
                    elif event.key in (pygame.K_LCTRL, pygame.K_RCTRL, pygame.K_x):
                        self.player.start_spin()
                else:
                    # Restart on any key press during game over
                    self.reset()
            elif event.type == pygame.MOUSEBUTTONDOWN and self.game_over:
                self.reset()

    def update(self, dt: int) -> None:
        self.player.update()
        self.update_speed(dt)
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer -= self.spawn_interval
            self.spawn_interval = random.randint(*SPAWN_INTERVAL_RANGE)
            self.create_crate_group()

        self.update_crates()
        self.background_offset = (self.background_offset + self.scroll_speed) % 120

        if self.combo > 0 and pygame.time.get_ticks() > self.combo_timeout:
            self.combo = 0

    def update_speed(self, dt: int) -> None:
        self.elapsed_since_speedup += dt
        if self.elapsed_since_speedup >= SPEED_STEP_INTERVAL:
            self.elapsed_since_speedup -= SPEED_STEP_INTERVAL
            self.scroll_speed = min(self.scroll_speed + SPEED_STEP, MAX_SCROLL_SPEED)

    def create_crate_group(self) -> None:
        start_x = WIDTH + 40
        pattern = random.random()
        if pattern < 0.55:
            count = random.randint(1, 3)
            for i in range(count):
                rect = pygame.Rect(
                    start_x + i * 70,
                    GROUND_Y - 64,
                    60,
                    60,
                )
                self.crates.append(Crate(rect, "basic"))
        elif pattern < 0.75:
            rect = pygame.Rect(start_x, GROUND_Y - 64, 60, 60)
            self.crates.append(Crate(rect, "aku"))
        else:
            rect = pygame.Rect(start_x, GROUND_Y - 64, 60, 60)
            self.crates.append(Crate(rect, "hazard"))
            if random.random() < 0.4:
                offset_rect = pygame.Rect(start_x + 70, GROUND_Y - 64, 60, 60)
                self.crates.append(Crate(offset_rect, "basic"))

    def update_crates(self) -> None:
        now = pygame.time.get_ticks()
        for crate in list(self.crates):
            crate.update(self.scroll_speed)
            if crate.rect.right < -100:
                self.crates.remove(crate)
                continue

            if self.player.rect.colliderect(crate.rect):
                if crate.kind == "hazard":
                    if self.player.spinning or self.player.invincible:
                        self.add_combo(35)
                        self.crates.remove(crate)
                    else:
                        took_damage = self.player.take_damage()
                        if took_damage and self.player.lives <= 0:
                            self.trigger_game_over()
                        self.crates.remove(crate)
                elif crate.kind == "aku":
                    self.player.grant_invincibility(AKU_AKU_DURATION)
                    self.add_combo(60)
                    self.crates.remove(crate)
                else:
                    landed_on_top = self.player.prev_rect.bottom <= crate.rect.top + 4
                    if self.player.spinning or landed_on_top:
                        self.add_combo(20)
                        self.crates.remove(crate)
                    else:
                        # Block the player from moving through the crate when not spinning.
                        self.player.rect.right = crate.rect.left

    def trigger_game_over(self) -> None:
        self.game_over = True
        self.high_score = max(self.score, self.high_score)

    def add_combo(self, base_points: int) -> None:
        self.combo += 1
        self.combo_timeout = pygame.time.get_ticks() + COMBO_TIMEOUT
        self.score += base_points * self.combo

    def draw_background(self) -> None:
        self.screen.fill(SKY_COLOR)

        # Parallax mountains
        mountain_height = 200
        for i in range(-1, 4):
            peak_x = i * 280 - int(self.background_offset * 0.3)
            peak = (peak_x + 120, HEIGHT - mountain_height - 60)
            left = (peak_x - 140, HEIGHT - 60)
            right = (peak_x + 380, HEIGHT - 60)
            pygame.draw.polygon(self.screen, MOUNTAIN_COLOR, (left, peak, right))

        # Ground with repeating tiles
        tile_width = 80
        for idx in range(-1, WIDTH // tile_width + 3):
            x_pos = idx * tile_width - int(self.background_offset)
            color = GROUND_COLORS[idx % len(GROUND_COLORS)]
            ground_rect = pygame.Rect(x_pos, GROUND_Y, tile_width, HEIGHT - GROUND_Y)
            pygame.draw.rect(self.screen, color, ground_rect)

            top_rect = pygame.Rect(x_pos, GROUND_Y - 16, tile_width, 16)
            pygame.draw.rect(self.screen, tuple(min(255, c + 30) for c in color), top_rect)

    def draw_ui(self) -> None:
        score_text = self.font.render(f"Score: {self.score}", True, TEXT_COLOR)
        self.screen.blit(score_text, (24, 20))

        high_text = self.font.render(f"Best: {self.high_score}", True, TEXT_COLOR)
        self.screen.blit(high_text, (24, 50))

        lives_text = self.font.render("Lives:", True, TEXT_COLOR)
        self.screen.blit(lives_text, (24, 80))
        for i in range(self.player.lives):
            offset = 24 + i * 24
            pygame.draw.circle(self.screen, PLAYER_COLOR, (110 + offset, 90), 10)

        if self.player.invincible:
            duration = max(0, (self.player.invincible_end_time - pygame.time.get_ticks()) / 1000)
            mask_text = self.font.render(f"Mask: {duration:.1f}s", True, AKU_COLOR)
            self.screen.blit(mask_text, (WIDTH - 180, 20))

        if self.combo > 1:
            combo_text = self.font.render(f"Combo x{self.combo}", True, (255, 240, 120))
            self.screen.blit(combo_text, (WIDTH - 180, 50))

        if self.total_runtime < 6000:
            instruct = self.font.render("Space: Jump  |  Ctrl/X: Spin", True, TEXT_COLOR)
            self.screen.blit(instruct, (WIDTH // 2 - instruct.get_width() // 2, HEIGHT - 60))

        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))

            title = self.big_font.render("Game Over", True, (255, 220, 180))
            self.screen.blit(
                title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 80)
            )

            summary = self.font.render(
                "Нажмите любую клавишу, чтобы сыграть снова", True, TEXT_COLOR
            )
            self.screen.blit(
                summary, (WIDTH // 2 - summary.get_width() // 2, HEIGHT // 2)
            )

    def draw(self) -> None:
        self.draw_background()
        for crate in self.crates:
            crate.draw(self.screen)
        self.player.draw(self.screen)
        self.draw_ui()


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
