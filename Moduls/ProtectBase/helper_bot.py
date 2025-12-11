import random
import math

from core import Vector2, WeaponType, PlayerState, GameMode
from .zombie import ZombieType
from .player import Player
from .bot_ai import BotAI, BotState


def safe_get(obj, key, default):
    try:
        val = obj[key]
        return val if val is not None else default
    except (KeyError, TypeError):
        return default

def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def safe_bool(val, default=False):
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return bool(val)
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return default

def safe_enum(enum_cls, value, default):
    try:
        if isinstance(value, enum_cls):
            return value
        return enum_cls(value)
    except Exception:
        return default


class HelperBot(Player):
    def __init__(self, start_position: Vector2, bot_id: int, color):
        super().__init__(start_position, bot_id, color)
        self.is_bot = True
        self.reviving_target = None
        self.ai = BotAI(self)
        self.base_speed = 130
        self.auto_orbit_speed = 0.5

    def update(self, dt, power_ups, zombies, other_players):
        bullets = []
        
        if self.state == PlayerState.DEAD:
            return bullets
        
        if self.state == PlayerState.DOWNED:
            bullets += super().update(dt, power_ups, zombies, other_players)
            return bullets
        
        ai_result = self.ai.update(dt, zombies, other_players, power_ups)
        
        if self.connected_to_base:
            self.update_bot_orbit(dt, zombies)
        else:
            move_dir = ai_result.get('move_direction', Vector2(0, 0))
            if move_dir.length() > 0:
                speed = self.get_speed()
                self.position.x += move_dir.x * speed * dt
                self.position.y += move_dir.y * speed * dt
        
        self.shooting = ai_result.get('shooting', False)
        self.target_zombie = ai_result.get('target_zombie', None)
        
        if ai_result.get('reviving', False) and self.reviving_target:
            self._do_revive(dt)
        else:
            self.reviving_target = self.ai.target_player if self.ai.state == BotState.REVIVE_PLAYER else None
        
        self._validate_position()
        
        bullets += super().update(dt, power_ups, zombies, other_players)
        return bullets

    def update_bot_orbit(self, dt, zombies):
        if not self.connected_to_base:
            return
        
        active_zombies = [z for z in zombies if z.active]
        if active_zombies:
            nearest_zombie = min(active_zombies, key=lambda z: (self.position - z.position).length())
            zombie_dir = nearest_zombie.position - self.connected_to_base.position
            target_angle = math.atan2(zombie_dir.y, zombie_dir.x)
            
            angle_diff = target_angle - self.orbit_angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            if abs(angle_diff) > 0.1:
                orbit_direction = 1 if angle_diff > 0 else -1
                self.orbit_angle += orbit_direction * self.orbit_speed * dt
        else:
            self.orbit_angle += self.auto_orbit_speed * dt
        
        base_pos = self.connected_to_base.position
        self.position.x = base_pos.x + math.cos(self.orbit_angle) * self.chain_length
        self.position.y = base_pos.y + math.sin(self.orbit_angle) * self.chain_length

    def get_speed(self):
        if self.ai.state == BotState.ESCAPE:
            return self.base_speed * 1.3
        elif self.ai.state == BotState.PROTECT_PLAYER:
            return self.base_speed * 1.1
        elif self.ai.state == BotState.REVIVE_PLAYER:
            return self.base_speed * 1.2
        return self.base_speed

    def _do_revive(self, dt):
        if not self.reviving_target:
            return
        if self.reviving_target.state != PlayerState.DOWNED:
            self.reviving_target = None
            return
        
        dist = (self.reviving_target.position - self.position).length()
        if dist < 60:
            self.reviving_target.being_revived = True
            self.reviving_target.reviver_player = self
            self.reviving_target.revive_progress += dt * 1000
            
            if self.reviving_target.revive_progress >= self.reviving_target.revive_duration:
                self.reviving_target.revive()
                self.reviving_target = None

    def _validate_position(self):
        if (
            math.isnan(self.position.x) or math.isnan(self.position.y) or
            math.isinf(self.position.x) or math.isinf(self.position.y)
        ):
            print(f"[ERROR] HelperBot {self.id} pozitsiyasi noto'g'ri: {self.position}")
            self.position = Vector2(0, 0)

    def get_ai_state(self) -> str:
        return self.ai.state.value if self.ai else "unknown"
