import math
import random
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from core import Vector2, PlayerState

if TYPE_CHECKING:
    from .player import Player
    from .zombie import Zombie


class BotState(Enum):
    IDLE = "idle"
    FOLLOW_PLAYER = "follow_player"
    ATTACK = "attack"
    ESCAPE = "escape"
    PROTECT_PLAYER = "protect_player"
    COLLECT_POWERUP = "collect_powerup"
    REVIVE_PLAYER = "revive_player"


class ThreatLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class BotAI:
    def __init__(self, bot):
        self.bot = bot
        self.state = BotState.IDLE
        self.previous_state = BotState.IDLE
        self.target_position: Optional[Vector2] = None
        self.target_zombie: Optional['Zombie'] = None
        self.target_player: Optional['Player'] = None
        self.state_timer = 0
        
        self.follow_distance = 120
        self.attack_range = 280
        self.escape_range = 80
        self.protect_range = 200
        self.revive_range = 60
        
        self.aggression = 0.6
        self.caution = 0.4
        self.loyalty = 0.8

    def evaluate_threat_level(self, zombies: List['Zombie']) -> ThreatLevel:
        if not zombies:
            return ThreatLevel.NONE
        
        close_zombies = 0
        very_close_zombies = 0
        
        for zombie in zombies:
            if not zombie.active:
                continue
            dist = (zombie.position - self.bot.position).length()
            if dist < self.escape_range:
                very_close_zombies += 1
            elif dist < self.attack_range:
                close_zombies += 1
        
        if very_close_zombies >= 3:
            return ThreatLevel.CRITICAL
        elif very_close_zombies >= 1:
            return ThreatLevel.HIGH
        elif close_zombies >= 5:
            return ThreatLevel.HIGH
        elif close_zombies >= 2:
            return ThreatLevel.MEDIUM
        elif close_zombies >= 1:
            return ThreatLevel.LOW
        return ThreatLevel.NONE

    def find_nearest_alive_player(self, players: List['Player']) -> Optional['Player']:
        nearest = None
        min_dist = float('inf')
        for p in players:
            if p.state == PlayerState.ALIVE and p is not self.bot:
                dist = (p.position - self.bot.position).length()
                if dist < min_dist:
                    min_dist = dist
                    nearest = p
        return nearest

    def find_downed_player(self, players: List['Player']) -> Optional['Player']:
        for p in players:
            if p.state == PlayerState.DOWNED and p is not self.bot:
                dist = (p.position - self.bot.position).length()
                if dist < 300:
                    return p
        return None

    def find_nearest_zombie(self, zombies: List['Zombie']) -> Optional['Zombie']:
        nearest = None
        min_dist = float('inf')
        for z in zombies:
            if not z.active:
                continue
            dist = (z.position - self.bot.position).length()
            if dist < min_dist:
                min_dist = dist
                nearest = z
        return nearest

    def find_zombie_threatening_player(self, zombies: List['Zombie'], player: 'Player') -> Optional['Zombie']:
        nearest = None
        min_dist = float('inf')
        for z in zombies:
            if not z.active:
                continue
            dist = (z.position - player.position).length()
            if dist < self.protect_range and dist < min_dist:
                min_dist = dist
                nearest = z
        return nearest

    def calculate_escape_direction(self, zombies: List['Zombie']) -> Vector2:
        if not zombies:
            return Vector2(0, 0)
        
        escape_vec = Vector2(0, 0)
        for z in zombies:
            if not z.active:
                continue
            dist = (z.position - self.bot.position).length()
            if dist < self.attack_range and dist > 0:
                away = self.bot.position - z.position
                weight = 1.0 / max(dist, 1)
                escape_vec.x += away.x * weight
                escape_vec.y += away.y * weight
        
        if escape_vec.length() > 0:
            return escape_vec.normalize()
        return Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()

    def decide_state(self, zombies: List['Zombie'], players: List['Player'], power_ups) -> BotState:
        if self.bot.state != PlayerState.ALIVE:
            return BotState.IDLE
        
        threat = self.evaluate_threat_level(zombies)
        
        downed_player = self.find_downed_player(players)
        if downed_player:
            dist_to_downed = (downed_player.position - self.bot.position).length()
            if dist_to_downed < 300:
                self.target_player = downed_player
                return BotState.REVIVE_PLAYER
        
        if threat == ThreatLevel.CRITICAL:
            return BotState.ESCAPE
        
        if threat == ThreatLevel.HIGH and self.bot.health < self.bot.max_health * 0.4:
            return BotState.ESCAPE
        
        nearest_player = self.find_nearest_alive_player(players)
        if nearest_player:
            zombie_near_player = self.find_zombie_threatening_player(zombies, nearest_player)
            if zombie_near_player and self.loyalty > 0.5:
                self.target_zombie = zombie_near_player
                self.target_player = nearest_player
                return BotState.PROTECT_PLAYER
        
        need_health = self.bot.health < self.bot.max_health * 0.6
        need_shield = hasattr(self.bot, 'shield') and self.bot.shield < self.bot.max_shield * 0.5
        if (need_health or need_shield) and power_ups:
            for pu in power_ups:
                if pu.active:
                    dist = (pu.position - self.bot.position).length()
                    if dist < 400:
                        self.target_position = pu.position
                        return BotState.COLLECT_POWERUP
        
        if threat != ThreatLevel.NONE:
            nearest_zombie = self.find_nearest_zombie(zombies)
            if nearest_zombie:
                self.target_zombie = nearest_zombie
                return BotState.ATTACK
        
        if nearest_player:
            dist_to_player = (nearest_player.position - self.bot.position).length()
            if dist_to_player > self.follow_distance:
                self.target_player = nearest_player
                return BotState.FOLLOW_PLAYER
        
        return BotState.IDLE

    def execute_state(self, dt: float, zombies: List['Zombie'], players: List['Player']) -> dict:
        result = {
            'move_direction': Vector2(0, 0),
            'shooting': False,
            'target_zombie': None
        }
        
        if self.state == BotState.IDLE:
            result = self._execute_idle(dt, players)
        elif self.state == BotState.FOLLOW_PLAYER:
            result = self._execute_follow(dt)
        elif self.state == BotState.ATTACK:
            result = self._execute_attack(dt, zombies)
        elif self.state == BotState.ESCAPE:
            result = self._execute_escape(dt, zombies, players)
        elif self.state == BotState.PROTECT_PLAYER:
            result = self._execute_protect(dt, zombies)
        elif self.state == BotState.COLLECT_POWERUP:
            result = self._execute_collect(dt, zombies)
        elif self.state == BotState.REVIVE_PLAYER:
            result = self._execute_revive(dt)
        
        return result

    def _execute_idle(self, dt: float, players: List['Player']) -> dict:
        nearest_player = self.find_nearest_alive_player(players)
        if nearest_player:
            dist = (nearest_player.position - self.bot.position).length()
            if dist > self.follow_distance * 0.5:
                direction = (nearest_player.position - self.bot.position)
                if direction.length() > 0:
                    return {
                        'move_direction': direction.normalize() * 0.3,
                        'shooting': False,
                        'target_zombie': None
                    }
        return {'move_direction': Vector2(0, 0), 'shooting': False, 'target_zombie': None}

    def _execute_follow(self, dt: float) -> dict:
        if not self.target_player:
            return {'move_direction': Vector2(0, 0), 'shooting': False, 'target_zombie': None}
        
        direction = self.target_player.position - self.bot.position
        dist = direction.length()
        
        if dist > self.follow_distance * 0.8:
            if direction.length() > 0:
                return {
                    'move_direction': direction.normalize(),
                    'shooting': False,
                    'target_zombie': None
                }
        
        return {'move_direction': Vector2(0, 0), 'shooting': False, 'target_zombie': None}

    def _execute_attack(self, dt: float, zombies: List['Zombie']) -> dict:
        if not self.target_zombie or not self.target_zombie.active:
            self.target_zombie = self.find_nearest_zombie(zombies)
        
        if not self.target_zombie:
            return {'move_direction': Vector2(0, 0), 'shooting': False, 'target_zombie': None}
        
        dist = (self.target_zombie.position - self.bot.position).length()
        direction = Vector2(0, 0)
        
        if dist < self.escape_range:
            away = self.bot.position - self.target_zombie.position
            if away.length() > 0:
                direction = away.normalize()
        elif dist > self.attack_range * 0.8:
            toward = self.target_zombie.position - self.bot.position
            if toward.length() > 0:
                direction = toward.normalize() * 0.5
        
        return {
            'move_direction': direction,
            'shooting': dist < self.attack_range,
            'target_zombie': self.target_zombie
        }

    def _execute_escape(self, dt: float, zombies: List['Zombie'], players: List['Player']) -> dict:
        escape_dir = self.calculate_escape_direction(zombies)
        
        nearest_player = self.find_nearest_alive_player(players)
        if nearest_player:
            to_player = nearest_player.position - self.bot.position
            if to_player.length() > 0:
                to_player = to_player.normalize()
                dot = escape_dir.x * to_player.x + escape_dir.y * to_player.y
                if dot > 0.3:
                    escape_dir.x = (escape_dir.x + to_player.x * 0.5)
                    escape_dir.y = (escape_dir.y + to_player.y * 0.5)
                    if escape_dir.length() > 0:
                        escape_dir = escape_dir.normalize()
        
        return {
            'move_direction': escape_dir,
            'shooting': False,
            'target_zombie': None
        }

    def _execute_protect(self, dt: float, zombies: List['Zombie']) -> dict:
        if not self.target_player or not self.target_zombie:
            return {'move_direction': Vector2(0, 0), 'shooting': False, 'target_zombie': None}
        
        if not self.target_zombie.active:
            self.target_zombie = self.find_zombie_threatening_player(zombies, self.target_player)
        
        if not self.target_zombie:
            return {'move_direction': Vector2(0, 0), 'shooting': False, 'target_zombie': None}
        
        player_to_zombie = self.target_zombie.position - self.target_player.position
        if player_to_zombie.length() > 0:
            intercept_pos = self.target_player.position + player_to_zombie.normalize() * 60
        else:
            intercept_pos = self.target_player.position
        
        direction = intercept_pos - self.bot.position
        dist = direction.length()
        
        move_dir = Vector2(0, 0)
        if dist > 30:
            move_dir = direction.normalize()
        
        zombie_dist = (self.target_zombie.position - self.bot.position).length()
        
        return {
            'move_direction': move_dir,
            'shooting': zombie_dist < self.attack_range,
            'target_zombie': self.target_zombie
        }

    def _execute_collect(self, dt: float, zombies: List['Zombie']) -> dict:
        if not self.target_position:
            return {'move_direction': Vector2(0, 0), 'shooting': False, 'target_zombie': None}
        
        direction = self.target_position - self.bot.position
        dist = direction.length()
        
        if dist < 20:
            self.target_position = None
            return {'move_direction': Vector2(0, 0), 'shooting': False, 'target_zombie': None}
        
        for z in zombies:
            if not z.active:
                continue
            zdist = (z.position - self.bot.position).length()
            if zdist < self.escape_range:
                escape_dir = self.calculate_escape_direction(zombies)
                return {
                    'move_direction': escape_dir,
                    'shooting': False,
                    'target_zombie': None
                }
        
        return {
            'move_direction': direction.normalize() if dist > 0 else Vector2(0, 0),
            'shooting': False,
            'target_zombie': None
        }

    def _execute_revive(self, dt: float) -> dict:
        if not self.target_player or self.target_player.state != PlayerState.DOWNED:
            self.target_player = None
            return {'move_direction': Vector2(0, 0), 'shooting': False, 'target_zombie': None}
        
        direction = self.target_player.position - self.bot.position
        dist = direction.length()
        
        if dist > self.revive_range:
            return {
                'move_direction': direction.normalize() if dist > 0 else Vector2(0, 0),
                'shooting': False,
                'target_zombie': None
            }
        
        return {
            'move_direction': Vector2(0, 0),
            'shooting': False,
            'target_zombie': None,
            'reviving': True
        }

    def update(self, dt: float, zombies: List['Zombie'], players: List['Player'], power_ups) -> dict:
        self.previous_state = self.state
        self.state = self.decide_state(zombies, players, power_ups)
        
        if self.state != self.previous_state:
            self.state_timer = 0
        else:
            self.state_timer += dt
        
        return self.execute_state(dt, zombies, players)
