import os
import random
import sys
import threading

import pygame

from loading import LoadingScreen
from core import *
from Moduls.default.save_load import save_game, delete_save, list_saved_games, load_game_data, load_from_data, \
    save_last_session, AUTOSAVE_PATH
from Moduls.default.world import World
from Moduls.default.zombie import Zombie, ZombieType, ALL_ZOMBIE_TYPES

pygame.init()

ZOMBIE_TYPE_WEIGHTS = {
    ZombieType.WALKER: 0.6,
    ZombieType.RUNNER: 0.3,
    ZombieType.TANKER: 0.1
}

MODULS_PATH = os.path.join(os.path.dirname(__file__), 'Moduls')

def get_all_moduls():
    return [d for d in os.listdir(MODULS_PATH) if os.path.isdir(os.path.join(MODULS_PATH, d))]



class Game:
    def __init__(self, screen = None, screen_width = 1200, screen_height = 800):
        self.fullscreen = False
        self.screen_width = screen_width
        self.screen_height = screen_height
        if screen is not None:
            self.screen = screen
        else:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Zombie Survival Shooter")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.loading_screen = LoadingScreen(self.screen, self.screen_width, self.screen_height, self.font, self.small_font)
        self.save_input_active = False
        self.loading_active = False
        self.loading_done = False
        self.loading_percent = 0
        self.loading_text = ""
        self.loading_timer = 0
        self.loading_params = None
        self.save_input_text = ""
        self.show_save_success = False
        self.save_slot_full = False
        self.load_menu_active = False
        self.available_saves = []
        self.selected_save = None
        self.menu_mode_select = None
        self.menu_bg_green = False
        self.state = GameState.MAIN_MENU
        self.mode = GameMode.Offline
        self.players = []
        self.selected_slots = [{'type': 'player', 'id': 1, 'name': 'Player 1', 'pos_x': 0, 'pos_y': 0}]
        self.add_menu_active = False
        self.add_menu_slot_index = None
        self.available_add = [
            {'type': 'player', 'id': 1, 'name': 'Player 1'},
            {'type': 'player', 'id': 2, 'name': 'Player 2'},
            {'type': 'bot', 'id': 101, 'name': 'Bot 1'},
            {'type': 'bot', 'id': 102, 'name': 'Bot 2'},
            {'type': 'bot', 'id': 103, 'name': 'Bot 3'},
            {'type': 'bot', 'id': 104, 'name': 'Bot 4'},
        ]
        self.zombies = []
        self.bullets = []
        self.world = World()
        self.camera = Vector2(0, 0)
        # Game stats
        self.game_start_time = 0
        self.game_time = 0
        self.zombies_killed = 0
        self.current_day = 1
        self.is_night = False
        self.zombie_strength = 1
        self.last_zombie_spawn = 0
        self.next_power_up_time = 0
        self.zombie_kills_by_type = {ztype.value: 0 for ztype in ALL_ZOMBIE_TYPES}
        # Input state
        self.keys = set()
        self.mouse_pos = Vector2(0, 0)
        self.mouse_down = False
        self.menu_bg_green = False
        self.pause_bg_green = False
        self.selected_modul = "default"
        self.logic = None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if self.save_input_active:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.save_input_text:
                            save_game(self, self.save_input_text, self.mode) 
                            self.save_input_active = False
                            self.show_save_success = True
                            self.save_slot_full = False
                            self.pause_bg_green = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.save_input_text = self.save_input_text[:-1]
                    else:
                        if len(self.save_input_text) < 20 and event.unicode.isalnum():
                            self.save_input_text += event.unicode

                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_ESCAPE:
                        self.save_input_active = False
                        self.show_save_success = False
                        self.save_slot_full = False
                        self.pause_bg_green = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    center_x = self.screen_width // 2
                    y = 600
                    box_width = 300
                    save_btn_rect = pygame.Rect(center_x + box_width // 2 - 80, y, 70, 40)
                    if save_btn_rect.collidepoint(mx, my):
                        if self.save_input_text:
                            save_game(self, self.save_input_text, self.mode)  # PATCH: try_save_game o‘rniga save_game
                            self.save_input_active = False
                            self.show_save_success = True
                            self.save_slot_full = False
                            self.pause_bg_green = False
                    continue
            if getattr(self, "load_input_active", False):
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.load_input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.load_input_text = getattr(self, "load_input_text", "")[:-1]
                    else:
                        if len(getattr(self, "load_input_text", "")) < 20 and event.unicode.isalnum():
                            self.load_input_text = getattr(self, "load_input_text", "") + event.unicode
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
                    self.load_input_active = False
            elif self.load_menu_active:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if hasattr(self, "load_menu_btns") and self.load_menu_btns.get("input") and self.load_menu_btns["input"].collidepoint(event.pos):
                        self.load_input_active = True
                        return True
                    self.handle_load_menu_click(event.pos)
                    return True
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.load_menu_active = False
                    self.load_input_active = False
                    self.selected_save = None
                    self.menu_bg_green = False
                    return True

            # Klaviatura eventlari
            elif event.type == pygame.KEYDOWN:
                for p in self.players:
                        print(f"player: {self.players}")
                        if hasattr(p, 'controls'):
                            if event.key == p.controls.get('up'):
                                print(f"Key: {event.key}")
                                p.move_up = True
                            if event.key == p.controls.get('down'):
                                print(f"Key: {event.key}")
                                p.move_down = True
                            if event.key == p.controls.get('left'):
                                print(f"Key: {event.key}")
                                p.move_left = True
                            if event.key == p.controls.get('right'):
                                print(f"Key: {event.key}")
                                p.move_right = True
                            if 'shoot' in p.controls and event.key in p.controls['shoot']:
                                p.shooting = True
                self.keys.add(event.key)
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    print(f"Fullscreen: {self.fullscreen}")
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.PLAYING:
                        self.state = GameState.PAUSED
                    elif self.state == GameState.PAUSED:
                        self.state = GameState.PLAYING
                if self.state == GameState.PLAYING:
                    if event.key == pygame.K_SPACE and len(self.players) >= 1:
                        if self.players[0].state == PlayerState.ALIVE:
                            self.players[0].shooting = True
                    elif event.key == pygame.K_f and len(self.players) >= 1:
                        if self.players[0].state == PlayerState.ALIVE:
                            self.players[0].shooting = True
                    elif event.key == pygame.K_l and len(self.players) >= 2:
                        if self.players[1].state == PlayerState.ALIVE:
                            self.players[1].shooting = True

            elif event.type == pygame.KEYUP:
                for p in self.players:
                        if hasattr(p, 'controls'):
                            if event.key == p.controls.get('up'):
                                print(f"Key: {event.key}")
                                p.move_up = False
                            if event.key == p.controls.get('down'):
                                print(f"Key: {event.key}")
                                p.move_down = False
                            if event.key == p.controls.get('left'):
                                print(f"Key: {event.key}")
                                p.move_left = False
                            if event.key == p.controls.get('right'):
                                print(f"Key: {event.key}")
                                p.move_right = False
                            if 'shoot' in p.controls and event.key in p.controls['shoot']:
                                p.shooting = False
                self.keys.discard(event.key)
                if event.key == pygame.K_SPACE and len(self.players) >= 1:
                    self.players[0].shooting = False
                elif event.key == pygame.K_f and len(self.players) >= 1:
                    self.players[0].shooting = False
                elif event.key == pygame.K_l and len(self.players) >= 2:
                    self.players[1].shooting = False

            # Mouse eventlari
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.handle_mouse_click(event.pos)
        return True
    
    
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            info = pygame.display.Info()
            w, h = info.current_w, info.current_h
            print("Fullscreen:", w, h)
            self.screen_width, self.screen_height = w, h
        else:
            self.screen_width, self.screen_height = 1200, 800
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
    
    def update_camera(self):
        if not self.players:
            return
        alive_players = [p for p in self.players if p.state == PlayerState.ALIVE]
        downed_players = [p for p in self.players if p.state == PlayerState.DOWNED]
        total = len(self.players)
        if total == 1:
            target = self.players[0]
            self.camera.x = target.position.x - self.screen_width // 2
            self.camera.y = target.position.y - self.screen_height // 2
        elif alive_players:
            avg_x = sum(p.position.x for p in alive_players) / len(alive_players)
            avg_y = sum(p.position.y for p in alive_players) / len(alive_players)
            self.camera.x = avg_x - self.screen_width // 2
            self.camera.y = avg_y - self.screen_height // 2
        elif downed_players:
            avg_x = sum(p.position.x for p in downed_players) / len(downed_players)
            avg_y = sum(p.position.y for p in downed_players) / len(downed_players)
            self.camera.x = avg_x - self.screen_width // 2
            self.camera.y = avg_y - self.screen_height // 2


    def handle_pause_click(self, pos):
        x, y = pos
        center_x = self.screen_width // 2
        button_width = 150
        button_height = 50
        if center_x - button_width // 2 <= x <= center_x + button_width // 2 and 350 <= y <= 400:
            self.state = GameState.PLAYING
            self.pause_bg_green = False
            print("[INFO] O'yin davom etdi (Resume)")
        elif center_x - button_width // 2 <= x <= center_x + button_width // 2 and 420 <= y <= 470:
            if hasattr(self, "last_loaded_save_name") and self.last_loaded_save_name:
                self.start_loading(self.last_loaded_mode, self.last_loaded_save_name)
                self.state = GameState.PAUSED
            else:
                self.restart_game()
                self.state = GameState.PLAYING
            self.pause_bg_green = False
            print("[INFO] O'yin qayta boshlandi (Restart)")
        elif center_x - button_width // 2 <= x <= center_x + button_width // 2 and 490 <= y <= 540:
            self.save_input_active = True
            self.save_input_text = ""
            self.pause_bg_green = True
            print(f"[INFO] Saqlandi.{self.save_input_text}")
        elif center_x - button_width // 2 <= x <= center_x + button_width // 2 and 560 <= y <= 610:
            save_last_session(self) 
            self.state = GameState.MAIN_MENU
            self.pause_bg_green = False
            print("[INFO] Asosiy menyuga qaytildi")

    def handle_game_over_click(self, pos):
        x, y = pos
        center_x = self.screen_width // 2
        button_width = 150
        button_height = 50
        play_again_x = center_x - 100
        if (play_again_x <= x <= play_again_x + button_width and
                500 <= y <= 500 + button_height):
            self.restart_game()
            return
        main_menu_x = center_x + 100 - button_width
        if (main_menu_x <= x <= main_menu_x + button_width and
                500 <= y <= 500 + button_height):
            self.state = GameState.MAIN_MENU
            return

    def restart_game(self):
        print("[INFO] O'yin qayta boshlandi")
        self.start_game(self.mode)

    def update(self):
        if self.loading_active:
            self.update_loading()
            if self.loading_done:
                if pygame.time.get_ticks() - self.loading_timer > 1000:
                    self.loading_active = False
                    self.loading_done = False
                    self.state = GameState.PLAYING
                    self.game_start_time = pygame.time.get_ticks()
            return
        if self.state != GameState.PLAYING:
            return
        dt = self.clock.get_time() / 1000.0
        self.game_time = pygame.time.get_ticks() - self.game_start_time
        if self.logic and hasattr(self.logic, "update"):
            self.logic.update(self, dt)
        else:
            pass

    def update_day_night_cycle(self):
        day_length = 15 * 60 * 1000
        day_progress = (self.game_time % day_length) / day_length
        new_day = (self.game_time // day_length) + 1
        if new_day != self.current_day:
            self.current_day = new_day
            if self.current_day % 7 == 0:
                self.zombie_strength += 1
        self.is_night = day_progress >= 8 / 15

    def update_players(self, dt):
        prev = getattr(self, "_last_players", 0)
        if len(self.players) != prev:
            print(f"[INFO] Players soni o'zgardi: {len(self.players)}")
            self._last_players = len(self.players)
        alive_positions = [p.position for p in self.players if p.state == PlayerState.ALIVE]
        for player in self.players:
            if player.state != PlayerState.DEAD:
                other_players = [p for p in self.players if p.id != player.id]
                new_bullets = player.update(dt, self.world.power_ups, self.zombies, other_players)
                self.bullets.extend(new_bullets)
        self.world.update(alive_positions)

    def update_zombies(self, dt):
        alive_positions = [p.position for p in self.players if p.state == PlayerState.ALIVE]
        protection_circles = [p.get_protection_circle_info() for p in self.players]
        for zombie in self.zombies[:]:
            if not zombie.active:
                self.zombies.remove(zombie)
                continue
            zombie.update(dt, alive_positions, protection_circles)
            for player in self.players:
                if player.state != PlayerState.ALIVE:
                    continue
                distance = (zombie.position - player.position).length()
                if distance < 25 and zombie.can_attack(pygame.time.get_ticks()):
                    damage = zombie.attack(pygame.time.get_ticks())
                    player.take_damage(damage)

    def update_bullets(self, dt):
        for bullet in self.bullets[:]:
            if not bullet.active:
                self.bullets.remove(bullet)
                continue
            bullet.update(dt)

    def spawn_zombies(self):
        current_time = pygame.time.get_ticks()
        spawn_rate = 1200
        if self.is_night:
            spawn_rate *= 0.4
            if random.random() < 0.3:
                self.spawn_zombie()
        max_level = max((p.level for p in self.players), default=1)
        if max_level >= 100:
            spawn_rate *= 0.3
        if current_time - self.last_zombie_spawn >= spawn_rate:
            self.spawn_zombie()
            if random.random() < 0.25:
                self.spawn_zombie()
            self.last_zombie_spawn = current_time

    def spawn_zombie(self):
        alive_players = [p for p in self.players if p.state == PlayerState.ALIVE]
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
        self.zombies.append(Zombie(spawn_pos, self.zombie_strength, ztype))

    def spawn_power_ups(self):
        current_time = pygame.time.get_ticks()
        if current_time >= self.next_power_up_time:
            kills_for_power_up = 10 + random.randint(0, 10)
            if self.zombies_killed >= kills_for_power_up:
                alive_players = [p for p in self.players if p.state == PlayerState.ALIVE]
                if alive_players:
                    random_player = random.choice(alive_players)
                    needs_power_up = (random_player.health < random_player.max_health or
                                      (random_player.level >= 10 and random_player.shield < random_player.max_shield))
                    if needs_power_up:
                        offset = Vector2(
                            (random.random() - 0.5) * 200,
                            (random.random() - 0.5) * 200
                        )
                        self.world.add_power_up(random_player.position + offset)
                self.zombies_killed = 0
                self.next_power_up_time = current_time + (10 + random.random() * 10) * 1000

    def check_collisions(self):
        for bullet in self.bullets[:]:
            if not bullet.active:
                continue
            for zombie in self.zombies[:]:
                if not zombie.active:
                    continue
                distance = (bullet.position - zombie.position).length()
                if distance < 15:
                    killed = zombie.take_damage(bullet.damage)
                    if killed:
                        self.zombies_killed += 1
                        if hasattr(self, "zombie_kills_by_type"):
                            ztype = getattr(zombie, "type", None)
                            if ztype is not None:
                                self.zombie_kills_by_type[getattr(zombie, "type").value] += 1
                        player = next((p for p in self.players if p.id == bullet.player_id), None)
                        if player:
                            player.add_zombie_kill()
                    bullet.active = False
                    break
        for player in self.players:
            if player.state != PlayerState.ALIVE:
                continue
            for power_up in self.world.power_ups[:]:
                if not power_up.active:
                    continue
                distance = (player.position - power_up.position).length()
                if distance < 20:
                    player.collect_power_up()
                    power_up.active = False
                    self.world.power_ups.remove(power_up)
    def handle_mouse_click(self, pos):
        if self.state == GameState.MAIN_MENU:
            center_x = self.screen_width // 2
            button_width = 260
            button_height = 70
            gap = 40
            start_y = 320
            play_rect = pygame.Rect(center_x - button_width // 2, start_y, button_width, button_height)
            multi_rect = pygame.Rect(center_x - button_width // 2, start_y + button_height + gap, button_width, button_height)
            exit_rect = pygame.Rect(center_x - button_width // 2, start_y + 2 * (button_height + gap), button_width, button_height)
            mx, my = pos
            if play_rect.collidepoint(mx, my):
                self.state = GameState.PLAY_MENU
                self.menu_bg_color = (70, 160, 230)
            elif multi_rect.collidepoint(mx, my):
                pass  
            elif exit_rect.collidepoint(mx, my):
                pygame.quit()
                sys.exit()
        elif self.state == GameState.PLAY_MENU:
            self.handle_play_menu_click(pos)
        elif self.state == GameState.LOAD_MENU:
            self.handle_load_menu_click(pos)
        elif self.state == GameState.PAUSED:
            self.handle_pause_click(pos)
        elif self.state == GameState.GAME_OVER:
            self.handle_game_over_click(pos)

    def handle_play_menu_click(self, pos):
        if self.add_menu_active:
            for obj, slot_rect in self.add_menu_rects:
                if slot_rect.collidepoint(pos):
                    if not any(s['id'] == obj['id'] for s in self.selected_slots):
                        if obj['type'] == 'player' and sum(1 for s in self.selected_slots if s['type'] == 'player') < 2:
                            self.selected_slots.append({'type': 'player', 'id': obj['id'], 'name': obj['name'], 'pos_x': 0, 'pos_y': 0})
                        elif obj['type'] == 'bot' and sum(1 for s in self.selected_slots if s['type'] == 'bot') < 4:
                            self.selected_slots.append({'type': 'bot', 'id': obj['id'], 'name': obj['name'], 'pos_x': 0, 'pos_y': 0})
                    self.add_menu_active = False
                    return
            self.add_menu_active = False
            return
        # Modul tugmalarini aniqlash
        for modul_name, modul_rect in self.modul_btn_rects:
            if modul_rect.collidepoint(pos):
                self.selected_modul = modul_name
                return

        # X tugmasi bosilganini aniqlash
        for i, x_rect in self.x_buttons_rects:
            if x_rect.collidepoint(pos):
                del self.selected_slots[i]
                return

        # Add tugmasi bosilganini aniqlash
        for i, add_rect in self.add_buttons_rects:
            if add_rect.collidepoint(pos):
                self.add_menu_active = True
                self.add_menu_slot_index = i
                return

        # Start, Load, Back tugmalari
        if self.play_menu_buttons['start'].collidepoint(pos):
            if not self.selected_slots:
                self.selected_slots.append({'type': 'player', 'id': 1, 'name': 'Player 1', 'pos_x': 0, 'pos_y': 0})
            if len(self.selected_slots) > 0:
                self.state = GameState.LOADING
                self.loading_screen.set_text("Loading...")
                self.loading_screen.set_percent(0)
                self.loading_selected_slots = list(self.selected_slots)
                self.loading_selected_modul = self.selected_modul
                self.loading_timer = pygame.time.get_ticks()
                self.loading_active = True
                self.loading_done = False
                threading.Thread(target=self._do_loading_from_slots, daemon=True).start()
                return
        elif self.play_menu_buttons['load'].collidepoint(pos):
            self.state = GameState.LOAD_MENU
        elif self.play_menu_buttons['back'].collidepoint(pos):
            self.state = GameState.MAIN_MENU
            self.menu_bg_color = (45, 80, 22)

    def handle_load_menu_click(self, pos):
        for save_name, slot_rect in self.load_menu_slots_rects:
            if slot_rect.collidepoint(pos):
                self.selected_save = save_name
                print(f"[DEBUG] Selected save: {save_name}")
                return  
        if self.load_menu_btns["delete"].collidepoint(pos):
            name = getattr(self, "selected_save", None)
            if name and name != "autosave":
                delete_save(name)
                self.selected_save = None
            return

        if self.load_menu_btns["load"].collidepoint(pos):
            name = getattr(self, "selected_save", None)
            if name and name in list_saved_games():
                if name == "autosave" and not os.path.exists(AUTOSAVE_PATH):
                    save_last_session(self)
                print(f"[DEBUG] Loading save: {name}")
                self.state = GameState.LOADING
                self.loading_screen.set_text(f"Loading {name}...")
                self.loading_screen.set_percent(0)
                self.loading_params = (GameMode.Offline, name)
                self.loading_timer = pygame.time.get_ticks()
                self.loading_active = True
                self.loading_done = False
                threading.Thread(target=self._do_loading, daemon=True).start()
            return

        if self.load_menu_btns["back"].collidepoint(pos):
            self.state = GameState.PLAY_MENU
            self.menu_bg_green = False
            self.load_input_text = ""
            self.load_input_active = False
            self.selected_save = None
            return

        # Page tugmalari
        if self.load_menu_page_btns:
            if self.load_menu_page_btns["up"].collidepoint(pos):
                if self.load_menu_page > 0:
                    self.load_menu_page -= 1
                    self.selected_save = None
                    print(f"[DEBUG] Page up: {self.load_menu_page}")
                return
            if self.load_menu_page_btns["down"].collidepoint(pos):
                # PATCH: page_count ni to'g'ri hisoblash
                search = getattr(self, "load_input_text", "").lower()
                all_saves = list_saved_games()
                filtered_saves = [s for s in all_saves if search in s.lower()] if search else all_saves
                filtered_saves = [s for s in filtered_saves if s != "autosave"]
                saves = ["autosave"] + filtered_saves
                page_size = 5
                page_count = max(1, (len(saves) + page_size - 1) // page_size)
                if self.load_menu_page < page_count - 1:
                    self.load_menu_page += 1
                    self.selected_save = None
                    print(f"[DEBUG] Page down: {self.load_menu_page}")
                return

        # Delete tugmasi
        if self.load_menu_btns["delete"].collidepoint(pos):
            name = getattr(self, "selected_save", None)
            if name and name != "autosave":
                delete_save(name)
                self.selected_save = None
            return

        # Load tugmasi
        if self.load_menu_btns["load"].collidepoint(pos):
            name = getattr(self, "selected_save", None)
            if name and name in list_saved_games():
                self.state = GameState.LOADING
                self.loading_screen.set_text(f"Loading {name}...")
                self.loading_screen.set_percent(0)
                self.loading_params = (GameMode.Offline, name)
                self.loading_timer = pygame.time.get_ticks()
                self.loading_active = True
                self.loading_done = False
                threading.Thread(target=self._do_loading, daemon=True).start()
            return

        # Back tugmasi
        if self.load_menu_btns["back"].collidepoint(pos):
            self.state = GameState.PLAY_MENU
            self.menu_bg_green = False
            self.load_input_text = ""
            self.load_input_active = False
            self.selected_save = None
            return

        # Page tugmalari
        if self.load_menu_page_btns:
            if self.load_menu_page_btns["up"].collidepoint(pos):
                if self.load_menu_page > 0:
                    self.load_menu_page -= 1
                    self.selected_save = None  # PATCH: page o‘zgarganda tanlangan faylni tozalash
                return
            if self.load_menu_page_btns["down"].collidepoint(pos):
                page_count = max(1, (len(self.filtered_saves) + 4) // 5)
                if self.load_menu_page < page_count - 1:
                    self.load_menu_page += 1
                    self.selected_save = None  # PATCH: page o‘zgarganda tanlangan faylni tozalash
                return
  
    def check_game_over(self):
        alive_players = [p for p in self.players if p.state == PlayerState.ALIVE]
        downed_players = [p for p in self.players if p.state == PlayerState.DOWNED]
        dead_players = [p for p in self.players if p.state == PlayerState.DEAD]
        max_level = max((p.level for p in self.players), default=1)

        if max_level >= 999:
            self.state = GameState.GAME_OVER
            print("[INFO] O'yin tugadi (VICTORY)")
            return

        if len(self.players) > 0:
            if len(dead_players) == len(self.players):
                self.state = GameState.GAME_OVER
                print("[INFO] O'yin tugadi (GAME OVER) - hammasi o'ldi")
                return
            if len(downed_players) == len(self.players):
                self.state = GameState.GAME_OVER
                print("[INFO] O'yin tugadi (GAME OVER) - hammasi downed")
                return
            if len(dead_players) + len(downed_players) == len(self.players):
                self.state = GameState.GAME_OVER
                print("[INFO] O'yin tugadi (GAME OVER) - hammasi o'ldi yoki downed")
                return

    def _do_loading_from_slots(self):
        try:
            self.loading_screen.set_text("Preparing players...")
            LoadingScreen.start_game_from_loading(self, self.loading_selected_slots, self.loading_selected_modul)
            self.loading_screen.set_percent(100)
            pygame.time.wait(700)
            self.state = GameState.PLAYING
            self.loading_active = False
            self.loading_done = True
            self.game_start_time = pygame.time.get_ticks()
        except Exception as e:
            self.loading_screen.set_text(f"Error: {e}")
            self.loading_screen.set_percent(100)
            self.loading_active = False
            self.loading_done = True
            print(f"[ERROR] Loading from slots failed: {e}")

    def _do_loading(self):
        try:
            def progress_callback(percent):
                self.loading_percent = percent

            game_mode, save_name = self.loading_params
            data = load_game_data(game_mode, save_name, progress_callback)
            print(f"[INFO] Save '{save_name}' yuklanmoqda...")
            if data is None:
                print(f"[ERROR] Save '{save_name}' topilmadi yoki zarar ko‘rgan!")
                self.loading_text = f"Error: Save '{save_name}' not found"
                self.loading_percent = 100
                self.loading_done = True
                return
            self.players.clear()
            self.zombies.clear()
            self.bullets.clear()
            self.world = World()
            load_from_data(self, data)
            print(f"[INFO] Save '{save_name}' muvaffaqiyatli yuklandi!")
            print("[DEBUG] Players after load:", len(self.players), [p.id for p in self.players])
            print("[DEBUG] Mode after load:", self.mode)
        except Exception as e:
            print(f"[ERROR] Save yuklashda xatolik: {e}")
            self.loading_text = f"Error: {e}"
        self.loading_percent = 100
        self.loading_done = True
        self.loading_timer = pygame.time.get_ticks()
        self.state = GameState.PLAYING

    def update_loading(self):
        if not self.loading_active or self.loading_done:
            return
    def render_load_menu(self):
        self.screen.fill((40, 40, 60))
        font = self.font
        small_font = self.small_font
        center_x = self.screen_width // 2

        # Qidirish inputi
        input_y = 80
        input_w = 260
        input_h = 40
        input_rect = pygame.Rect(center_x - input_w // 2, input_y, input_w, input_h)
        pygame.draw.rect(self.screen, WHITE, input_rect, 2)
        input_text = small_font.render(getattr(self, "load_input_text", ""), True, WHITE)
        self.screen.blit(input_text, (input_rect.x + 10, input_rect.y + 8))

        # Tugmalar
        del_btn_rect = pygame.Rect(input_rect.left - 120, input_y, 100, input_h)
        load_btn_rect = pygame.Rect(input_rect.right + 20, input_y, 100, input_h)
        back_btn_rect = pygame.Rect(load_btn_rect.right + 20, input_y, 100, input_h)
        self.load_menu_btns = {
            "delete": del_btn_rect,
            "load": load_btn_rect,
            "back": back_btn_rect,
            "input": input_rect
        }
        pygame.draw.rect(self.screen, (200, 60, 60), del_btn_rect, border_radius=8)
        pygame.draw.rect(self.screen, (60, 180, 70), load_btn_rect, border_radius=8)
        pygame.draw.rect(self.screen, (100, 100, 200), back_btn_rect, border_radius=8)
        self.screen.blit(small_font.render("Delete", True, WHITE), del_btn_rect.move(20, 8))
        self.screen.blit(small_font.render("Load", True, WHITE), load_btn_rect.move(30, 8))
        self.screen.blit(small_font.render("Back", True, WHITE), back_btn_rect.move(30, 8))

        # Fayllar ro'yxati va page logikasi
        search = getattr(self, "load_input_text", "").lower()
        all_saves = list_saved_games()
        filtered_saves = [s for s in all_saves if search in s.lower()] if search else all_saves
        filtered_saves = [s for s in filtered_saves if s != "autosave"]
        saves = ["autosave"] + filtered_saves
        page_size = 5
        page_count = max(1, (len(saves) + page_size - 1) // page_size)
        page = getattr(self, "load_menu_page", 0)
        page = max(0, min(page, page_count - 1))
        self.load_menu_page = page
        slots = saves[page * page_size: (page + 1) * page_size]
        self.load_menu_slots_rects = []
        selected_save = getattr(self, "selected_save", None)

        slot_start_y = 160
        slot_gap = 30
        slot_h = 70
        slot_w = 480
        for i, save_name in enumerate(slots):
            slot_rect = pygame.Rect(center_x - slot_w // 2, slot_start_y + i * (slot_h + slot_gap), slot_w, slot_h)
            self.load_menu_slots_rects.append((save_name, slot_rect))
            color = (60, 180, 70) if save_name != "autosave" else (180, 180, 220)
            if save_name == selected_save:
                pygame.draw.rect(self.screen, (255, 220, 80), slot_rect, border_radius=12)
            else:
                pygame.draw.rect(self.screen, color, slot_rect, border_radius=12)
            name_text = font.render(f"{i + page * page_size}. {save_name}", True, WHITE)
            self.screen.blit(name_text, slot_rect.move(20, 10))
            try:
                data = load_game_data(GameMode.Offline, save_name)
                player_count = sum(1 for p in data["player"] if p.get("type", "player") == "player")
                bot_count = sum(1 for p in data["player"] if p.get("type", "player") == "bot")
                play_time = data.get("meta", {}).get("game_time", 0)
                minutes = play_time // 60000
                hours = minutes // 60
                minutes = minutes % 60
                time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
                info = f"Players: {player_count} | Bots: {bot_count} | Time: {time_str}"
            except Exception:
                info = "Corrupted or missing data"
            info_text = small_font.render(info, True, WHITE)
            self.screen.blit(info_text, slot_rect.move(20, 40))

        # Page tugmalari
        if page_count > 1:
            page_x = center_x - slot_w // 2 - 60
            page_y = slot_start_y + (page_size // 2) * (slot_h + slot_gap)
            box_rect = pygame.Rect(page_x, page_y, 50, 50)
            pygame.draw.rect(self.screen, (80, 80, 80), box_rect, border_radius=8)
            page_num_text = small_font.render(str(page + 1), True, WHITE)
            self.screen.blit(page_num_text, box_rect.move(15, 10))
            up_rect = pygame.Rect(page_x + 10, page_y - 30, 30, 20)
            pygame.draw.polygon(self.screen, (180, 180, 180) if page == 0 else BLACK,
                                [(up_rect.centerx, up_rect.top), (up_rect.left, up_rect.bottom), (up_rect.right, up_rect.bottom)])
            down_rect = pygame.Rect(page_x + 10, page_y + 50, 30, 20)
            pygame.draw.polygon(self.screen, (180, 180, 180) if page == page_count - 1 else BLACK,
                                [(down_rect.centerx, down_rect.bottom), (down_rect.left, down_rect.top), (down_rect.right, down_rect.top)])
            self.load_menu_page_btns = {"up": up_rect, "down": down_rect, "box": box_rect}
        else:
            self.load_menu_page_btns = {}

    def render(self):
        if self.state == GameState.MAIN_MENU:
            print(f"Game state: {self.state}")
            self.render_main_menu()
        elif self.state == GameState.PLAY_MENU:
            print(f"Game state: {self.state}")
            self.render_play_menu()
        elif self.state == GameState.LOAD_MENU:
            print(f"Game state: {self.state}")
            self.render_load_menu()
        elif self.state == GameState.LOADING:
            print(f"Game state: {self.state}")
            self.render_loading()
        elif self.state == GameState.PLAYING:
            print(f"Game state: {self.state}")
            self.render_game()
        elif self.state == GameState.PAUSED:
            print(f"Game state: {self.state}")
            self.render_pause_menu()
        elif self.state == GameState.GAME_OVER:
            print(f"Game state: {self.state}")
            self.render_game_over()
        elif self.state == GameState.LOADING:
            print(f"Game state: {self.state}")
            self.render_loading()



    def render_main_menu(self):
        self.menu_bg_color = (45, 80, 22)
        self.screen.fill(self.menu_bg_color)
        print(f"Background color: {self.menu_bg_color}")
        title = self.font.render("Zombie Survival Shooter", True, WHITE)
        title_rect = title.get_rect(center=(self.screen_width // 2, 180))
        self.screen.blit(title, title_rect)
        center_x = self.screen_width // 2
        button_width = 260
        button_height = 70
        gap = 40
        start_y = 320

        # PLAY tugmasi
        play_rect = pygame.Rect(center_x - button_width // 2, start_y, button_width, button_height)
        pygame.draw.rect(self.screen, (24, 134, 42), play_rect, border_radius=18)
        play_text = self.font.render("Play", True, WHITE)
        self.screen.blit(play_text, play_text.get_rect(center=play_rect.center))

        # MULTIPLAYER tugmasi (faqat ko‘rinish, funksiya yo‘q)
        multi_rect = pygame.Rect(center_x - button_width // 2, start_y + button_height + gap, button_width, button_height)
        pygame.draw.rect(self.screen, (70, 160, 230), multi_rect, border_radius=18)
        multi_text = self.font.render("Multiplayer", True, WHITE)
        self.screen.blit(multi_text, multi_text.get_rect(center=multi_rect.center))

        # EXIT tugmasi
        exit_rect = pygame.Rect(center_x - button_width // 2, start_y + 2 * (button_height + gap), button_width, button_height)
        pygame.draw.rect(self.screen, (200, 100, 100), exit_rect, border_radius=18)
        exit_text = self.font.render("Exit", True, WHITE)
        self.screen.blit(exit_text, exit_text.get_rect(center=exit_rect.center))

        # Tugmalarni bosish uchun aniqlash
        if self.mouse_down:
            mx, my = self.mouse_pos.x, self.mouse_pos.y
            if play_rect.collidepoint(mx, my):
                self.state = GameState.PLAY_MENU
                self.menu_bg_color = (70, 160, 230) 
            elif multi_rect.collidepoint(mx, my):
                pass
            elif exit_rect.collidepoint(mx, my):
                pygame.quit()
                sys.exit()  

    def render_play_menu(self):
        self.screen.fill((70, 160, 230))
        center_x = self.screen_width // 2
        slot_width = 180
        slot_height = 60
        slot_gap = 30
        slot_start_y = 220

        self.play_slots_rects = []
        self.add_buttons_rects = []
        self.x_buttons_rects = []
        self.selected_modul = getattr(self, "selected_modul", "defult")

        moduls_list = get_all_moduls()
        modul_btn_width, modul_btn_height = 140, 32
        modul_start_y = 120
        center_x = self.screen_width // 2
        self.modul_btn_rects = []
        for i, modul_name in enumerate(moduls_list):
            modul_rect = pygame.Rect(center_x - modul_btn_width // 2, modul_start_y + i * (modul_btn_height + 8),
                                     modul_btn_width, modul_btn_height)
            color = (24, 134, 42) if self.selected_modul == modul_name else (70, 160, 230)
            pygame.draw.rect(self.screen, color, modul_rect, border_radius=8)
            text = self.small_font.render(modul_name, True, WHITE)
            self.screen.blit(text, text.get_rect(center=modul_rect.center))
            self.modul_btn_rects.append((modul_name, modul_rect))

        for i in range(4):
            slot_rect = pygame.Rect(center_x - slot_width // 2, slot_start_y + i * (slot_height + slot_gap), slot_width, slot_height)
            self.play_slots_rects.append(slot_rect)
            if not self.selected_slots:
                self.selected_slots.append({'type': 'player', 'id': 1, 'name': 'Player 1', 'pos_x': 0, 'pos_y': 0})
            if i < len(self.selected_slots):
                slot = self.selected_slots[i]
                color = (24, 134, 42) if slot['type'] == 'player' else (200, 220, 240)
                pygame.draw.rect(self.screen, color, slot_rect, border_radius=12)
                slot_text = self.small_font.render(slot['name'], True, WHITE)
                self.screen.blit(slot_text, slot_text.get_rect(center=slot_rect.center))
                x_rect = pygame.Rect(slot_rect.right - 30, slot_rect.top + 10, 20, 20)
                pygame.draw.rect(self.screen, (220, 50, 50), x_rect, border_radius=6)
                x_text = self.small_font.render("X", True, WHITE)
                self.screen.blit(x_text, x_text.get_rect(center=x_rect.center))
                self.x_buttons_rects.append((i, x_rect))
            else:
                pygame.draw.rect(self.screen, (180, 180, 180), slot_rect, border_radius=12)
                slot_text = self.small_font.render("Empty", True, (60, 60, 60))
                self.screen.blit(slot_text, slot_text.get_rect(center=slot_rect.center))
                add_rect = pygame.Rect(slot_rect.right + 15, slot_rect.top + slot_height // 2 - 20, 50, 40)
                pygame.draw.rect(self.screen, (60, 180, 70), add_rect, border_radius=8)
                add_text = self.small_font.render("Add", True, WHITE)
                self.screen.blit(add_text, add_text.get_rect(center=add_rect.center))
                self.add_buttons_rects.append((i, add_rect))


        # Add menyu ochilgan bo‘lsa
        if self.add_menu_active:
            self.render_add_menu()

        btn_width = 140
        btn_height = 50
        btn_gap = 30
        btn_y = slot_start_y + 4 * (slot_height + slot_gap) + 30

        total_width = btn_width * 3 + btn_gap * 2
        start_x = center_x - total_width // 2

        start_rect = pygame.Rect(start_x, btn_y, btn_width, btn_height)
        pygame.draw.rect(self.screen, (24, 134, 42), start_rect, border_radius=10)
        start_text = self.small_font.render("Start", True, WHITE)
        self.screen.blit(start_text, start_text.get_rect(center=start_rect.center))

        load_rect = pygame.Rect(start_x + btn_width + btn_gap, btn_y, btn_width, btn_height)
        pygame.draw.rect(self.screen, (70, 100, 200), load_rect, border_radius=10)  # To'q ko'k
        load_text = self.small_font.render("Load", True, WHITE)
        self.screen.blit(load_text, load_text.get_rect(center=load_rect.center))

        back_rect = pygame.Rect(start_x + 2 * (btn_width + btn_gap), btn_y, btn_width, btn_height)
        pygame.draw.rect(self.screen, (200, 100, 100), back_rect, border_radius=10)
        back_text = self.small_font.render("Back", True, WHITE)
        self.screen.blit(back_text, back_text.get_rect(center=back_rect.center))

        self.play_menu_buttons = {
            'start': start_rect,
            'load': load_rect,
            'back': back_rect
        }
    def render_add_menu(self):
        menu_width = int(self.screen_width * 0.75)
        menu_height = 120
        menu_x = self.screen_width // 2 - menu_width // 2
        menu_y = self.screen_height // 2 - menu_height // 2
        pygame.draw.rect(self.screen, (220, 220, 220), (menu_x, menu_y, menu_width, menu_height), border_radius=16)
        slot_w = 70
        slot_h = 90
        gap = 20
        self.add_menu_rects = []
        for i, obj in enumerate([
            {'type': 'player', 'id': 1, 'name': 'Player 1'},
            {'type': 'player', 'id': 2, 'name': 'Player 2'},
            {'type': 'bot', 'id': 101, 'name': 'Bot 1'},
            {'type': 'bot', 'id': 102, 'name': 'Bot 2'},
            {'type': 'bot', 'id': 103, 'name': 'Bot 3'},
            {'type': 'bot', 'id': 104, 'name': 'Bot 4'},
        ]):
            slot_x = menu_x + 30 + i * (slot_w + gap)
            slot_y = menu_y + 15
            slot_rect = pygame.Rect(slot_x, slot_y, slot_w, slot_h)
            is_selected = any(s['id'] == obj['id'] for s in self.selected_slots)
            color = (220, 50, 50) if is_selected else (60, 180, 70)
            pygame.draw.rect(self.screen, color, slot_rect, border_radius=10)
            slot_text = self.small_font.render(obj['name'], True, WHITE)
            self.screen.blit(slot_text, slot_text.get_rect(center=slot_rect.center))
            self.add_menu_rects.append((obj, slot_rect))
    def render_loading(self):
        self.screen.fill((20, 20, 20))
        font = pygame.font.Font(None, 48)
        text = font.render(self.loading_text or "Loading...", True, (255, 255, 255))
        self.screen.blit(text, (self.screen_width // 2 - text.get_width() // 2, 300))
        bar_x = self.screen_width // 2 - 150
        bar_y = 400
        bar_width = 300
        bar_height = 30
        pygame.draw.rect(self.screen, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height))
        fill_width = int(bar_width * self.loading_percent / 100)
        pygame.draw.rect(self.screen, (60, 180, 70), (bar_x, bar_y, fill_width, bar_height))
        percent_text = self.small_font.render(f"{self.loading_percent}%", True, (255, 255, 255))
        self.screen.blit(percent_text, (self.screen_width // 2 - percent_text.get_width() // 2, bar_y + bar_height + 10))

    def render_game(self):
        if self.logic and hasattr(self.logic, "render"):
            self.logic.render(self)
        else:
            pass
        self.world.render(self.screen, self.camera, self.screen_width, self.screen_height)
        for zombie in self.zombies:
            zombie.render(self.screen, self.camera)
        for bullet in self.bullets:
            bullet.render(self.screen, self.camera)
        for player in self.players:
            player.render(self.screen, self.camera)
        if self.is_night:
            night_surface = pygame.Surface((self.screen_width, self.screen_height))
            night_surface.fill((0, 0, 50))
            night_surface.set_alpha(100)
            self.screen.blit(night_surface, (0, 0))
        print("RENDER_GAME:", self.state, self.loading_active, len(self.players), len(self.zombies))
        self.render_hud()

    def render_hud(self):
        if not self.players:
            return
        player1 = next((p for p in self.players if p.id == 1), self.players[0])
        hud_x = 20 if len(self.players) > 1 else self.screen_width // 2 - 100
        hud_info = [
            f"P1 Level: {player1.level}",
            f"P1 State: {player1.state.name}",
            f"Weapon: {player1.weapon_type.name.replace('_', ' ').title()}",
            f"Zombies: {sum(p.zombie_kills for p in self.players)}",
            f"Day: {self.current_day} ({'Night' if self.is_night else 'Day'})"
        ]
        if player1.drone:
            hud_info.append(f"Drone Level: {player1.drone.level}")
        for i, info in enumerate(hud_info):
            color = WHITE
            if "State: DOWNED" in info:
                color = YELLOW
            elif "State: DEAD" in info:
                color = RED
            text = self.small_font.render(info, True, color)
            self.screen.blit(text, (hud_x, 20 + i * 25))
        if len(self.players) > 1:
            player2 = next((p for p in self.players if p.id != 1), None)

            hud_x2 = self.screen_width - 220
            hud_info2 = [
                f"P2 Level: {player2.level}",
                f"P2 State: {player2.state.name}",
                f"Weapon: {player2.weapon_type.name.replace('_', ' ').title()}"
            ]
            if player2.drone:
                hud_info2.append(f"Drone Level: {player2.drone.level}")
            for i, info in enumerate(hud_info2):
                color = WHITE
                if "State: DOWNED" in info:
                    color = YELLOW
                elif "State: DEAD" in info:
                    color = RED
                text = self.small_font.render(info, True, color)
                text_rect = text.get_rect(topright=(hud_x2, 20 + i * 25))
                self.screen.blit(text, text_rect)

    def render_save_input(self):
        center_x = self.screen_width // 2
        y = 600
        box_width = 300
        box_height = 40
        pygame.draw.rect(self.screen, WHITE, (center_x - box_width // 2, y, box_width, box_height), 2)
        text = self.small_font.render("Save Name:", True, WHITE)
        self.screen.blit(text, (center_x - box_width // 2 + 5, y - 25))
        input_text = self.small_font.render(self.save_input_text, True, WHITE)
        self.screen.blit(input_text, (center_x - box_width // 2 + 10, y + 8))
        save_btn_rect = pygame.Rect(center_x + box_width // 2 - 80, y, 70, box_height)
        pygame.draw.rect(self.screen, GREEN, save_btn_rect)
        save_text = self.small_font.render("Save", True, WHITE)
        self.screen.blit(save_text, (save_btn_rect.centerx - 20, y + 8))

    def render_pause_menu(self):
        bg_color = (0, 200, 0) if self.pause_bg_green and self.save_input_active else BLACK
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill(bg_color)
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill(BLACK)
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))
        title = self.font.render("PAUSED", True, WHITE)
        title_rect = title.get_rect(center=(self.screen_width // 2, 250))
        self.screen.blit(title, title_rect)
        center_x = self.screen_width // 2
        button_width = 150
        button_height = 50
        buttons = [
            ("Continue", 350),
            ("Restart", 420),
            ("Save", 490),
            ("Main Menu", 560)
        ]
        for idx, (text, y) in enumerate(buttons):
            pygame.draw.rect(self.screen, (74, 124, 89) if text != "Main Menu" else (139, 69, 19),
                             (center_x - button_width // 2, y, button_width, button_height))
            rendered_text = self.small_font.render(text, True, WHITE)
            text_rect = rendered_text.get_rect(center=(center_x, y + button_height // 2))
            self.screen.blit(rendered_text, text_rect)
        if self.save_input_active:
            self.render_save_input()
        if self.save_slot_full:
            msg = self.small_font.render("Slot full", True, (255, 0, 0))
            self.screen.blit(msg, (center_x - 60, 650))
        elif self.show_save_success:
            msg = self.small_font.render("Game saved!", True, (0, 220, 0))
            self.screen.blit(msg, (center_x - 60, 650))

    def render_game_over(self):
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill(BLACK)
        overlay.set_alpha(200)
        self.screen.blit(overlay, (0, 0))
        max_level = max((p.level for p in self.players), default=1)
        is_victory = max_level >= 1000
        title_text = "VICTORY!" if is_victory else "GAME OVER"
        title_color = GREEN if is_victory else RED
        title = self.font.render(title_text, True, title_color)
        title_rect = title.get_rect(center=(self.screen_width // 2, 200))
        self.screen.blit(title, title_rect)
        days = self.current_day
        total_kills = sum(p.zombie_kills for p in self.players)
        max_level = max((p.level for p in self.players), default=1)
        stats = [
            f"Days Survived: {days}",
            f"Zombies Killed: {total_kills}",
            f"Max Level Reached: {max_level}",
        ]
        if hasattr(self, "zombie_kills_by_type"):
            stats.append("Zombie kills by type:")
            for ztype in ALL_ZOMBIE_TYPES:
                count = self.zombie_kills_by_type[ztype.value]
                stats.append(f"  {ztype.value}: {count}")

        for i, stat in enumerate(stats):
            text = self.small_font.render(stat, True, WHITE)
            text_rect = text.get_rect(center=(self.screen_width // 2, 300 + i * 30))
            self.screen.blit(text, text_rect)
        center_x = self.screen_width // 2
        button_width = 150
        button_height = 50
        play_again_x = center_x - 170
        pygame.draw.rect(self.screen, (74, 124, 89),
                         (play_again_x, 500, button_width, button_height))
        text = self.small_font.render("Play Again", True, WHITE)
        text_rect = text.get_rect(center=(play_again_x + button_width // 2, 525))
        self.screen.blit(text, text_rect)
        main_menu_x = center_x + 170 - button_width
        pygame.draw.rect(self.screen, (139, 69, 19),
                         (main_menu_x, 500, button_width, button_height))
        text = self.small_font.render("Main Menu", True, WHITE)
        text_rect = text.get_rect(center=(main_menu_x + button_width // 2, 525))
        self.screen.blit(text, text_rect)

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.render()
            pygame.display.flip()
            self.clock.tick(FPS)
