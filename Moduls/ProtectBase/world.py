import math
import random
from typing import List

import pygame

from core import Vector2, BACKGROUND_COLOR

TREE_GREEN = (34, 139, 34)
BROWN = (139, 69, 19)
WHITE = (255, 255, 255)
ROCK_GRAY = (150, 150, 150)


class WorldObject:
    def __init__(self, position: Vector2, size: Vector2, obj_type: str, color):
        self.position = position
        self.size = size
        self.type = obj_type
        self.color = color

    def render(self, screen, camera):
        screen_pos = (
            int(self.position.x - camera.x),
            int(self.position.y - camera.y)
        )

        # Custom rendering for tree and rock
        if self.type == "tree":
            # Draw "archa" in three triangles, smaller than before
            base_w = int(self.size.x * 0.7)
            base_h = int(self.size.y * 0.7)
            cx = screen_pos[0] + base_w // 2
            cy = screen_pos[1] + base_h // 2

            # Largest triangle (bottom)
            triangle1 = [
                (cx - base_w // 2, cy + base_h // 2),
                (cx + base_w // 2, cy + base_h // 2),
                (cx, cy + base_h // 2 - int(base_h * 0.6))
            ]
            # Middle triangle
            triangle2 = [
                (cx - int(base_w * 0.4), cy + int(base_h * 0.1)),
                (cx + int(base_w * 0.4), cy + int(base_h * 0.1)),
                (cx, cy - int(base_h * 0.3))
            ]
            # Top triangle (smallest)
            triangle3 = [
                (cx - int(base_w * 0.2), cy - int(base_h * 0.2)),
                (cx + int(base_w * 0.2), cy - int(base_h * 0.2)),
                (cx, cy - int(base_h * 0.6))
            ]
            pygame.draw.polygon(screen, TREE_GREEN, triangle1)
            pygame.draw.polygon(screen, TREE_GREEN, triangle2)
            pygame.draw.polygon(screen, TREE_GREEN, triangle3)
            # Trunk
            trunk_w = int(base_w * 0.15)
            trunk_h = int(base_h * 0.2)
            trunk_x = cx - trunk_w // 2
            trunk_y = cy + base_h // 2
            pygame.draw.rect(screen, BROWN, (trunk_x, trunk_y, trunk_w, trunk_h))
            return

        elif self.type == "rock":
            # Draw a small gray rounded rock (ellipse)
            width = int(self.size.x * 0.6)
            height = int(self.size.y * 0.6)
            rx = screen_pos[0] + (self.size.x - width) // 2
            ry = screen_pos[1] + (self.size.y - height) // 2
            pygame.draw.ellipse(screen, ROCK_GRAY, (rx, ry, width, height))
            # Optional: draw some shadows for visual effect
            pygame.draw.ellipse(screen, (180, 180, 180), (rx + width // 4, ry + height // 4, width // 2, height // 3))
            return

        # Other types default rendering (just in case)
        pygame.draw.rect(screen, self.color,
                         (*screen_pos, int(self.size.x), int(self.size.y)))


class PowerUp:
    def __init__(self, position: Vector2, type_: str = "unknown", size: int = 20):
        self.position = position
        self.type = type_
        self.size = size
        self.active = True

    def render(self, screen, camera):
        if not self.active:
            return

        screen_pos = (
            int(self.position.x - camera.x - self.size // 2),
            int(self.position.y - camera.y - self.size // 2)
        )

        # Pulsing effect
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 0.3 + 0.7
        color = (int(0 * pulse), int(255 * pulse), int(0 * pulse))

        pygame.draw.rect(screen, color, (*screen_pos, self.size, self.size))

        # Draw cross
        pygame.draw.rect(screen, WHITE,
                         (screen_pos[0] + 2, screen_pos[1] + 6, 12, 4))
        pygame.draw.rect(screen, WHITE,
                         (screen_pos[0] + 6, screen_pos[1] + 2, 4, 12))


class World:
    def __init__(self):
        self.objects = []
        self.power_ups = []
        self.chunk_size = 1000
        self.loaded_chunks = set()
        self.generate_initial_world()

    def generate_initial_world(self):
        for x in range(-2, 3):
            for y in range(-2, 3):
                self.generate_chunk(x, y)

    def generate_chunk(self, chunk_x: int, chunk_y: int):
        chunk_key = f"{chunk_x},{chunk_y}"
        if chunk_key in self.loaded_chunks:
            return

        self.loaded_chunks.add(chunk_key)

        base_x = chunk_x * self.chunk_size
        base_y = chunk_y * self.chunk_size

        # Seed random for consistent generation
        random.seed(chunk_x * 1000 + chunk_y)

        # Generate trees (archa)
        tree_count = 30 + random.randint(0, 20)
        for _ in range(tree_count):
            self.objects.append(WorldObject(
                Vector2(base_x + random.random() * self.chunk_size,
                        base_y + random.random() * self.chunk_size),
                Vector2(18 + random.random() * 6, 22 + random.random() * 6),  # a bit smaller than before
                "tree",
                TREE_GREEN
            ))

        # Generate rocks (used to be house)
        rock_count = 2 + random.randint(0, 3)
        for _ in range(rock_count):
            self.objects.append(WorldObject(
                Vector2(base_x + random.random() * self.chunk_size,
                        base_y + random.random() * self.chunk_size),
                Vector2(13 + random.random() * 7, 14 + random.random() * 7),  # smaller than tree
                "rock",
                ROCK_GRAY
            ))

        # Reset random seed
        random.seed()

    def update(self, player_positions: List[Vector2]):
        for player_pos in player_positions:
            chunk_x = int(player_pos.x // self.chunk_size)
            chunk_y = int(player_pos.y // self.chunk_size)

            for x in range(chunk_x - 1, chunk_x + 2):
                for y in range(chunk_y - 1, chunk_y + 2):
                    self.generate_chunk(x, y)

    def add_power_up(self, position: Vector2):
        self.power_ups.append(PowerUp(position))

    def render(self, screen, camera, screen_width: int, screen_height: int):
        # Render background
        screen.fill(BACKGROUND_COLOR)

        # Render objects in view
        view_left = camera.x - 100
        view_right = camera.x + screen_width + 100
        view_top = camera.y - 100
        view_bottom = camera.y + screen_height + 100

        for obj in self.objects:
            if (obj.position.x + obj.size.x >= view_left and
                    obj.position.x <= view_right and
                    obj.position.y + obj.size.y >= view_top and
                    obj.position.y <= view_bottom):
                obj.render(screen, camera)

        # Render power-ups
        for power_up in self.power_ups:
            if power_up.active:
                power_up.render(screen, camera)
