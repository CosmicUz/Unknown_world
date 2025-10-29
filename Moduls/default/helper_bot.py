import random
import math
import numpy as np

from core import Vector2, WeaponType, PlayerState, GameMode
from .zombie import ZombieType
from .player import Player


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

    def update(self, dt, power_ups, zombies, other_players):
        bullets = []
        if hasattr(self, "is_leader") and not self.is_leader and hasattr(self, "leader_id"):
            leader = next((p for p in other_players if getattr(p, "id", None) == self.leader_id), None)
            if leader:
                leader_radius = 150
                distance = (leader.position - self.position).length()
                if not math.isnan(distance) and distance > leader_radius:
                    direction = (leader.position - self.position)
                    if direction.length() > 0:
                        direction = direction.normalize()
                        self.position += direction * self.get_speed() * dt
                    return bullets
                return bullets

        if self.state != PlayerState.ALIVE:
            return bullets

        if self.reviving_target is not None:
            bullets += super().update(dt, power_ups, zombies, other_players)
            return bullets

        if len(zombies) >= 2:
            angles = []
            positions = []
            for z in zombies:
                vec = z.position - self.position
                if vec.length() > 0:
                    angle = math.atan2(vec.y, vec.x)
                    angles.append(angle)
                    positions.append(z.position)
            sorted_zombies = sorted(zip(angles, positions), key=lambda x: x[0])
            max_gap = 0
            escape_angle = None
            for i in range(len(sorted_zombies)):
                a1 = sorted_zombies[i][0]
                a2 = sorted_zombies[(i + 1) % len(sorted_zombies)][0]
                gap = (a2 - a1) % (2 * math.pi)
                if gap > max_gap:
                    max_gap = gap
                    escape_angle = (a1 + gap / 2) % (2 * math.pi)
            if escape_angle is not None:
                escape_dir = Vector2(math.cos(escape_angle), math.sin(escape_angle))
                nearest_player = None
                min_player_dist = float('inf')
                for p in other_players:
                    if p.state == PlayerState.ALIVE:
                        dist = (p.position - self.position).length()
                        if dist < min_player_dist:
                            min_player_dist = dist
                            nearest_player = p
                if nearest_player:
                    player_dir = (nearest_player.position - self.position)
                    if player_dir.length() > 0:
                        player_dir = player_dir.normalize()
                        dot = escape_dir.x * player_dir.x + escape_dir.y * player_dir.y
                        angle_between = math.acos(np.clip(dot, -1, 1)) * 180 / math.pi
                        if angle_between < 60:
                            escape_dir = player_dir
                speed = self.get_speed()
                self.position += escape_dir * speed * dt
                self.shooting = False
                self.target_zombie = None
                bullets += super().update(dt, power_ups, zombies, other_players)
                return bullets

        need_hp = self.health < self.max_health * 0.7
        need_shield = self.shield < self.max_shield * 0.7 if hasattr(self, "max_shield") else False
        target_powerup = None
        min_pu_dist = float('inf')
        if need_hp or need_shield:
            for pu in power_ups:
                if not pu.active:
                    continue
                if need_hp and (pu.type == "hp" or pu.type == "health" or pu.type == "unknown"):
                    dist = (pu.position - self.position).length()
                    if dist < min_pu_dist:
                        min_pu_dist = dist
                        target_powerup = pu
                elif need_shield and (pu.type == "shield"):
                    dist = (pu.position - self.position).length()
                    if dist < min_pu_dist:
                        min_pu_dist = dist
                        target_powerup = pu

        if target_powerup:
            direction = (target_powerup.position - self.position)
            dist_to_pu = direction.length()
            direction = direction.normalize() if dist_to_pu > 0 else Vector2(0, 0)
            blocked = False
            for z in zombies:
                to_zombie = (z.position - self.position)
                if to_zombie.length() > 0:
                    proj = direction.x * to_zombie.x + direction.y * to_zombie.y
                    proj /= to_zombie.length()
                else:
                    proj = 0
                if proj > 0.8 and 0 < to_zombie.length() < dist_to_pu and (z.position - (self.position + direction * to_zombie.length())).length() < 40:
                    blocked = True
                    break
            if not blocked:
                speed = self.get_speed()
                self.position += direction * speed * dt
            else:
                nearest_zombie = min(zombies, key=lambda z: (z.position - self.position).length())
                away = (self.position - nearest_zombie.position)
                if away.length() > 0:
                    away = away.normalize()
                perp = Vector2(-direction.y, direction.x)
                if random.random() < 0.5:
                    perp = -perp
                move_dir = (away + perp * 0.7)
                if move_dir.length() > 0:
                    move_dir = move_dir.normalize()
                    self.position += move_dir * self.get_speed() * dt
            self.shooting = False
            self.target_zombie = None
            bullets += super().update(dt, power_ups, zombies, other_players)
            return bullets

        nearest_zombie = None
        min_dist = float('inf')
        for z in zombies:
            dist = (z.position - self.position).length()
            if dist < min_dist:
                min_dist = dist
                nearest_zombie = z

        shoot_radius = 300
        escape_radius = shoot_radius / 2

        if nearest_zombie and min_dist < escape_radius:
            direction = (self.position - nearest_zombie.position)
            if direction.length() > 0:
                direction = direction.normalize()
                speed = self.get_speed()
                self.position += direction * speed * dt
            self.shooting = False
            self.target_zombie = None

        elif nearest_zombie and min_dist < shoot_radius:
            self.shooting = True
            self.target_zombie = nearest_zombie

        else:
            self.shooting = False
            self.target_zombie = None

        if other_players:
            main_player = other_players[0]
            dist_to_main = (self.position - main_player.position).length()
            if dist_to_main > 200:
                direction = (main_player.position - self.position)
                if direction.length() > 0:
                    direction = direction.normalize()
                    speed = self.get_speed()
                    self.position += direction * speed * dt

        # --- Push-back ---
        for p in other_players:
            if getattr(p, "state", None) == PlayerState.ALIVE and p is not self:
                dist = (self.position - p.position).length()
                if dist < 40:
                    push_dir = (self.position - p.position)
                    if push_dir.length() > 0:
                        push_dir = push_dir.normalize()
                        push_strength = (40 - dist) / 40
                        self.position += push_dir * push_strength * self.get_speed() * dt

        if (
            math.isnan(self.position.x) or math.isnan(self.position.y) or
            math.isinf(self.position.x) or math.isinf(self.position.y)
        ):
            print(f"[ERROR] {self.__class__.__name__} {getattr(self, 'id', '')} pozitsiyasi noto'g'ri: {self.position}")

        bullets += super().update(dt, power_ups, zombies, other_players)
        return bullets

    def get_speed(self):
        return 120

    def try_revive(self, player, dt):
        if player.state == PlayerState.DOWNED:
            player.revive_progress += dt * 1000
            if player.revive_progress >= player.revive_duration:
                player.state = PlayerState.ALIVE
                player.health = player.max_health // 2
                player.revive_progress = 0