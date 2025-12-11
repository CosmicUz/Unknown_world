import pygame
import math
from typing import List, Optional
from core import Vector2, WeaponType
from .bullet import Bullet


class Base:
    def __init__(self, position: Vector2):
        self.position = Vector2(position.x, position.y)
        self.health = 1000
        self.max_health = 1000
        self.size = 80
        self.color = (100, 100, 200)
        
        self.level = 1
        self.zombie_kills = 0
        self.weapon_type = WeaponType.PISTOL
        
        self.last_fire_time = 0
        self.fire_rate = 1000
        self.damage = 100
        
        self.target_zombie = None
        self.active = True
        
        self.chain_radius = 150
        
    def update(self, dt: float, zombies: List, connected_players: List) -> List[Bullet]:
        bullets = []
        
        if self.health <= 0:
            self.active = False
            return bullets
        
        movement = self.calculate_movement(connected_players, dt)
        if movement.length() > 0:
            self.position = self.position + movement
            
        self.target_zombie = self.find_nearest_zombie(zombies)
        
        if self.target_zombie and self.can_fire():
            direction = (self.target_zombie.position - self.position)
            if direction.length() > 0:
                direction = direction.normalize()
                bullets.append(self.create_bullet(direction))
                self.last_fire_time = pygame.time.get_ticks()
        
        self.check_level_progression()
        self.update_player_weapons(connected_players)
        
        return bullets
    
    def calculate_movement(self, connected_players: List, dt: float) -> Vector2:
        if not connected_players:
            return Vector2(0, 0)
        
        moving_players = []
        total_direction = Vector2(0, 0)
        
        for player in connected_players:
            move_dir = Vector2(0, 0)
            if hasattr(player, 'move_up') and player.move_up:
                move_dir.y -= 1
            if hasattr(player, 'move_down') and player.move_down:
                move_dir.y += 1
            if hasattr(player, 'move_left') and player.move_left:
                move_dir.x -= 1
            if hasattr(player, 'move_right') and player.move_right:
                move_dir.x += 1
            
            if hasattr(player, 'is_bot') and player.is_bot:
                if hasattr(player, 'ai') and hasattr(player.ai, 'move_direction'):
                    move_dir = player.ai.move_direction
            
            if move_dir.length() > 0:
                moving_players.append(player)
                total_direction = total_direction + move_dir.normalize()
        
        if len(moving_players) == 0:
            return Vector2(0, 0)
        
        if total_direction.length() > 0:
            total_direction = total_direction.normalize()
            speed = 100
            return total_direction * speed * dt
        
        return Vector2(0, 0)
    
    def find_nearest_zombie(self, zombies: List) -> Optional[object]:
        if not zombies:
            return None
        
        active_zombies = [z for z in zombies if z.active]
        if not active_zombies:
            return None
        
        nearest_zombie = None
        nearest_distance = 400
        
        for zombie in active_zombies:
            distance = (self.position - zombie.position).length()
            if distance < nearest_distance:
                nearest_zombie = zombie
                nearest_distance = distance
        
        return nearest_zombie
    
    def can_fire(self) -> bool:
        current_time = pygame.time.get_ticks()
        return current_time - self.last_fire_time >= self.fire_rate
    
    def create_bullet(self, direction: Vector2) -> Bullet:
        return Bullet(self.position, direction, self.damage, player_id=0, speed=350)
    
    def check_level_progression(self):
        kills_needed = (15 + 15) * 5
        if self.zombie_kills >= kills_needed * self.level:
            self.level_up()
    
    def level_up(self):
        self.level += 1
        
        if self.level >= 100:
            self.weapon_type = WeaponType.MINI_GUN
        elif self.level >= 75:
            self.weapon_type = WeaponType.MG_3
        elif self.level >= 50:
            self.weapon_type = WeaponType.M_249
        elif self.level >= 30:
            self.weapon_type = WeaponType.DRONE
        elif self.level >= 20:
            self.weapon_type = WeaponType.AK_47
        elif self.level >= 15:
            self.weapon_type = WeaponType.SHOT_GUN
        elif self.level >= 10:
            self.weapon_type = WeaponType.M_16
        elif self.level >= 5:
            self.weapon_type = WeaponType.DUAL_PISTOLS
    
    def update_player_weapons(self, connected_players: List):
        for player in connected_players:
            player.weapon_type = self.weapon_type
            player.level = self.level
            
            if self.level >= 10:
                player.max_shield = 100
            if self.level >= 40:
                player.max_shield = 200
            if self.level >= 60:
                player.max_shield = 300
            if self.level >= 100:
                player.max_shield = 400
    
    def add_zombie_kill(self):
        self.zombie_kills += 1
    
    def take_damage(self, damage: int):
        self.health = max(0, self.health - damage)
        if self.health <= 0:
            self.active = False
    
    def render(self, screen, camera):
        if not self.active:
            return
        
        screen_x = int(self.position.x - camera.x)
        screen_y = int(self.position.y - camera.y)
        
        pygame.draw.circle(screen, self.color, (screen_x, screen_y), self.size // 2)
        pygame.draw.circle(screen, (150, 150, 250), (screen_x, screen_y), self.size // 2, 4)
        
        pygame.draw.circle(screen, (80, 80, 150), (screen_x, screen_y), self.size // 2 - 10, 2)
        
        if self.target_zombie and self.target_zombie.active:
            direction = (self.target_zombie.position - self.position).normalize()
            weapon_end_x = screen_x + direction.x * (self.size // 2 + 15)
            weapon_end_y = screen_y + direction.y * (self.size // 2 + 15)
            pygame.draw.line(screen, (50, 50, 100), (screen_x, screen_y), 
                           (int(weapon_end_x), int(weapon_end_y)), 6)
        
        bar_width = self.size
        bar_height = 8
        bar_x = screen_x - bar_width // 2
        bar_y = screen_y - self.size // 2 - 20
        
        pygame.draw.rect(screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        health_width = int(bar_width * (self.health / self.max_health))
        pygame.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, health_width, bar_height))
        
        font = pygame.font.Font(None, 28)
        level_text = f"BASE LVL {self.level}"
        text_surface = font.render(level_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(screen_x, screen_y - self.size // 2 - 35))
        screen.blit(text_surface, text_rect)
        
    def render_chains(self, screen, camera, connected_players: List):
        screen_x = int(self.position.x - camera.x)
        screen_y = int(self.position.y - camera.y)
        
        for player in connected_players:
            player_screen_x = int(player.position.x - camera.x)
            player_screen_y = int(player.position.y - camera.y)
            
            chain_color = (150, 150, 150)
            pygame.draw.line(screen, chain_color, (screen_x, screen_y), 
                           (player_screen_x, player_screen_y), 2)
            
            dx = player_screen_x - screen_x
            dy = player_screen_y - screen_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance > 0:
                num_links = int(distance / 15)
                for i in range(num_links):
                    t = i / max(1, num_links - 1)
                    link_x = screen_x + dx * t
                    link_y = screen_y + dy * t
                    pygame.draw.circle(screen, (100, 100, 100), (int(link_x), int(link_y)), 3)
