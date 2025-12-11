import pygame

from core import Vector2, YELLOW


class Bullet:
    def __init__(self, position: Vector2, direction: Vector2, damage: int, player_id: int, speed: float = 400):
        self.position = Vector2(position.x, position.y)
        self.velocity = direction.normalize() * speed
        self.damage = damage
        self.player_id = player_id
        self.range = 300

        self.travel_distance = 0
        self.active = True

    def update(self, dt: float):
        if not self.active:
            return

        movement = self.velocity * dt
        self.position = self.position + movement
        self.travel_distance += movement.length()
        if self.travel_distance >= self.range:
            self.active = False

    def render(self, screen, camera):
        if not self.active:
            return

        screen_pos = (
            int(self.position.x - camera.x),
            int(self.position.y - camera.y)
        )
        pygame.draw.circle(screen, YELLOW, screen_pos, 3)
