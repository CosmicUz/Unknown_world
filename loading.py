import pygame
from Moduls.default.player import Player
from core import Vector2
from Moduls.default.helper_bot import HelperBot
from Moduls.default.world import World
import os
import importlib.util
import importlib


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
    def start_game_from_loading(screen, width, height, selected_slots, selected_modul="default", font=None, small_font=None, save_data=None):
        """
        Start actual module game by delegating to Moduls.<modul>.modul_loading -> that module will import
        the chosen `game_logic` and run its `run_game` entrypoint.
        """
        try:
            modul_name = selected_modul if selected_modul else "default"
            modul_loading_path = f"Moduls.{modul_name}.modul_loading"
            modul_loading = importlib.import_module(modul_loading_path)
        except Exception as e:
            print(f"[loading.py] ERROR importing modul_loading for {selected_modul}: {e}")
            # Fallback to default modul_loading if exists
            try:
                modul_loading = importlib.import_module("Moduls.default.modul_loading")
            except Exception as e2:
                print(f"[loading.py] ERROR fallback modul_loading: {e2}")
                raise

        try:
            # delegate starting the module game; modul_loading is expected to provide
            # `start_modul_game(screen, width, height, selected_slots, selected_modul)`
            modul_loading.start_modul_game(screen, width, height, selected_slots, selected_modul)
        except Exception as e:
            print(f"[loading.py] ERROR starting modul game: {e}")

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
