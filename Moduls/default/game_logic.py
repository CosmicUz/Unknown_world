import random
import math
import pygame
from core import Vector2, GameState, PlayerState, WeaponType
from Moduls.default.player import Player
from Moduls.default.helper_bot import HelperBot
from Moduls.default.world import World
from Moduls.default.zombie import Zombie, ZombieType

ZOMBIE_TYPE_WEIGHTS = {
    ZombieType.WALKER: 0.6,
    ZombieType.RUNNER: 0.3,
    ZombieType.TANKER: 0.1
}

def setup_players(game, selected_slots):
    player_colors = {
        1: (20, 120, 255),
        2: (220, 40, 40),
        101: (60, 180, 70),
        102: (220, 220, 40),
        103: (30, 30, 30),
        104: (255, 255, 255),
    }
    player_controls = {
        1: {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a, 'right': pygame.K_d, 'shoot': [pygame.K_f, pygame.K_SPACE]},
        2: {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT, 'shoot': [pygame.K_k]},
    }
    slot_spawns = {0: Vector2(-50, 50), 1: Vector2(50, 50), 2: Vector2(-50, -50), 3: Vector2(50, -50)}
    slot_ids = ['s1', 's2', 's3', 's4']

    game.players.clear()
    for slot in selected_slots:
        color = player_colors.get(slot['id'], (200, 200, 200))
        controls = player_controls.get(slot['id'], {}) if slot['type'] == 'player' else {}
        spawn_pos = slot_spawns.get(selected_slots.index(slot), Vector2(0, 0))
        slot_id = slot_ids[selected_slots.index(slot)] if selected_slots.index(slot) < len(slot_ids) else f"s{selected_slots.index(slot)+1}"
        if slot['type'] == 'player':
            p = Player(spawn_pos, slot['id'], color=color, controls=controls)
            p.slot_id = slot_id
            game.players.append(p)
        elif slot['type'] == 'bot':
            b = HelperBot(spawn_pos, slot['id'], color=color)
            b.slot_id = slot_id
            bot_count = sum(1 for s in selected_slots if s['type'] == 'bot')
            if bot_count > 1:
                if selected_slots.index(slot) == 0:
                    b.is_leader = True
                    b.leader_id = None
                else:
                    b.is_leader = False
                    b.leader_id = selected_slots[0]['id']
            else:
                b.is_leader = True
                b.leader_id = None
            game.players.append(b)
    player_count = sum(1 for slot in selected_slots if slot['type'] == 'player')
    bot_count = sum(1 for slot in selected_slots if slot['type'] == 'bot')
    total = player_count + bot_count
    can_go_down = total >= 2
    multi_player_mode = total >= 2
    for p in game.players:
        p.can_go_down = can_go_down
        p.multi_player_mode = multi_player_mode

def setup_world(game):
    game.zombies.clear()
    game.bullets.clear()
    game.world = World()
    game.zombies_killed = 0
    game.current_day = 1
    game.is_night = False
    game.zombie_strength = 1

def update(game, dt):
    update_day_night_cycle(game)
    update_players(game, dt)
    update_zombies(game, dt)
    update_bullets(game, dt)
    spawn_zombies(game)
    spawn_power_ups(game)
    check_collisions(game)
    game.update_camera()
    game.check_game_over()

def update_day_night_cycle(game):
    day_length = 15 * 60 * 1000
    day_progress = (game.game_time % day_length) / day_length
    new_day = (game.game_time // day_length) + 1
    if new_day != game.current_day:
        game.current_day = new_day
        if game.current_day % 7 == 0:
            game.zombie_strength += 1
    game.is_night = day_progress >= 8 / 15

def update_players(game, dt):
    alive_positions = [p.position for p in game.players if p.state == PlayerState.ALIVE]
    for player in game.players:
        if player.state != PlayerState.DEAD:
            other_players = [p for p in game.players if p.id != player.id]
            new_bullets = player.update(dt, game.world.power_ups, game.zombies, other_players)
            game.bullets.extend(new_bullets)
    game.world.update(alive_positions)

def update_zombies(game, dt):
    alive_positions = [p.position for p in game.players if p.state == PlayerState.ALIVE]
    protection_circles = [p.get_protection_circle_info() for p in game.players]
    for zombie in game.zombies[:]:
        if not zombie.active:
            game.zombies.remove(zombie)
            continue
        zombie.update(dt, alive_positions, protection_circles)
        for player in game.players:
            if player.state != PlayerState.ALIVE:
                continue
            distance = (zombie.position - player.position).length()
            if distance < 25 and zombie.can_attack(pygame.time.get_ticks()):
                damage = zombie.attack(pygame.time.get_ticks())
                player.take_damage(damage)

def update_bullets(game, dt):
    for bullet in game.bullets[:]:
        if not bullet.active:
            game.bullets.remove(bullet)
            continue
        bullet.update(dt)

def spawn_zombies(game):
    current_time = pygame.time.get_ticks()
    spawn_rate = 1200
    if game.is_night:
        spawn_rate *= 0.4
        if random.random() < 0.3:
            spawn_zombie(game)
    max_level = max((p.level for p in game.players), default=1)
    if max_level >= 100:
        spawn_rate *= 0.3
    if current_time - game.last_zombie_spawn >= spawn_rate:
        spawn_zombie(game)
        if random.random() < 0.25:
            spawn_zombie(game)
        game.last_zombie_spawn = current_time

def spawn_zombie(game):
    alive_players = [p for p in game.players if p.state == PlayerState.ALIVE]
    if not alive_players:
        return
    target_player = random.choice(alive_players)
    angle = random.random() * 2 * math.pi
    distance = 400 + random.random() * 200
    spawn_pos = Vector2(
        target_player.position.x + math.cos(angle) * distance,
        target_player.position.y + math.sin(angle) * distance
    )
    zombie_types = list(ZOMBIE_TYPE_WEIGHTS.keys())
    weights = list(ZOMBIE_TYPE_WEIGHTS.values())
    ztype = random.choices(zombie_types, weights=weights, k=1)[0]
    game.zombies.append(Zombie(spawn_pos, game.zombie_strength, ztype))

def spawn_power_ups(game):
    current_time = pygame.time.get_ticks()
    if current_time >= game.next_power_up_time:
        kills_for_power_up = 10 + random.randint(0, 10)
        if game.zombies_killed >= kills_for_power_up:
            alive_players = [p for p in game.players if p.state == PlayerState.ALIVE]
            if alive_players:
                random_player = random.choice(alive_players)
                needs_power_up = (random_player.health < random_player.max_health or
                                  (random_player.level >= 10 and random_player.shield < random_player.max_shield))
                if needs_power_up:
                    offset = Vector2(
                        (random.random() - 0.5) * 200,
                        (random.random() - 0.5) * 200
                    )
                    game.world.add_power_up(random_player.position + offset)
            game.zombies_killed = 0
            game.next_power_up_time = current_time + (10 + random.random() * 10) * 1000

def check_collisions(game):
    for bullet in game.bullets[:]:
        if not bullet.active:
            continue
        for zombie in game.zombies[:]:
            if not zombie.active:
                continue
            distance = (bullet.position - zombie.position).length()
            if distance < 15:
                killed = zombie.take_damage(bullet.damage)
                if killed:
                    game.zombies_killed += 1
                    if hasattr(game, "zombie_kills_by_type"):
                        ztype = getattr(zombie, "type", None)
                        if ztype is not None:
                            game.zombie_kills_by_type[getattr(zombie, "type").value] += 1
                    player = next((p for p in game.players if p.id == bullet.player_id), None)
                    if player:
                        player.add_zombie_kill()
                bullet.active = False
                break
    for player in game.players:
        if player.state != PlayerState.ALIVE:
            continue
        for power_up in game.world.power_ups[:]:
            if not power_up.active:
                continue
            distance = (player.position - power_up.position).length()
            if distance < 20:
                player.collect_power_up()
                power_up.active = False
                game.world.power_ups.remove(power_up)

def render(game):
    game.world.render(game.screen, game.camera, game.screen_width, game.screen_height)
    for zombie in game.zombies:
        zombie.render(game.screen, game.camera)
    for bullet in game.bullets:
        bullet.render(game.screen, game.camera)
    for player in game.players:
        player.render(game.screen, game.camera)
    if game.is_night:
        night_surface = pygame.Surface((game.screen_width, game.screen_height))
        night_surface.fill((0, 0, 50))
        night_surface.set_alpha(100)
        game.screen.blit(night_surface, (0, 0))
    game.render_hud()