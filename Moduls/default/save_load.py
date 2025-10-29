import json
import os
import sqlite3
import time
import pygame

from .helper_bot import safe_get, safe_int, safe_bool, safe_enum, HelperBot
from core import Vector2, WeaponType, PlayerState, GameMode
from .player import Player, Drone
from .world import World, PowerUp, WorldObject
from .zombie import Zombie, ZombieType

SAVE_ROOT = os.path.join(os.path.dirname(__file__), 'saves')
AUTOSAVE_PATH = os.path.join(SAVE_ROOT, 'autosave.db')



def get_save_path(save_name):
    os.makedirs(SAVE_ROOT, exist_ok=True)
    if save_name == "autosave":
        return AUTOSAVE_PATH
    return os.path.join(SAVE_ROOT, f"{save_name}.db")


def get_last_session_path(game_mode):
    return AUTOSAVE_PATH



def save_last_session(game):
    db_path = AUTOSAVE_PATH
    if os.path.exists(db_path):
        os.remove(db_path)
    save_game(game, "autosave", game.mode)

def create_tables(conn):
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS player (
            id INTEGER PRIMARY KEY,
            position_x REAL, position_y REAL,
            health INTEGER, max_health INTEGER, shield INTEGER, max_shield INTEGER,
            level INTEGER, zombie_kills INTEGER,
            weapon_type TEXT, ammo INTEGER, state TEXT,
            down_time INTEGER, down_timer_duration INTEGER,
            protection_circle_active INTEGER, protection_circle_radius INTEGER,
            protection_timer INTEGER, protection_duration INTEGER,
            revive_progress INTEGER, revive_duration INTEGER, being_revived INTEGER,
            invulnerability_time INTEGER, invulnerability_duration INTEGER,
            last_fire_time INTEGER, last_damage_time INTEGER,
            drone_json TEXT,
            type TEXT,
            color TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS zombie (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_x REAL, position_y REAL, strength INTEGER,
            health INTEGER, max_health INTEGER, speed REAL, size INTEGER,
            last_attack_time INTEGER, active INTEGER,
            type TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS world_object (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_x REAL, position_y REAL,
            size_x REAL, size_y REAL,
            type TEXT, color TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS powerup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_x REAL, position_y REAL, type TEXT,
            size INTEGER, active INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS meta (
            id INTEGER PRIMARY KEY,
            mode TEXT, camera_x REAL, camera_y REAL,
            game_time INTEGER, zombies_killed INTEGER, current_day INTEGER,
            is_night INTEGER, zombie_strength INTEGER,
            last_zombie_spawn INTEGER, next_power_up_time INTEGER,
            loaded_chunks TEXT,
            zombie_kills_by_type TEXT
        )
    ''')
    conn.commit()


def save_game(game, save_name, game_mode):
    db_path = get_save_path(save_name)
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("DELETE FROM player")
        c.execute("DELETE FROM zombie")
        c.execute("DELETE FROM world_object")
        c.execute("DELETE FROM powerup")
        c.execute("DELETE FROM meta")
        conn.commit()
        conn.close()
    conn = sqlite3.connect(db_path)
    create_tables(conn)
    c = conn.cursor()

    # Playerlar (P1 va P2 uchun har doim id = 0, id = 1)
    for idx, player in enumerate(game.players):
        drone_json = None
        if player.drone:
            drone_json = json.dumps({
                "position": [player.drone.position.x, player.drone.position.y],
                "level": player.drone.level, "max_level": player.drone.max_level,
                "player_id": player.drone.player_id, "last_fire_time": player.drone.last_fire_time,
                "last_rocket_time": player.drone.last_rocket_time, "size": player.drone.size
            })
        player_type = "bot" if isinstance(player, HelperBot) else "player"
        player_color = list(getattr(player, "color", (200, 200, 200)))  # PATCH: for sikl ichiga o‘tkazildi
        c.execute('''
            INSERT INTO player VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                ?
            )
        ''', (
            idx,
            player.position.x, player.position.y,
            player.health, player.max_health, player.shield, player.max_shield,
            player.level, player.zombie_kills,
            player.weapon_type.name, player.ammo, player.state.name,
            player.down_time, player.down_timer_duration,
            int(player.protection_circle_active), player.protection_circle_radius,
            player.protection_timer, player.protection_duration,
            player.revive_progress, player.revive_duration, int(player.being_revived),
            player.invulnerability_time, player.invulnerability_duration,
            player.last_fire_time, player.last_damage_time,
            drone_json,
            player_type,
            json.dumps(player_color)
        ))

    # Zombielar
    for zombie in game.zombies:
        c.execute('''
            INSERT INTO zombie (
                position_x, position_y, strength, health, max_health, speed, size, last_attack_time, active, type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            zombie.position.x, zombie.position.y, zombie.strength, zombie.health, zombie.max_health,
            zombie.speed, zombie.size, zombie.last_attack_time, int(zombie.active), zombie.type.value
        ))

    # World Objects
    for obj in game.world.objects:
        c.execute('''
            INSERT INTO world_object (
                position_x, position_y, size_x, size_y, type, color
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            obj.position.x, obj.position.y, obj.size.x, obj.size.y, obj.type, json.dumps(list(obj.color))
        ))

    # PowerUps
    for p in game.world.power_ups:
        c.execute('''
            INSERT INTO powerup (
                position_x, position_y, type, size, active
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            p.position.x, p.position.y, p.type, p.size, int(p.active)
        ))

    # Meta/statistika
    c.execute('''
        INSERT INTO meta VALUES (
            1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    ''', (
        game.mode.name,
        game.camera.x, game.camera.y,
        game.game_time, game.zombies_killed, game.current_day,
        int(game.is_night), game.zombie_strength,
        game.last_zombie_spawn, game.next_power_up_time,
        json.dumps(list(game.world.loaded_chunks)),
        json.dumps(getattr(game, "zombie_kills_by_type", {}))
    ))

    conn.commit()
    conn.close()
    print(f"[INFO] O'yin '{save_name}' DB holatda saqlandi: {db_path}")


def load_last_session():
    db_path = AUTOSAVE_PATH
    if not os.path.exists(db_path):
        return None
    return load_game_data(GameMode.Offline, "autosave")

def delete_last_session_files():
    for path in [SAVE_ROOT, AUTOSAVE_PATH]:
        if os.path.exists(path):
            for _ in range(3):
                try:
                    os.remove(path)
                    print(f"[INFO] Last session fayl o'chirildi: {path}")
                    break
                except PermissionError:
                    print(f"[WARN] Faylni o‘chirishda xatolik, 0.3s kutiladi: {path}")
                    time.sleep(0.3)
                except Exception as e:
                    print(f"[ERROR] Faylni o‘chirishda boshqa xatolik: {path} {e}")
                    break

def try_load_game_any_mode(save_name):
    for mode in [GameMode.Offline, GameMode.Online]:
        db_path = get_save_path(save_name)
        if os.path.exists(db_path):
            data = load_game_data(mode, save_name)
            if data is not None:
                print(f"[INFO] Save '{save_name}' {mode.name} rejimida ochildi!")
                return data, mode
    print(f"[ERROR] '{save_name}' nomli save fayli topilmadi yoki mos kelmadi!")
    return None, None

def load_game_data(save_name, progress_callback=None):
    db_path = get_save_path(save_name)
    print("[DEBUG] DB path:", db_path)
    print("[DEBUG] File exists:", os.path.exists(db_path))
    if not os.path.exists(db_path):
        print("[ERROR] Save fayl topilmadi:", db_path)
        return None

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    data = {}
    # Progress uchun
    total = 5
    step = 0

    # Meta
    meta = c.execute('SELECT * FROM meta WHERE id=1').fetchone()
    print("[DEBUG] meta row:", meta)
    if meta is None:
        print("[ERROR] meta jadvali bo‘sh yoki saqlashda xatolik bo‘ldi!")
        conn.close()
        return None
    (
        _, mode, camera_x, camera_y, game_time, zombies_killed, current_day,
        is_night, zombie_strength, last_zombie_spawn, next_power_up_time,
        loaded_chunks_json, zombie_kills_by_type_json
    ) = meta
    data["meta"] = {
        "mode": mode,
        "camera": [camera_x, camera_y],
        "game_time": game_time,
        "zombies_killed": zombies_killed,
        "current_day": current_day,
        "is_night": bool(is_night),
        "zombie_strength": zombie_strength,
        "last_zombie_spawn": last_zombie_spawn,
        "next_power_up_time": next_power_up_time,
    }
    try:
        data["meta"]["zombie_kills_by_type"] = json.loads(
            zombie_kills_by_type_json) if zombie_kills_by_type_json else {}
    except Exception:
        data["meta"]["zombie_kills_by_type"] = {}
    try:
        data["meta"]["loaded_chunks"] = json.loads(loaded_chunks_json)
    except Exception:
        data["meta"]["loaded_chunks"] = []

    step += 1
    if progress_callback:
        progress_callback(int(step * 100 / total))

    # Playerlar (always ordered by id for multiplayer)
    player_data = []
    player_rows = c.execute('SELECT * FROM player ORDER BY id ASC').fetchall()
    print("[DEBUG] player rows:", player_rows)
    for row in player_rows:
        (
            pid, px, py, health, max_health, shield, max_shield, level, zombie_kills,
            weapon_type, ammo, state, down_time, down_timer_duration,
            protection_circle_active, protection_circle_radius, protection_timer, protection_duration,
            revive_progress, revive_duration, being_revived,
            invulnerability_time, invulnerability_duration, last_fire_time, last_damage_time,
            drone_json
        ) = row
        pdata = {
            "id": pid,
            "position": [px, py],
            "health": health,
            "max_health": max_health,
            "shield": shield,
            "max_shield": max_shield,
            "level": level,
            "zombie_kills": zombie_kills,
            "weapon_type": weapon_type,
            "ammo": ammo,
            "state": state,
            "down_time": down_time,
            "down_timer_duration": down_timer_duration,
            "protection_circle_active": bool(protection_circle_active),
            "protection_circle_radius": protection_circle_radius,
            "protection_timer": protection_timer,
            "protection_duration": protection_duration,
            "revive_progress": revive_progress,
            "revive_duration": revive_duration,
            "being_revived": bool(being_revived),
            "invulnerability_time": invulnerability_time,
            "invulnerability_duration": invulnerability_duration,
            "last_fire_time": last_fire_time,
            "last_damage_time": last_damage_time,
            "drone": json.loads(drone_json) if drone_json else None,
        }
        player_data.append(pdata)
    data["player"] = player_data
    step += 1
    if progress_callback:
        progress_callback(int(step * 100 / total))

    # Zombielar
    zombies_data = []
    for row in c.execute('SELECT * FROM zombie').fetchall():
        (
            _, px, py, strength, health, max_health, speed, size,
            last_attack_time, active, ztype_str
        ) = row
        ztype = ZombieType(ztype_str) if ztype_str else ZombieType.WALKER
        zombies_data.append({
            "position": [px, py],
            "strength": strength,
            "health": health,
            "max_health": max_health,
            "speed": speed,
            "size": size,
            "last_attack_time": last_attack_time,
            "active": bool(active),
            "type": ztype.value
        })
    data["zombies"] = zombies_data
    step += 1
    if progress_callback:
        progress_callback(int(step * 100 / total))

    # World Objects
    world_objects_data = []
    for row in c.execute('SELECT * FROM world_object').fetchall():
        _, px, py, sx, sy, otype, color = row
        color_tuple = json.loads(color)
        world_objects_data.append({
            "position": [px, py],
            "size": [sx, sy],
            "type": otype,
            "color": color_tuple
        })
    data["worldObjects"] = world_objects_data
    step += 1
    if progress_callback:
        progress_callback(int(step * 100 / total))

    # PowerUps va loaded_chunks
    power_ups_data = []
    for row in c.execute('SELECT * FROM powerup').fetchall():
        _, px, py, ptype, size, active = row
        power_ups_data.append({
            "position": [px, py],
            "type": ptype,
            "size": size,
            "active": bool(active)
        })
    world = {}
    world["power_ups"] = power_ups_data
    world["loaded_chunks"] = data.get("meta", {}).get("loaded_chunks", [])
    data["world"] = world

    step += 1
    if progress_callback:
        progress_callback(int(step * 100 / total))

    conn.close()
    return data

def load_from_data(game, data):
    # --- Playerlar ---
    game.players.clear()
    player_data = data.get("player", [])
    player_data = sorted(player_data, key=lambda pd: pd.get("id", 0))
    for idx, pdata in enumerate(player_data):
        player_type = pdata.get("type", "player")
        color = tuple(pdata.get("color", [200, 200, 200]))
        if player_type == "bot":
            player = HelperBot(Vector2(*safe_get(pdata, "position", [0, 0])), safe_int(safe_get(pdata, "id", idx)), color=color)
        else:
            player = Player(Vector2(*safe_get(pdata, "position", [0, 0])), safe_int(safe_get(pdata, "id", idx)), color=color)
        player.id = safe_int(safe_get(pdata, "id", idx))
        player.health = safe_int(safe_get(pdata, "health", 100))
        player.max_health = safe_int(safe_get(pdata, "max_health", 100))
        player.shield = safe_int(safe_get(pdata, "shield", 0))
        player.max_shield = safe_int(safe_get(pdata, "max_shield", 100))
        player.level = safe_int(safe_get(pdata, "level", 1))
        player.zombie_kills = safe_int(safe_get(pdata, "zombie_kills", 0))
        player.weapon_type = safe_enum(WeaponType, safe_get(pdata, "weapon_type", "PISTOL"), WeaponType.PISTOL)
        player.state = safe_enum(PlayerState, safe_get(pdata, "state", "ALIVE"), PlayerState.ALIVE)
        player.down_time = safe_int(safe_get(pdata, "down_time", 0))
        player.ammo = safe_int(safe_get(pdata, "ammo", 0))
        player.down_timer_duration = safe_int(safe_get(pdata, "down_timer_duration", 60000))
        player.protection_circle_active = safe_bool(safe_get(pdata, "protection_circle_active", False))
        player.protection_circle_radius = safe_int(safe_get(pdata, "protection_circle_radius", 60))
        player.protection_timer = safe_int(safe_get(pdata, "protection_timer", 0))
        player.protection_duration = safe_int(safe_get(pdata, "protection_duration", 10000))
        player.revive_progress = safe_int(safe_get(pdata, "revive_progress", 0))
        player.revive_duration = safe_int(safe_get(pdata, "revive_duration", 5000))
        player.being_revived = safe_bool(safe_get(pdata, "being_revived", False))
        player.invulnerability_time = safe_int(safe_get(pdata, "invulnerability_time", 0))
        player.invulnerability_duration = safe_int(safe_get(pdata, "invulnerability_duration", 3000))
        player.last_fire_time = safe_int(safe_get(pdata, "last_fire_time", 0))
        player.last_damage_time = safe_int(safe_get(pdata, "last_damage_time", 0))
        # Drone
        drone_data = safe_get(pdata, "drone", None)
        if drone_data:
            drone = Drone(
                Vector2(*safe_get(drone_data, "position", [0, 0])),
                safe_int(safe_get(drone_data, "player_id", player.id))
            )
            drone.level = safe_int(safe_get(drone_data, "level", 1))
            drone.max_level = safe_int(safe_get(drone_data, "max_level", 1))
            drone.last_fire_time = safe_int(safe_get(drone_data, "last_fire_time", 0))
            drone.last_rocket_time = safe_int(safe_get(drone_data, "last_rocket_time", 0))
            drone.size = safe_int(safe_get(drone_data, "size", 20))
            player.drone = drone
        game.players.append(player)
    if len(game.players) > 1:
        game.players.sort(key=lambda p: p.id)

    # --- Zombielar ---
    game.zombies.clear()
    zombies_data = data.get("zombies", [])
    for zdata in zombies_data:
        ztype = safe_enum(ZombieType, zdata.get("type", "Walker"), ZombieType.WALKER)
        zombie = Zombie(Vector2(*safe_get(zdata, "position", [0, 0])), safe_int(safe_get(zdata, "strength", 1)), ztype)
        zombie.health = safe_int(safe_get(zdata, "health", 20))
        zombie.max_health = safe_int(safe_get(zdata, "max_health", 20))
        zombie.speed = safe_int(safe_get(zdata, "speed", 50))
        zombie.size = safe_int(safe_get(zdata, "size", 20))
        zombie.last_attack_time = safe_int(safe_get(zdata, "last_attack_time", 0))
        zombie.active = safe_bool(safe_get(zdata, "active", True))
        game.zombies.append(zombie)

    # --- World, worldObjects va powerups ---
    world_data = data.get("world", {})
    game.world = World()

    # PowerUps
    game.world.power_ups.clear()
    for p in world_data.get("power_ups", []):
        powerup = PowerUp(Vector2(*safe_get(p, "position", [0, 0])), safe_get(p, "type", "unknown"), size=safe_int(safe_get(p, "size", 20)))
        powerup.active = safe_bool(safe_get(p, "active", True))
        game.world.power_ups.append(powerup)
    # loaded_chunks
    game.world.loaded_chunks = set(world_data.get("loaded_chunks", []))

    # WorldObjects
    game.world.objects.clear()
    world_objects_data = data.get("worldObjects", [])
    for o in world_objects_data:
        obj = WorldObject(
            Vector2(*safe_get(o, "position", [0, 0])),
            Vector2(*safe_get(o, "size", [20, 20])),
            safe_get(o, "type", "unknown"),
            tuple(safe_get(o, "color", [255, 255, 255]))
        )
        game.world.objects.append(obj)

    # --- General game meta/statistika ---
    meta = data.get("meta", {})
    try:
        game.mode = safe_enum(GameMode, meta.get("mode", "Offline"), GameMode.Offline)
    except Exception:
        game.mode = GameMode.Offline
    if "zombie_kills_by_type" in meta:
        game.zombie_kills_by_type = meta["zombie_kills_by_type"]

    print("[DEBUG] load_from_data: mode:", game.mode)
    print("[DEBUG] load_from_data: players:", len(game.players), [p.id for p in game.players])
    game.camera = Vector2(*meta.get("camera", [0, 0]))
    game.game_time = meta.get("game_time", 0)
    game.zombies_killed = meta.get("zombies_killed", 0)
    game.current_day = meta.get("current_day", 1)
    game.is_night = meta.get("is_night", False)
    game.zombie_strength = meta.get("zombie_strength", 1)

    # Timers
    game.last_zombie_spawn = pygame.time.get_ticks()
    game.next_power_up_time = pygame.time.get_ticks() + 5000
    game.game_start_time = pygame.time.get_ticks()

    print("Players loaded:", len(game.players))
    print("Zombies loaded:", len(game.zombies))
    print("World objects loaded:", len(game.world.objects))

def list_saved_games():
    files = [f for f in os.listdir(SAVE_ROOT) if f.endswith('.db')]
    return [f[:-3] for f in files]


def delete_save(save_name):
    db_path = get_save_path(save_name)
    if save_name == "autosave":
        print("[ERROR] Avtosave faylini o'chirib bo'lmaydi!")
        return
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[INFO] Save fayl o'chirildi: {db_path}")