from typing import List, Optional

from core import *
from .bullet import Bullet
import pygame
import math
import random

from .zombie import Zombie


class Player:
    def __init__(self, start_position: Vector2, player_id: int, color = None, controls = None):
        self.position = Vector2(start_position.x, start_position.y)
        self.id = player_id
        self.health = 100
        self.max_health = 100
        self.can_go_down = True  
        self.multi_player_mode = False
        self.shield = 0
        self.max_shield = 100
        self.level = 1
        self.zombie_kills = 0
        self.weapon_type = WeaponType.PISTOL
        self.ammo = 30
        self.drone = None
        self.size = 30
        self.speed = 150
        self.last_damage_time = 0
        self.state = PlayerState.ALIVE
        self.color = color if color is not None else (40, 120, 255)

        self.down_time = 0
        self.down_timer_duration = 60000
        self.protection_circle_active = False
        self.protection_circle_radius = self.size * 2
        self.protection_timer = 0
        self.protection_duration = 10000
        self.revive_progress = 0
        self.revive_duration = 5000
        self.being_revived = False
        self.reviver_player = None
        self.invulnerability_time = 0
        self.invulnerability_duration = 3000

        self.last_fire_time = 0

        self.controls = controls or {}
        self.move_up = False
        self.move_down = False
        self.move_left = False
        self.move_right = False
        # orbit controls separate from movement when connected to base
        self.orbit_left = False
        self.orbit_right = False
        self.shooting = False
        self.target_zombie = None
        
        self.connected_to_base = None
        self.orbit_angle = 0.0
        self.orbit_speed = 1.5
        self.chain_length = 120

    def update(self, dt: float, power_ups: List, zombies: List[Zombie], other_players: List) -> List[Bullet]:
        bullets = []
        current_time = pygame.time.get_ticks()

        if self.state == PlayerState.DOWNED:
            self.update_downed_state(current_time, other_players)
            return bullets

        if self.invulnerability_time > 0:
            self.invulnerability_time -= dt * 1000
            if self.invulnerability_time <= 0:
                self.invulnerability_time = 0

        if self.state == PlayerState.DEAD:
            return bullets
        
        if self.connected_to_base:
            self.update_orbit_movement(dt)
        else:
            movement = Vector2(0, 0)
            if self.move_up:
                movement.y -= 1
            if self.move_down:
                movement.y += 1
            if self.move_left:
                movement.x -= 1
            if self.move_right:
                movement.x += 1

            if movement.length() > 0:
                movement = movement.normalize()
                self.position = self.position + movement * self.speed * dt
            
        self.target_zombie = self.find_nearest_zombie(zombies)

        if self.shooting and self.can_fire() and self.target_zombie:
            direction = (self.target_zombie.position - self.position)
            if direction.length() > 0:
                direction = direction.normalize()
                bullets.append(self.create_bullet(direction))
            if self.weapon_type == WeaponType.DUAL_PISTOLS:
                offset_angle = 0.1
                angle = math.atan2(direction.y, direction.x)
                second_direction = Vector2(
                    math.cos(angle + offset_angle),
                    math.sin(angle + offset_angle)
                )
                bullets.append(self.create_bullet(second_direction))

            if self.weapon_type == WeaponType.SHOT_GUN:
                angle = math.atan2(direction.y, direction.x)
                offset_angle = 0.15

                left_direction = Vector2(
                    math.cos(angle - offset_angle),
                    math.sin(angle - offset_angle)
                )
                bullets.append(self.create_bullet(left_direction))

                right_direction = Vector2(
                    math.cos(angle + offset_angle),
                    math.sin(angle + offset_angle)
                )
                bullets.append(self.create_bullet(right_direction))

            self.last_fire_time = pygame.time.get_ticks()

        if self.drone:
            offset_angle = pygame.time.get_ticks() * 0.001
            offset = Vector2(math.cos(offset_angle) * 50, math.sin(offset_angle) * 50)
            target_pos = self.position + offset
            direction = (target_pos - self.drone.position)
            if direction.length() > 0:
                direction = direction.normalize()
                self.drone.position = self.drone.position + direction * 150 * dt

            drone_bullets = self.drone.update(dt, self.position, zombies)
            bullets.extend(drone_bullets)

        return bullets

    def update_orbit_movement(self, dt: float):
        if not self.connected_to_base:
            return
            
        orbit_direction = 0
        # Use explicit orbit flags only (set by GameEngine controls).
        # Do NOT fall back to movement flags — movement keys should not cause orbit when connected to base.
        left = getattr(self, 'orbit_left', False)
        right = getattr(self, 'orbit_right', False)
        if left:
            orbit_direction -= 1
        if right:
            orbit_direction += 1
        
        if orbit_direction != 0:
            self.orbit_angle += orbit_direction * self.orbit_speed * dt
        
        base_pos = self.connected_to_base.position
        self.position.x = base_pos.x + math.cos(self.orbit_angle) * self.chain_length
        self.position.y = base_pos.y + math.sin(self.orbit_angle) * self.chain_length

    def connect_to_base(self, base, initial_angle: float = 0.0):
        self.connected_to_base = base
        self.orbit_angle = initial_angle
        self.chain_length = base.size // 2 + 50
        
        self.position.x = base.position.x + math.cos(self.orbit_angle) * self.chain_length
        self.position.y = base.position.y + math.sin(self.orbit_angle) * self.chain_length

    def update_downed_state(self, current_time: int, other_players: List):
        if current_time - self.down_time >= self.down_timer_duration:
            self.state = PlayerState.DEAD
            self.protection_circle_active = False
            return

        if self.protection_circle_active:
            if current_time - self.protection_timer >= self.protection_duration:
                self.protection_circle_active = False

        self.being_revived = False
        self.reviver_player = None

        for other_player in other_players:
            if other_player.state == PlayerState.ALIVE and other_player.id != self.id:
                distance = (self.position - other_player.position).length()
                if distance <= self.protection_circle_radius:
                    self.being_revived = True
                    self.reviver_player = other_player

                    if not self.protection_circle_active:
                        self.protection_circle_active = True
                        self.protection_timer = current_time

                    self.revive_progress += 16.67

                    if self.revive_progress >= self.revive_duration:
                        self.revive()
                    break

        if not self.being_revived:
            self.revive_progress = 0
            any_player_in_circle = any(
                other_player.state == PlayerState.ALIVE and
                (self.position - other_player.position).length() <= self.protection_circle_radius
                for other_player in other_players if other_player.id != self.id
            )
            if not any_player_in_circle:
                self.protection_circle_active = False

    def revive(self):
        self.state = PlayerState.ALIVE
        self.health = 30
        self.protection_circle_active = False
        self.revive_progress = 0
        self.being_revived = False
        self.reviver_player = None
        self.invulnerability_time = self.invulnerability_duration

    def get_protection_circle_info(self):
        if self.state == PlayerState.DOWNED and self.protection_circle_active:
            return {
                'active': True,
                'position': self.position,
                'radius': self.protection_circle_radius
            }
        return {'active': False, 'position': self.position, 'radius': 0}

    def can_fire(self) -> bool:
        current_time = pygame.time.get_ticks()
        fire_rates = {
            WeaponType.PISTOL: 1000,
            WeaponType.DUAL_PISTOLS: 500,
            WeaponType.SHOT_GUN: 300,
            WeaponType.M_16: 333,
            WeaponType.AK_47: 200,
            WeaponType.DRONE: 200,
            WeaponType.M_249: 100,
            WeaponType.MG_3: 66,
            WeaponType.MINI_GUN: 50
        }
        return current_time - self.last_fire_time >= fire_rates[self.weapon_type]

    def create_bullet(self, direction: Vector2) -> Bullet:
        damages = {
            WeaponType.PISTOL: 7,
            WeaponType.DUAL_PISTOLS: 8,
            WeaponType.M_16: 13,
            WeaponType.SHOT_GUN: 10,
            WeaponType.AK_47: 15,
            WeaponType.DRONE: 20,
            WeaponType.M_249: 17,
            WeaponType.MG_3: 17,
            WeaponType.MINI_GUN: 20
        }
        return Bullet(self.position, direction, damages[self.weapon_type], self.id)

    def find_nearest_zombie(self, zombies: List[Zombie]) -> Optional[Zombie]:
        if not zombies:
            return None

        active_zombies = [z for z in zombies if z.active]
        if not active_zombies:
            return None

        nearest_zombie = None
        nearest_distance = 300

        for zombie in active_zombies:
            distance = (self.position - zombie.position).length()
            if distance < nearest_distance:
                nearest_zombie = zombie
                nearest_distance = distance

        return nearest_zombie

    def check_level_progression(self):
        pass

    def level_up(self):
        pass

    def add_zombie_kill(self):
        pass

    def take_damage(self, damage: int):
        current_time = pygame.time.get_ticks()

        if self.invulnerability_time > 0:
            return

        if current_time - self.last_damage_time < 500:
            return

        self.last_damage_time = current_time

        if self.shield > 0:
            shield_damage = damage * 0.5
            if self.max_shield == 200 and self.shield > 100:
                shield_damage = damage * 0.2
            self.shield = max(0, self.shield - shield_damage)
        else:
            self.health = max(0, self.health - damage)
            if self.health <= 0:
                if self.can_go_down and self.multi_player_mode:
                    self.go_down()
                else:
                    self.state = PlayerState.DEAD

    def go_down(self):
        self.state = PlayerState.DOWNED
        self.down_time = pygame.time.get_ticks()
        self.protection_circle_active = True
        self.protection_timer = pygame.time.get_ticks()
        self.revive_progress = 0
        self.being_revived = False

    def collect_power_up(self):
        if self.health < self.max_health:
            self.health = min(self.health + 10, self.max_health)
        elif self.level >= 10 and self.shield < self.max_shield:
            shield_increase = self.max_shield * 0.04
            self.shield = min(self.shield + shield_increase, self.max_shield)

    def render(self, screen, camera):
        if (
            not hasattr(self.position, "x") or not hasattr(self.position, "y") or
            self.position.x is None or self.position.y is None or
            math.isnan(self.position.x) or math.isnan(self.position.y) or
            math.isinf(self.position.x) or math.isinf(self.position.y)
        ):
            print(f"[ERROR] Player {self.id} pozitsiyasi noto'g'ri: {self.position}")
            return

        screen_pos = (
            int(self.position.x - camera.x - self.size // 2),
            int(self.position.y - camera.y - self.size // 2)
        )

        if self.state == PlayerState.DOWNED and self.protection_circle_active:
            circle_screen_pos = (
                int(self.position.x - camera.x),
                int(self.position.y - camera.y)
            )
            pygame.draw.circle(screen, LIGHT_BLUE, circle_screen_pos, int(self.protection_circle_radius), 3)
            circle_surface = pygame.Surface((self.protection_circle_radius * 2, self.protection_circle_radius * 2),
                                            pygame.SRCALPHA)
            pygame.draw.circle(circle_surface, (135, 206, 235, 50),
                               (self.protection_circle_radius, self.protection_circle_radius),
                               self.protection_circle_radius)
            screen.blit(circle_surface, (circle_screen_pos[0] - self.protection_circle_radius,
                                         circle_screen_pos[1] - self.protection_circle_radius))

        if self.state == PlayerState.DEAD:
            pygame.draw.rect(screen, DARK_GRAY, (*screen_pos, self.size, self.size))
            return
        elif self.state == PlayerState.DOWNED:
            pygame.draw.rect(screen, GRAY, (*screen_pos, self.size, self.size))
            plus_size = self.size // 3
            center_x = screen_pos[0] + self.size // 2
            center_y = screen_pos[1] + self.size // 2
            pygame.draw.rect(screen, WHITE,
                             (center_x - plus_size // 2, center_y - plus_size // 6, plus_size, plus_size // 3))
            pygame.draw.rect(screen, WHITE,
                             (center_x - plus_size // 6, center_y - plus_size // 2, plus_size // 3, plus_size))

            current_time = pygame.time.get_ticks()
            time_left = max(0, self.down_timer_duration - (current_time - self.down_time))
            seconds_left = int(time_left / 1000)
            font = pygame.font.Font(None, 24)
            timer_text = font.render(str(seconds_left), True, RED)
            timer_rect = timer_text.get_rect(center=(center_x, screen_pos[1] - 10))
            screen.blit(timer_text, timer_rect)

            if self.being_revived:
                progress_percent = self.revive_progress / self.revive_duration
                bar_width = self.size
                bar_height = 4
                pygame.draw.rect(screen, RED, (screen_pos[0], screen_pos[1] + self.size + 5, bar_width, bar_height))
                pygame.draw.rect(screen, GREEN, (screen_pos[0], screen_pos[1] + self.size + 5,
                                                 int(bar_width * progress_percent), bar_height))
            return

        color = self.color
        if self.invulnerability_time > 0:
            if int(pygame.time.get_ticks() / 100) % 2:
                color = tuple(min(255, c + 100) for c in color)
        pygame.draw.rect(screen, color, (*screen_pos, self.size, self.size))
        
        if self.target_zombie and self.target_zombie.active:
            direction = (self.target_zombie.position - self.position).normalize()
            weapon_end = Vector2(
                screen_pos[0] + self.size // 2 + direction.x * 25,
                screen_pos[1] + self.size // 2 + direction.y * 25
            )
            pygame.draw.line(screen, BLACK,
                             (screen_pos[0] + self.size // 2, screen_pos[1] + self.size // 2),
                             (int(weapon_end.x), int(weapon_end.y)), 3)

        self.render_health_bar(screen, screen_pos)

        if self.max_shield > 0:
            self.render_shield_bar(screen, screen_pos)

        if self.drone:
            self.drone.render(screen, camera)

    def render_health_bar(self, screen, screen_pos):
        bar_width = self.size
        bar_height = 4
        segment_width = bar_width // 10

        for i in range(10):
            segment_health = max(0, min(10, self.health - i * 10))
            color = GREEN if segment_health > 5 else RED

            if segment_health > 0:
                pygame.draw.rect(screen, color,
                                 (screen_pos[0] + i * segment_width,
                                  screen_pos[1] + self.size + 5,
                                  segment_width - 1, bar_height))
            else:
                pygame.draw.rect(screen, DARK_GRAY,
                                 (screen_pos[0] + i * segment_width,
                                  screen_pos[1] + self.size + 5,
                                  segment_width - 1, bar_height))

    def render_shield_bar(self, screen, screen_pos):
        if self.shield <= 0:
            return

        bar_width = self.size
        bar_height = 3
        shield_percent = self.shield / self.max_shield

        color = LIGHT_BLUE
        if self.max_shield == 200 and self.shield > 100:
            color = DARK_BLUE

        pygame.draw.rect(screen, color,
                         (screen_pos[0], screen_pos[1] + self.size + 10,
                          int(bar_width * shield_percent), bar_height))


class Drone:
    def __init__(self, player_id: int):
        self.position = Vector2(0, 0)
        self.level = 1
        self.max_level = 10
        self.player_id = player_id
        self.last_fire_time = 0
        self.last_rocket_time = 0
        self.target = None
        self.size = 16

    def update(self, dt: float, player_pos: Vector2, zombies: List[Zombie]) -> List[Bullet]:
        bullets = []

        offset_angle = pygame.time.get_ticks() * 0.001
        offset = Vector2(math.cos(offset_angle) * 50, math.sin(offset_angle) * 50)
        target_pos = player_pos + offset

        direction = (target_pos - self.position).normalize()
        self.position = self.position + direction * 150 * dt

        active_zombies = [z for z in zombies if z.active]
        if active_zombies:
            self.target = min(active_zombies,
                              key=lambda z: (self.position - z.position).length())

        if self.target and self.target.active:
            distance = (self.position - self.target.position).length()
            current_time = pygame.time.get_ticks()

            if distance <= 200:
                if current_time - self.last_fire_time >= 1000:
                    shoot_direction = (self.target.position - self.position).normalize()
                    bullets.append(Bullet(self.position, shoot_direction, 8, self.player_id, 300))
                    self.last_fire_time = current_time

                if self.level >= 10 and current_time - self.last_rocket_time >= 5000:
                    shoot_direction = (self.target.position - self.position).normalize()
                    bullets.append(Bullet(self.position, shoot_direction, 25, self.player_id, 200))
                    self.last_rocket_time = current_time

        return bullets

    def add_kill(self):
        if random.random() < 0.1:
            self.level = min(self.level + 1, self.max_level)

    def render(self, screen, camera):
        screen_pos = (
            int(self.position.x - camera.x - self.size // 2),
            int(self.position.y - camera.y - self.size // 2)
        )

        color = ORANGE if self.level >= 10 else BLUE
        pygame.draw.rect(screen, color, (*screen_pos, self.size, self.size))

        font = pygame.font.Font(None, 16)
        text = font.render(str(self.level), True, WHITE)
        text_rect = text.get_rect(center=(screen_pos[0] + self.size // 2,
                                          screen_pos[1] + self.size // 2))
        screen.blit(text, text_rect)
