import random
import math
import pygame
from core import Vector2, GameState, PlayerState, WeaponType, GameMode
from Moduls.ProtectBase.player import Player
from Moduls.ProtectBase.helper_bot import HelperBot
from Moduls.ProtectBase.save_load import save_game
from Moduls.ProtectBase.world import World
from Moduls.ProtectBase.zombie import Zombie, ZombieType
from Moduls.ProtectBase.base import Base

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 0, 0)
GREEN = (0, 200, 0)
YELLOW = (255, 255, 0)

ALL_ZOMBIE_TYPES = [ZombieType.WALKER, ZombieType.RUNNER, ZombieType.TANKER]
ZOMBIE_TYPE_WEIGHTS = {
    ZombieType.WALKER: 0.6,
    ZombieType.RUNNER: 0.3,
    ZombieType.TANKER: 0.1
}


class GameEngine:
    def __init__(self, screen, width, height):
        self.screen = screen
        self.screen_width = width
        self.screen_height = height
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.clock = pygame.time.Clock()
        
        self.state = "PLAYING"
        self.mode = GameMode.Offline 
        self.fullscreen = False
        self.pause_bg_green = False
        
        self.players = []
        self.zombies = []
        self.bullets = []
        self.world = World()
        self.camera = Vector2(0, 0)
        
        self.base = None
        
        self.game_start_time = pygame.time.get_ticks()
        self.game_time = 0
        self.current_day = 1
        self.is_night = False
        self.zombie_strength = 1
        self.zombies_killed = 0
        self.zombie_kills_by_type = {ztype.value: 0 for ztype in ALL_ZOMBIE_TYPES}
        
        self.last_zombie_spawn = 0
        self.next_power_up_time = 0
        
        self.keys = set()
        self.mouse_pos = Vector2(0, 0)
        self.mouse_down = False
        
        self.last_loaded_save_name = None
        self.last_loaded_mode = None

    def setup_players(self, selected_slots):
        self.players.clear()
        
        self.base = Base(Vector2(0, 0))
        
        PLAYER_CONTROLS = {
            1: {
                'up': pygame.K_w,
                'down': pygame.K_s,
                'left': pygame.K_a,
                'right': pygame.K_d,
                'shoot': [pygame.K_SPACE, pygame.K_f],
                # orbit keys for base (Q/E)
                'orbit_left': pygame.K_q,
                'orbit_right': pygame.K_e
            },
            2: {
                'up': pygame.K_UP,
                'down': pygame.K_DOWN,
                'left': pygame.K_LEFT,
                'right': pygame.K_RIGHT,
                'shoot': [pygame.K_k],
                # orbit keys for base (O/P)
                'orbit_left': pygame.K_o,
                'orbit_right': pygame.K_p
            }
        }
        
        if not selected_slots:
            player = Player(Vector2(0, 0), 1)
            player.controls = PLAYER_CONTROLS.get(1, {})
            self.players.append(player)
            player.connect_to_base(self.base, 0)
            return
        
        player_count = sum(1 for s in selected_slots if s.get('type') == 'player')
        is_multiplayer = len(selected_slots) >= 2
        
        player_index = 0
        angle_step = (2 * math.pi) / max(1, len(selected_slots))
        
        for i, slot in enumerate(selected_slots):
            slot_type = slot.get('type', 'player')
            slot_id = slot.get('id', 1)
            color = tuple(slot.get('color', [40, 120, 255]))
            
            initial_angle = i * angle_step
            
            if slot_type == 'player':
                player_index += 1
                player = Player(Vector2(0, 0), slot_id, color=color)
                player.controls = PLAYER_CONTROLS.get(player_index, PLAYER_CONTROLS.get(1, {}))
                player.multi_player_mode = is_multiplayer
                player.can_go_down = is_multiplayer
                player.connect_to_base(self.base, initial_angle)
                self.players.append(player)
            elif slot_type == 'bot':
                bot = HelperBot(Vector2(0, 0), slot_id, color=color)
                bot.multi_player_mode = is_multiplayer
                bot.can_go_down = is_multiplayer
                bot.connect_to_base(self.base, initial_angle)
                self.players.append(bot)
        
        print(f"[GameEngine ProtectBase] Setup {len(self.players)} players connected to base")

    def setup_world(self):
        self.zombies.clear()
        self.bullets.clear()
        self.world = World()
        print("[GameEngine ProtectBase] World initialized")

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            info = pygame.display.Info()
            self.screen_width, self.screen_height = info.current_w, info.current_h
        else:
            self.screen_width, self.screen_height = 1200, 800
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))

    def update_camera(self):
        if self.base:
            self.camera.x = self.base.position.x - self.screen_width // 2
            self.camera.y = self.base.position.y - self.screen_height // 2

    def handle_pause_click(self, pos):
        if hasattr(self, 'pause_save_input_active') and self.pause_save_input_active:
            if hasattr(self, 'pause_save_dialog_input') and self.pause_save_dialog_input.collidepoint(pos):
                return
            
            if hasattr(self, 'pause_save_dialog_cancel') and self.pause_save_dialog_cancel.collidepoint(pos):
                self.pause_save_input_active = False
                self.pause_save_input_text = ""
                return
            
            if hasattr(self, 'pause_save_dialog_save') and self.pause_save_dialog_save.collidepoint(pos):
                if self.pause_save_input_text.strip():
                    try:
                        save_game(self, self.pause_save_input_text, self.mode, modul_name="ProtectBase")
                        print(f"[INFO] O'yin '{self.pause_save_input_text}' nomida saqlandi")
                    except Exception as e:
                        print(f"[ERROR] Save xatosi: {e}")
                self.pause_save_input_active = False
                self.pause_save_input_text = ""
                return
        
        if hasattr(self, 'pause_menu_buttons'):
            for btn_name, btn_rect in self.pause_menu_buttons.items():
                if btn_rect.collidepoint(pos):
                    if btn_name == "continue":
                        self.state = "PLAYING"
                        self.pause_bg_green = False
                    elif btn_name == "save":
                        self.pause_save_input_active = True
                        self.pause_save_input_text = ""
                    elif btn_name == "restart":
                        self.restart_game()
                        self.state = "PLAYING"
                        self.pause_bg_green = False
                    elif btn_name == "main menu":
                        self.state = "MAIN_MENU"
                        self.pause_bg_green = False
                    return

    def handle_game_over_click(self, pos):
        x, y = pos
        center_x = self.screen_width // 2
        button_width = 150
        button_height = 50
        play_again_x = center_x - 160
        
        if (play_again_x <= x <= play_again_x + button_width and
                500 <= y <= 500 + button_height):
            self.restart_game()
            return
        
        main_menu_x = center_x + 10
        if (main_menu_x <= x <= main_menu_x + button_width and
                500 <= y <= 500 + button_height):
            self.state = "MAIN_MENU"
            return

    def restart_game(self):
        print("[INFO] O'yin qayta boshlandi")
        self.setup_players(getattr(self, '_last_selected_slots', [{'type': 'player', 'id': 1, 'name': 'Player 1'}]))
        self.setup_world()
        self.state = "PLAYING"
        self.game_start_time = pygame.time.get_ticks()

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
        if self.base:
            base_bullets = self.base.update(dt, self.zombies, self.players)
            self.bullets.extend(base_bullets)
        
        alive_positions = [p.position for p in self.players if p.state == PlayerState.ALIVE]
        for player in self.players:
            if player.state != PlayerState.DEAD:
                other_players = [p for p in self.players if p.id != player.id]
                new_bullets = player.update(dt, self.world.power_ups, self.zombies, other_players)
                self.bullets.extend(new_bullets)
        
        self.world.update(alive_positions if alive_positions else [self.base.position] if self.base else [])

    def update_zombies(self, dt):
        alive_positions = [p.position for p in self.players if p.state == PlayerState.ALIVE]
        if self.base and self.base.active:
            alive_positions.append(self.base.position)
        
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
            
            if self.base and self.base.active:
                distance = (zombie.position - self.base.position).length()
                if distance < self.base.size // 2 + 10 and zombie.can_attack(pygame.time.get_ticks()):
                    damage = zombie.attack(pygame.time.get_ticks())
                    self.base.take_damage(damage)

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
        
        if self.base:
            if self.base.level >= 100:
                spawn_rate *= 0.3
        
        if current_time - self.last_zombie_spawn >= spawn_rate:
            self.spawn_zombie()
            if random.random() < 0.25:
                self.spawn_zombie()
            self.last_zombie_spawn = current_time

    def spawn_zombie(self):
        if not self.base or not self.base.active:
            return
        
        angle = random.random() * 2 * math.pi
        distance = 400 + random.random() * 200
        spawn_pos = Vector2(
            self.base.position.x + math.cos(angle) * distance,
            self.base.position.y + math.sin(angle) * distance
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
                                self.zombie_kills_by_type[ztype.value] += 1
                        if self.base:
                            self.base.add_zombie_kill()
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

    def check_game_over(self):
        if self.base and not self.base.active:
            self.state = "GAME_OVER"
            print("[INFO] O'yin tugadi - Baza yo'q qilindi!")
            return
        
        if self.base and self.base.level >= 999:
            self.state = "GAME_OVER"
            print("[INFO] O'yin tugadi (VICTORY)")
            return

    def handle_events(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if hasattr(self, 'pause_save_input_active') and self.pause_save_input_active:
                    if event.key == pygame.K_RETURN:
                        if self.pause_save_input_text.strip():
                            try:
                                save_game(self, self.pause_save_input_text, self.mode, modul_name="ProtectBase")
                            except Exception as e:
                                print(f"[ERROR] Save xatosi: {e}")
                        self.pause_save_input_active = False
                        self.pause_save_input_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.pause_save_input_text = self.pause_save_input_text[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        self.pause_save_input_active = False
                        self.pause_save_input_text = ""
                    elif event.unicode.isprintable():
                        if len(self.pause_save_input_text) < 30:
                            self.pause_save_input_text += event.unicode
                    return True
                
                for p in self.players:
                    if hasattr(p, 'controls'):
                        if event.key == p.controls.get('up'):
                            p.move_up = True
                        if event.key == p.controls.get('down'):
                            p.move_down = True
                        if event.key == p.controls.get('left'):
                            p.move_left = True
                        if event.key == p.controls.get('right'):
                            p.move_right = True
                        # orbit flags (used when connected_to_base)
                        if 'orbit_left' in p.controls and event.key == p.controls.get('orbit_left'):
                            setattr(p, 'orbit_left', True)
                        if 'orbit_right' in p.controls and event.key == p.controls.get('orbit_right'):
                            setattr(p, 'orbit_right', True)
                        if 'shoot' in p.controls and event.key in p.controls['shoot']:
                            p.shooting = True
                
                self.keys.add(event.key)
                
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                
                if event.key == pygame.K_ESCAPE:
                    if self.state == "PLAYING":
                        self.state = "PAUSED"
                        self._init_pause_menu_buttons()
                    elif self.state == "PAUSED":
                        self.state = "PLAYING"
            
            elif event.type == pygame.KEYUP:
                for p in self.players:
                    if hasattr(p, 'controls'):
                        if event.key == p.controls.get('up'):
                            p.move_up = False
                        if event.key == p.controls.get('down'):
                            p.move_down = False
                        if event.key == p.controls.get('left'):
                            p.move_left = False
                        if event.key == p.controls.get('right'):
                            p.move_right = False
                        # orbit flags
                        if 'orbit_left' in p.controls and event.key == p.controls.get('orbit_left'):
                            setattr(p, 'orbit_left', False)
                        if 'orbit_right' in p.controls and event.key == p.controls.get('orbit_right'):
                            setattr(p, 'orbit_right', False)
                        if 'shoot' in p.controls and event.key in p.controls['shoot']:
                            p.shooting = False
                self.keys.discard(event.key)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.mouse_pos = Vector2(event.pos[0], event.pos[1])
                    self.mouse_down = True
                    self.handle_mouse_click(event.pos)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.mouse_down = False
            
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = Vector2(event.pos[0], event.pos[1])
        
        return True

    def handle_mouse_click(self, pos):
        if self.state == "PAUSED":
            self.handle_pause_click(pos)
        elif self.state == "GAME_OVER":
            self.handle_game_over_click(pos)

    def step_update(self, dt):
        if self.state != "PLAYING":
            return
        
        self.update_day_night_cycle()
        self.update_players(dt)
        self.update_zombies(dt)
        self.update_bullets(dt)
        self.spawn_zombies()
        self.spawn_power_ups()
        self.check_collisions()
        self.update_camera()
        self.check_game_over()

    def _init_pause_menu_buttons(self):
        center_x = self.screen_width // 2
        button_width = 150
        button_height = 50
        self.pause_menu_buttons = {
            "continue": pygame.Rect(center_x - button_width // 2, 300, button_width, button_height),
            "save": pygame.Rect(center_x - button_width // 2, 370, button_width, button_height),
            "restart": pygame.Rect(center_x - button_width // 2, 440, button_width, button_height),
            "main menu": pygame.Rect(center_x - button_width // 2, 510, button_width, button_height)
        }

    def render_pause_menu(self):
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill(BLACK)
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))
        
        title = self.font.render("PAUSED - PROTECT BASE", True, WHITE)
        title_rect = title.get_rect(center=(self.screen_width // 2, 250))
        self.screen.blit(title, title_rect)
        
        if not hasattr(self, 'pause_menu_buttons'):
            self._init_pause_menu_buttons()
        
        if not hasattr(self, 'pause_save_input_active'):
            self.pause_save_input_active = False
            self.pause_save_input_text = ""
        
        for btn_name, btn_rect in self.pause_menu_buttons.items():
            pygame.draw.rect(self.screen, (70, 70, 70), btn_rect)
            pygame.draw.rect(self.screen, WHITE, btn_rect, 2)
            btn_text = self.font.render(btn_name.title(), True, WHITE)
            btn_text_rect = btn_text.get_rect(center=btn_rect.center)
            self.screen.blit(btn_text, btn_text_rect)

        # Pause save input dialog
        if getattr(self, 'pause_save_input_active', False):
            dialog_w, dialog_h = 520, 160
            dialog_x = self.screen_width // 2 - dialog_w // 2
            dialog_y = self.screen_height // 2 - dialog_h // 2
            dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
            pygame.draw.rect(self.screen, (60, 60, 60), dialog_rect)
            pygame.draw.rect(self.screen, WHITE, dialog_rect, 2)

            prompt = self.font.render("Save name:", True, WHITE)
            self.screen.blit(prompt, (dialog_x + 20, dialog_y + 16))

            input_rect = pygame.Rect(dialog_x + 20, dialog_y + 56, dialog_w - 40, 36)
            pygame.draw.rect(self.screen, (30, 30, 30), input_rect)
            pygame.draw.rect(self.screen, WHITE, input_rect, 2)

            # Render input text
            txt = self.pause_save_input_text if hasattr(self, 'pause_save_input_text') else ''
            input_text_surface = self.font.render(txt, True, WHITE)
            # clip if too long
            max_w = input_rect.w - 10
            if input_text_surface.get_width() > max_w:
                # show only last part
                text_to_show = txt[-(max_w // 10):]
                input_text_surface = self.font.render(text_to_show, True, WHITE)
            self.screen.blit(input_text_surface, (input_rect.x + 6, input_rect.y + 4))

            # Buttons
            btn_w, btn_h = 110, 36
            save_btn = pygame.Rect(dialog_x + dialog_w - btn_w - 20, dialog_y + dialog_h - btn_h - 16, btn_w, btn_h)
            cancel_btn = pygame.Rect(dialog_x + 20, dialog_y + dialog_h - btn_h - 16, btn_w, btn_h)

            pygame.draw.rect(self.screen, (70, 130, 70), save_btn)
            pygame.draw.rect(self.screen, WHITE, save_btn, 2)
            save_text = self.font.render("Save", True, WHITE)
            save_text_rect = save_text.get_rect(center=save_btn.center)
            self.screen.blit(save_text, save_text_rect)

            pygame.draw.rect(self.screen, (130, 70, 70), cancel_btn)
            pygame.draw.rect(self.screen, WHITE, cancel_btn, 2)
            cancel_text = self.font.render("Cancel", True, WHITE)
            cancel_text_rect = cancel_text.get_rect(center=cancel_btn.center)
            self.screen.blit(cancel_text, cancel_text_rect)

            # store rects for click handling
            self.pause_save_dialog_input = input_rect
            self.pause_save_dialog_save = save_btn
            self.pause_save_dialog_cancel = cancel_btn

    def render_game_over(self):
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill(BLACK)
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))
        
        if self.base and self.base.level >= 999:
            title = self.font.render("VICTORY!", True, (255, 215, 0))
        else:
            title = self.font.render("GAME OVER - BASE DESTROYED!", True, RED)
        title_rect = title.get_rect(center=(self.screen_width // 2, 300))
        self.screen.blit(title, title_rect)
        
        if self.base:
            stats_text = self.font.render(f"Base Level: {self.base.level} | Kills: {self.base.zombie_kills}", True, WHITE)
            stats_rect = stats_text.get_rect(center=(self.screen_width // 2, 400))
            self.screen.blit(stats_text, stats_rect)
        
        center_x = self.screen_width // 2
        button_width = 150
        button_height = 50
        
        play_again_rect = pygame.Rect(center_x - 160, 500, button_width, button_height)
        pygame.draw.rect(self.screen, (70, 130, 70), play_again_rect)
        pygame.draw.rect(self.screen, WHITE, play_again_rect, 2)
        play_text = self.font.render("Play Again", True, WHITE)
        play_text_rect = play_text.get_rect(center=play_again_rect.center)
        self.screen.blit(play_text, play_text_rect)
        
        menu_rect = pygame.Rect(center_x + 10, 500, button_width, button_height)
        pygame.draw.rect(self.screen, (130, 70, 70), menu_rect)
        pygame.draw.rect(self.screen, WHITE, menu_rect, 2)
        menu_text = self.font.render("Main Menu", True, WHITE)
        menu_text_rect = menu_text.get_rect(center=menu_rect.center)
        self.screen.blit(menu_text, menu_text_rect)

    def render_hud(self):
        if self.base:
            base_info = f"BASE HP: {self.base.health}/{self.base.max_health} | LVL: {self.base.level} | Kills: {self.base.zombie_kills}"
            info_text = self.font.render(base_info, True, WHITE)
            pygame.draw.rect(self.screen, (0, 0, 0, 128), (10, 10, info_text.get_width() + 20, 40))
            self.screen.blit(info_text, (20, 20))
        
        day_text = f"Day {self.current_day}" + (" (Night)" if self.is_night else "")
        day_surface = self.small_font.render(day_text, True, WHITE)
        self.screen.blit(day_surface, (self.screen_width - day_surface.get_width() - 20, 20))

    def render(self):
        self.world.render(self.screen, self.camera, self.screen_width, self.screen_height)
        
        if self.base:
            self.base.render_chains(self.screen, self.camera, self.players)
            self.base.render(self.screen, self.camera)
        
        for player in self.players:
            player.render(self.screen, self.camera)
        
        for zombie in self.zombies:
            zombie.render(self.screen, self.camera)
        
        for bullet in self.bullets:
            bullet.render(self.screen, self.camera)
        
        self.render_hud()
        
        if self.state == "PAUSED":
            self.render_pause_menu()
        elif self.state == "GAME_OVER":
            self.render_game_over()

    def run(self, selected_slots=None):
        self._last_selected_slots = selected_slots or []
        self.setup_players(selected_slots or [])
        self.setup_world()
        
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            self.game_time = pygame.time.get_ticks() - self.game_start_time
            
            running = self.handle_events()
            
            if self.state == "MAIN_MENU":
                return "MAIN_MENU"
            
            self.step_update(dt)
            self.render()
            
            pygame.display.flip()
        
        pygame.quit()
        return None


def run_game(screen, width, height, selected_slots=None):
    engine = GameEngine(screen, width, height)
    return engine.run(selected_slots)
