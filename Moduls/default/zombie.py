import random
import math
from typing import List
from enum import Enum
import pygame

from core import Vector2

RED = (255, 0, 0)
GREEN = (0, 255, 0)

class ZombieType(Enum):
    WALKER = "Walker"
    RUNNER = "Runner"
    TANKER = "Tanker"

ALL_ZOMBIE_TYPES = [ZombieType.WALKER, ZombieType.RUNNER, ZombieType.TANKER]

class Zombie:
    def __init__(self, position: Vector2, strength: int = 1, ztype: ZombieType = ZombieType.WALKER):
        self.type = ztype
        self.position = Vector2(position.x, position.y)
        self.strength = strength

        if self.type == ZombieType.WALKER:
            self.size = 20
            self.speed = 50 + (strength - 1) * 10
            self.max_health = 20 + (strength - 1) * 10
        elif self.type == ZombieType.RUNNER:
            self.size = 15
            self.speed = int((50 + (strength - 1) * 10) * 1.3)
            self.max_health = 20 + (strength - 1) * 10
        elif self.type == ZombieType.TANKER:
            self.size = 28
            self.speed = 50 + (strength - 1) * 10
            self.max_health = int((20 + (strength - 1) * 10) * 1.4)

        self.health = self.max_health
        self.last_attack_time = 0
        self.active = True

    def update(self, dt: float, player_positions: List[Vector2], protection_circles: List):
        if not self.active or self.health <= 0:
            return

        # Find nearest player (only alive players)
        if not player_positions:
            return

        nearest_player = min(player_positions,
                             key=lambda p: (self.position - p).length())

        # Check if zombie is trying to enter a protection circle
        for circle in protection_circles:
            if circle['active']:
                distance_to_circle = (self.position - circle['position']).length()
                circle_radius = circle['radius']

                # If zombie touches the circle, it dies
                if distance_to_circle <= circle_radius + self.size // 2:
                    self.active = False
                    return

                # If zombie is moving towards the circle, redirect it
                direction_to_player = (nearest_player - self.position).normalize()
                direction_to_circle = (circle['position'] - self.position).normalize()

                # Calculate if the zombie's path would intersect the circle
                future_pos = self.position + direction_to_player * self.speed * dt * 5
                future_distance_to_circle = (future_pos - circle['position']).length()

                if future_distance_to_circle < circle_radius + 20:
                    # Redirect zombie around the circle
                    perpendicular = Vector2(-direction_to_circle.y, direction_to_circle.x)
                    if random.random() < 0.5:
                        perpendicular = Vector2(direction_to_circle.y, -direction_to_circle.x)

                    redirect_direction = (direction_to_player + perpendicular * 2).normalize()
                    self.position = self.position + redirect_direction * self.speed * dt
                    return

        direction = (nearest_player - self.position)
        if direction.length() > 0:
            direction = direction.normalize()
            self.position += direction * self.speed * dt
        
        if (
            math.isnan(self.position.x) or math.isnan(self.position.y) or
            math.isinf(self.position.x) or math.isinf(self.position.y)
        ):
            print(f"[ERROR] {self.__class__.__name__} {getattr(self, 'id', '')} pozitsiyasi noto'g'ri: {self.position}")

    def take_damage(self, damage: int) -> bool:
        self.health -= damage
        if self.health <= 0:
            self.active = False
            return True
        return False

    def can_attack(self, current_time: float) -> bool:
        return current_time - self.last_attack_time >= 1000  # 1 second cooldown

    def attack(self, current_time: float) -> int:
        self.last_attack_time = current_time
        return 10 * self.strength

    def render(self, screen, camera):
        if not self.active:
            return
        if (
            math.isnan(self.position.x) or math.isnan(self.position.y) or
            math.isinf(self.position.x) or math.isinf(self.position.y)
        ):
            return
        screen_pos = (
            int(self.position.x - camera.x - self.size // 2),
            int(self.position.y - camera.y - self.size // 2)
        )

        # Rang va shakl
        if self.type == ZombieType.WALKER:
            color = (100 + self.strength * 20, 50, 50)
            pygame.draw.rect(screen, color, (*screen_pos, self.size, self.size))
        elif self.type == ZombieType.RUNNER:
            color = (180, 100, 180)
            pygame.draw.circle(screen, color, (screen_pos[0] + self.size // 2, screen_pos[1] + self.size // 2), self.size // 2)
        elif self.type == ZombieType.TANKER:
            color = (80, 30, 30)
            pygame.draw.ellipse(screen, color, (*screen_pos, self.size, self.size + 8))

        # Health bar
        if self.health < self.max_health:
            bar_width = self.size
            bar_height = 3
            health_percent = self.health / self.max_health
            pygame.draw.rect(screen, (255, 0, 0), (screen_pos[0], screen_pos[1] - 8, bar_width, bar_height))
            pygame.draw.rect(screen, (0, 255, 0), (screen_pos[0], screen_pos[1] - 8, int(bar_width * health_percent), bar_height))

        # Draw health bar if damaged
        if self.health < self.max_health:
            bar_width = self.size
            bar_height = 3
            health_percent = self.health / self.max_health

            # Background
            pygame.draw.rect(screen, RED,
                             (screen_pos[0], screen_pos[1] - 8, bar_width, bar_height))
            # Health
            pygame.draw.rect(screen, GREEN,
                             (screen_pos[0], screen_pos[1] - 8,
                              int(bar_width * health_percent), bar_height))
