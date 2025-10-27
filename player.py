from typing import List, Optional

from core import *
from bullet import Bullet
import pygame
import math
import random

from zombie import Zombie


class Player:
    def __init__(self, start_position: Vector2, player_id: int, color = None, controls = None):
        self.position = Vector2(start_position.x, start_position.y)
        self.id = player_id
        self.health = 100
        self.max_health = 100
        self.can_go_down = False
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

        # Downed system variables
        self.down_time = 0  # When player was downed
        self.down_timer_duration = 60000  # 60 seconds in milliseconds
        self.protection_circle_active = False
        self.protection_circle_radius = self.size * 2  # Circle larger than player
        self.protection_timer = 0
        self.protection_duration = 10000  # 10 seconds
        self.revive_progress = 0
        self.revive_duration = 5000  # 5 seconds
        self.being_revived = False
        self.reviver_player = None
        self.invulnerability_time = 0
        self.invulnerability_duration = 3000  # 3 seconds after revive

        self.last_fire_time = 0

        # Input state
        self.controls = controls or {}
        self.move_up = False
        self.move_down = False
        self.move_left = False
        self.move_right = False
        self.shooting = False
        self.target_zombie = None

    def update(self, dt: float, power_ups: List, zombies: List[Zombie], other_players: List) -> List[Bullet]:
 
        bullets = []
        current_time = pygame.time.get_ticks()

        # Handle downed state
        if self.state == PlayerState.DOWNED:
            self.update_downed_state(current_time, other_players)
            return bullets

        # Handle invulnerability after revive
        if self.invulnerability_time > 0:
            self.invulnerability_time -= dt * 1000
            if self.invulnerability_time <= 0:
                self.invulnerability_time = 0

        if self.state == PlayerState.DEAD:
            return bullets
        
        # Movement
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
            print(f"[DEBUG] Player {self.id} pozitsiya: {self.position}")
            
        # Auto-target nearest zombie
        self.target_zombie = self.find_nearest_zombie(zombies)

        # Shooting with auto-aim
        if self.shooting and self.can_fire() and self.target_zombie:
            direction = (self.target_zombie.position - self.position)
            if direction.length() > 0:
                direction = direction.normalize()
                bullets.append(self.create_bullet(direction))
            # Dual pistols fire second bullet
            if self.weapon_type == WeaponType.DUAL_PISTOLS:
                offset_angle = 0.1
                angle = math.atan2(direction.y, direction.x)
                second_direction = Vector2(
                    math.cos(angle + offset_angle),
                    math.sin(angle + offset_angle)
                )
                bullets.append(self.create_bullet(second_direction))

            # Shot gun fire another bullet
            if self.weapon_type == WeaponType.SHOT_GUN:
                angle = math.atan2(direction.y, direction.x)
                offset_angle = 0.15  # You can adjust this for spread

                # Left spread
                left_direction = Vector2(
                    math.cos(angle - offset_angle),
                    math.sin(angle - offset_angle)
                )
                bullets.append(self.create_bullet(left_direction))

                # Right spread
                right_direction = Vector2(
                    math.cos(angle + offset_angle),
                    math.sin(angle + offset_angle)
                )
                bullets.append(self.create_bullet(right_direction))

            self.last_fire_time = pygame.time.get_ticks()



        # Update drone
        if self.drone:
            # Drone follows player with circular motion
            offset_angle = pygame.time.get_ticks() * 0.001
            offset = Vector2(math.cos(offset_angle) * 50, math.sin(offset_angle) * 50)
            target_pos = self.position + offset
            direction = (target_pos - self.drone.position)
            if direction.length() > 0:
                direction = direction.normalize()
                self.drone.position = self.drone.position + direction * 150 * dt

            drone_bullets = self.drone.update(dt, self.position, zombies)
            bullets.extend(drone_bullets)

        if (
            math.isnan(self.position.x) or math.isnan(self.position.y) or
            math.isinf(self.position.x) or math.isinf(self.position.y)
        ):
            print(f"[ERROR] {self.__class__.__name__} {getattr(self, 'id', '')} pozitsiyasi noto'g'ri: {self.position}")

        # Check level progression
        self.check_level_progression()

        return bullets

    def update_downed_state(self, current_time: int, other_players: List):
        # Check if down timer expired
        if current_time - self.down_time >= self.down_timer_duration:
            self.state = PlayerState.DEAD
            self.protection_circle_active = False
            return

        # Update protection circle
        if self.protection_circle_active:
            if current_time - self.protection_timer >= self.protection_duration:
                self.protection_circle_active = False

        # Check for revive by other players
        self.being_revived = False
        self.reviver_player = None

        for other_player in other_players:
            if other_player.state == PlayerState.ALIVE and other_player.id != self.id:
                distance = (self.position - other_player.position).length()
                if distance <= self.protection_circle_radius:
                    self.being_revived = True
                    self.reviver_player = other_player

                    # Activate protection circle when someone enters
                    if not self.protection_circle_active:
                        self.protection_circle_active = True
                        self.protection_timer = current_time

                    # Progress revive
                    self.revive_progress += 16.67  # ~1000ms/60fps = 16.67ms per frame

                    if self.revive_progress >= self.revive_duration:
                        self.revive()
                    break

        # If no one is reviving, reset progress but keep protection if active
        if not self.being_revived:
            self.revive_progress = 0
            # If someone left the circle, deactivate protection
            any_player_in_circle = any(
                other_player.state == PlayerState.ALIVE and
                (self.position - other_player.position).length() <= self.protection_circle_radius
                for other_player in other_players if other_player.id != self.id
            )
            if not any_player_in_circle:
                self.protection_circle_active = False

    def revive(self):
        self.state = PlayerState.ALIVE
        self.health = 30  # 30% of max health (30 out of 100)
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
            WeaponType.PISTOL: 1000,  # 1 shot per second
            WeaponType.DUAL_PISTOLS: 500,  # 2 shots per 
            WeaponType.SHOT_GUN: 300,  # 3 shots per second
            WeaponType.M_16: 333,  # 3 shots per second
            WeaponType.AK_47: 200,  # 5 shots per second
            WeaponType.DRONE: 200,  # 5 shots per second
            WeaponType.M_249: 100,  # 10 shots per second
            WeaponType.MG_3: 66,  # 15 shots per second
            WeaponType.MINI_GUN: 50  # 20 shots per second
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

        # Find zombie within range (300 units)
        nearest_zombie = None
        nearest_distance = 300  # Maximum shooting range

        for zombie in active_zombies:
            distance = (self.position - zombie.position).length()
            if distance < nearest_distance:
                nearest_zombie = zombie
                nearest_distance = distance

        return nearest_zombie

    def check_level_progression(self):
        kills_needed = 15 + random.randint(0, 15)  # 15-30 kills
        if self.zombie_kills >= kills_needed * self.level:
            self.level_up()

    def level_up(self):
        self.level += 1

        # Update weapon
        if self.level >= 100:
            self.weapon_type = WeaponType.MINI_GUN
        elif self.level >= 75:
            self.weapon_type = WeaponType.MG_3
        elif self.level >= 50:
            self.weapon_type = WeaponType.M_249
        elif self.level >= 30:
            self.weapon_type = WeaponType.DRONE
            if not self.drone:
                self.drone = Drone(self.id)
        elif self.level >= 20:
            self.weapon_type = WeaponType.AK_47
        elif self.level >= 15:
            self.weapon_type = WeaponType.SHOT_GUN
        elif self.level >= 10:
            self.weapon_type = WeaponType.M_16
        elif self.level >= 5:
            self.weapon_type = WeaponType.DUAL_PISTOLS

        # Unlock shield at level 10
        if self.level == 10:
            self.max_shield = 100

        # Increase max shield at level 40
        if self.level == 40:
            self.max_shield = 200

        if self.level == 60:
            self.max_shield = 300

        if self.level == 100:
            self.max_shield = 400

    def add_zombie_kill(self):
        self.zombie_kills += 1
        if self.drone:
            self.drone.add_kill()

    def take_damage(self, damage: int):
        current_time = pygame.time.get_ticks()

        # Check invulnerability
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
                # Yangi logika: flaglar orqali boshqariladi
                if self.can_go_down and self.multi_player_mode:
                    self.go_down()
                else:
                    self.state = PlayerState.DEAD

                    
    def go_down(self):
        """Player goes down instead of dying immediately"""
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

        # Render protection circle for downed player
        if self.state == PlayerState.DOWNED and self.protection_circle_active:
            circle_screen_pos = (
                int(self.position.x - camera.x),
                int(self.position.y - camera.y)
            )
            # Draw circle outline
            pygame.draw.circle(screen, LIGHT_BLUE, circle_screen_pos, int(self.protection_circle_radius), 3)
            # Draw semi-transparent fill
            circle_surface = pygame.Surface((self.protection_circle_radius * 2, self.protection_circle_radius * 2),
                                            pygame.SRCALPHA)
            pygame.draw.circle(circle_surface, (135, 206, 235, 50),
                               (self.protection_circle_radius, self.protection_circle_radius),
                               self.protection_circle_radius)
            screen.blit(circle_surface, (circle_screen_pos[0] - self.protection_circle_radius,
                                         circle_screen_pos[1] - self.protection_circle_radius))

        # Draw player based on state
        if self.state == PlayerState.DEAD:
            pygame.draw.rect(screen, DARK_GRAY, (*screen_pos, self.size, self.size))
            return
        elif self.state == PlayerState.DOWNED:
            # Draw downed player in gray with plus symbol
            pygame.draw.rect(screen, GRAY, (*screen_pos, self.size, self.size))
            # Draw large plus symbol
            plus_size = self.size // 3
            center_x = screen_pos[0] + self.size // 2
            center_y = screen_pos[1] + self.size // 2
            pygame.draw.rect(screen, WHITE,
                             (center_x - plus_size // 2, center_y - plus_size // 6, plus_size, plus_size // 3))
            pygame.draw.rect(screen, WHITE,
                             (center_x - plus_size // 6, center_y - plus_size // 2, plus_size // 3, plus_size))

            # Draw countdown timer
            current_time = pygame.time.get_ticks()
            time_left = max(0, self.down_timer_duration - (current_time - self.down_time))
            seconds_left = int(time_left / 1000)
            font = pygame.font.Font(None, 24)
            timer_text = font.render(str(seconds_left), True, RED)
            timer_rect = timer_text.get_rect(center=(center_x, screen_pos[1] - 10))
            screen.blit(timer_text, timer_rect)

            # Draw revive progress if being revived
            if self.being_revived:
                progress_percent = self.revive_progress / self.revive_duration
                bar_width = self.size
                bar_height = 4
                pygame.draw.rect(screen, RED, (screen_pos[0], screen_pos[1] + self.size + 5, bar_width, bar_height))
                pygame.draw.rect(screen, GREEN, (screen_pos[0], screen_pos[1] + self.size + 5,
                                                 int(bar_width * progress_percent), bar_height))
            return

        # Draw alive player with invulnerability effect
        color = self.color
        if self.invulnerability_time > 0:
            # Flashing effect during invulnerability
            if int(pygame.time.get_ticks() / 100) % 2:
                color = tuple(min(255, c + 100) for c in color)
        pygame.draw.rect(screen, color, (*screen_pos, self.size, self.size))
        
        # Draw weapon direction pointing to target
        if self.target_zombie and self.target_zombie.active:
            direction = (self.target_zombie.position - self.position).normalize()
            weapon_end = Vector2(
                screen_pos[0] + self.size // 2 + direction.x * 25,
                screen_pos[1] + self.size // 2 + direction.y * 25
            )
            pygame.draw.line(screen, BLACK,
                             (screen_pos[0] + self.size // 2, screen_pos[1] + self.size // 2),
                             (int(weapon_end.x), int(weapon_end.y)), 3)

            # Auto aim targeting line removed - invisible now

        # Draw health bar
        self.render_health_bar(screen, screen_pos)

        # Draw shield bar
        if self.max_shield > 0:
            self.render_shield_bar(screen, screen_pos)

        # Draw level indicator
        self.render_level_indicator(screen, screen_pos)

        # Draw drone
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

    def render_level_indicator(self, screen, screen_pos):
        # Level text above player
        font = pygame.font.Font(None, 24)
        level_text = f"LVL {self.level}"

        # Color coding for different level ranges
        if self.level >= 999:
            color = (255, 215, 0)  # Gold for max level
        elif self.level >= 500:
            color = (255, 0, 0)  # Red for high levels
        elif self.level >= 100:
            color = (255, 165, 0)  # Orange for high levels
        elif self.level >= 50:
            color = (128, 0, 128)  # Purple for mid levels
        elif self.level >= 20:
            color = (0, 255, 255)  # Cyan for medium levels
        else:
            color = WHITE  # White for low levels

        text_surface = font.render(level_text, True, color)
        text_rect = text_surface.get_rect()
        text_rect.centerx = screen_pos[0] + self.size // 2
        text_rect.bottom = screen_pos[1] - 5

        # Draw background for better visibility
        bg_rect = text_rect.inflate(4, 2)
        pygame.draw.rect(screen, (0, 0, 0, 128), bg_rect)
        screen.blit(text_surface, text_rect)


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

        # Follow player with circular motion
        offset_angle = pygame.time.get_ticks() * 0.001
        offset = Vector2(math.cos(offset_angle) * 50, math.sin(offset_angle) * 50)
        target_pos = player_pos + offset

        direction = (target_pos - self.position).normalize()
        self.position = self.position + direction * 150 * dt

        # Find target
        active_zombies = [z for z in zombies if z.active]
        if active_zombies:
            self.target = min(active_zombies,
                              key=lambda z: (self.position - z.position).length())

        # Attack target
        if self.target and self.target.active:
            distance = (self.position - self.target.position).length()
            current_time = pygame.time.get_ticks()

            if distance <= 200:
                # Regular shots
                if current_time - self.last_fire_time >= 1000:  # 1 shot per second
                    shoot_direction = (self.target.position - self.position).normalize()
                    bullets.append(Bullet(self.position, shoot_direction, 8, self.player_id, 300))
                    self.last_fire_time = current_time

                # Rocket shots at max level
                if self.level >= 10 and current_time - self.last_rocket_time >= 5000:
                    shoot_direction = (self.target.position - self.position).normalize()
                    bullets.append(Bullet(self.position, shoot_direction, 25, self.player_id, 200))
                    self.last_rocket_time = current_time

        return bullets

    def add_kill(self):
        if random.random() < 0.1:  # 10% chance to level up per kill
            self.level = min(self.level + 1, self.max_level)

    def render(self, screen, camera):
        screen_pos = (
            int(self.position.x - camera.x - self.size // 2),
            int(self.position.y - camera.y - self.size // 2)
        )

        color = ORANGE if self.level >= 10 else BLUE
        pygame.draw.rect(screen, color, (*screen_pos, self.size, self.size))

        # Draw level indicator
        font = pygame.font.Font(None, 16)
        text = font.render(str(self.level), True, WHITE)
        text_rect = text.get_rect(center=(screen_pos[0] + self.size // 2,
                                          screen_pos[1] + self.size // 2))
        screen.blit(text, text_rect)
