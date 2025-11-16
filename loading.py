import pygame
from Moduls.default.player import Player
from core import Vector2
from Moduls.default.helper_bot import HelperBot
from Moduls.default.world import World
import os
import importlib.util


def load_game_logic(modul_name):
    module_fullname = f"Moduls.{modul_name}.game_logic"
    try:
        game_logic = importlib.import_module(module_fullname)
        return game_logic
    except Exception as e:
        print(f"[loading.py] ERROR loading game logic modul: {modul_name}: {e}")
        if modul_name != "default":
            try:
                return importlib.import_module("Moduls.default.game_logic")
            except Exception as e2:
                print(f"[loading.py] ERROR fallback to default game_logic: {e2}")
        raise

class LoadingScreen:
    def __init__(self, screen, width, height, font=None, small_font=None):
        self.screen = screen
        self.width = width
        self.height = height
        self.font = font or pygame.font.Font(None, 48)
        self.small_font = small_font or pygame.font.Font(None, 24)
        self.text = "Loading..."
        self.percent = 0

    @staticmethod
    def start_game_from_loading(game, selected_slots, selected_modul="default", save_data=None):
        game_logic_module = load_game_logic(selected_modul)
        game.logic = game_logic_module

        try:
            game_logic_module = load_game_logic(selected_modul if selected_modul else "default")
        except Exception as e:
            print(f"[Loading] error loading game logic for modul {selected_modul}: {e}")
            game_logic_module = load_game_logic("default")
        game.logic = game_logic_module

        if hasattr(game.logic, "setup_players"):
            game.logic.setup_players(game, selected_slots)
        else:
            player_colors = {
                1: (20, 120, 255),
                2: (220, 40, 40),
                101: (60, 180, 70),
                102: (220, 220, 40),
                103: (30, 30, 30),
                104: (255, 255, 255),
            }
            player_controls = {
                1: {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a, 'right': pygame.K_d,
                    'shoot': [pygame.K_f, pygame.K_SPACE]},
                2: {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT,
                    'shoot': [pygame.K_k]},
            }
            slot_spawns = {
                0: Vector2(-50, 50),
                1: Vector2(50, 50),
                2: Vector2(-50, -50),
                3: Vector2(50, -50),
            }
            slot_ids = ['s1', 's2', 's3', 's4']
            game.players.clear()
            for slot in selected_slots:
                color = player_colors.get(slot['id'], (200, 200, 200))
                controls = player_controls.get(slot['id'], {}) if slot['type'] == 'player' else {}
                spawn_pos = slot_spawns.get(selected_slots.index(slot), Vector2(0, 0))
                slot_id = slot_ids[selected_slots.index(slot)] if selected_slots.index(slot) < len(
                    slot_ids) else f"s{selected_slots.index(slot) + 1}"
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

        if hasattr(game.logic, "setup_world"):
            game.logic.setup_world(game)
        else:
            game.zombies.clear()
            game.bullets.clear()
            game.world = World()
            game.zombies_killed = 0
            game.current_day = 1
            game.is_night = False
            game.zombie_strength = 1

    def set_text(self, text):
        self.text = text

    def set_percent(self, percent):
        self.percent = percent

    def render(self):
        self.screen.fill((20, 20, 20))
        text = self.font.render(self.text, True, (255, 255, 255))
        self.screen.blit(text, (self.width // 2 - text.get_width() // 2, 300))
        bar_x = self.width // 2 - 150
        bar_y = 400
        bar_width = 300
        bar_height = 30
        pygame.draw.rect(self.screen, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height))
        fill_width = int(bar_width * self.percent / 100)
        pygame.draw.rect(self.screen, (60, 180, 70), (bar_x, bar_y, fill_width, bar_height))
        percent_text = self.small_font.render(f"{self.percent}%", True, (255, 255, 255))
        self.screen.blit(percent_text, (self.width // 2 - percent_text.get_width() // 2, bar_y + bar_height + 10))
