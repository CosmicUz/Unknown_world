import random
import math
import pygame
from core import Vector2, GameState, PlayerState, WeaponType, GameMode
from Moduls.default.player import Player
from Moduls.default.helper_bot import HelperBot
from Moduls.default.world import World
from Moduls.default.zombie import Zombie, ZombieType

# Color constants
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 0, 0)
GREEN = (0, 200, 0)
YELLOW = (255, 255, 0)

# Zombie spawn weights
ALL_ZOMBIE_TYPES = [ZombieType.WALKER, ZombieType.RUNNER, ZombieType.TANKER]
ZOMBIE_TYPE_WEIGHTS = {
    ZombieType.WALKER: 0.6,
    ZombieType.RUNNER: 0.3,
    ZombieType.TANKER: 0.1
}


class GameEngine:
    """
    Complete game engine encapsulating all gameplay logic.
    """
    def __init__(self, screen, width, height):
        self.screen = screen
        self.screen_width = width
        self.screen_height = height
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.clock = pygame.time.Clock()
        
        # Game state
        self.state = "PLAYING"
        self.mode = GameMode.Offline 
        self.fullscreen = False
        self.pause_bg_green = False
        
        # Player & world
        self.players = []
        self.zombies = []
        self.bullets = []
        self.world = World()
        self.camera = Vector2(0, 0)
        
        # Game timing & progression
        self.game_start_time = pygame.time.get_ticks()
        self.game_time = 0
        self.current_day = 1
        self.is_night = False
        self.zombie_strength = 1
        self.zombies_killed = 0
        self.zombie_kills_by_type = {ztype.value: 0 for ztype in ALL_ZOMBIE_TYPES}
        
        # Spawn tracking
        self.last_zombie_spawn = 0
        self.next_power_up_time = 0
        
        # Input tracking
        self.keys = set()
        self.mouse_pos = Vector2(0, 0)
        self.mouse_down = False
        
        # For pause/game over handling
        self.last_loaded_save_name = None
        self.last_loaded_mode = None

    def setup_players(self, selected_slots):
        """Initialize players and bots from slot configuration."""
        self.players.clear()
        
        PLAYER_CONTROLS = {
            1: {
                'up': pygame.K_w,
                'down': pygame.K_s,
                'left': pygame.K_a,
                'right': pygame.K_d,
                'shoot': [pygame.K_SPACE, pygame.K_f]
            },
            2: {
                'up': pygame.K_UP,
                'down': pygame.K_DOWN,
                'left': pygame.K_LEFT,
                'right': pygame.K_RIGHT,
                'shoot': [pygame.K_k]
            }
        }
        
        if not selected_slots:
            player = Player(Vector2(0, 0), 1)
            player.controls = PLAYER_CONTROLS.get(1, {})
            self.players.append(player)
            return
        
        player_count = sum(1 for s in selected_slots if s.get('type') == 'player')
        is_multiplayer = player_count >= 2
        
        player_index = 0
        for slot in selected_slots:
            slot_type = slot.get('type', 'player')
            slot_id = slot.get('id', 1)
            slot_name = slot.get('name', f'Player {slot_id}')
            pos_x = slot.get('pos_x', 0)
            pos_y = slot.get('pos_y', 0)
            color = tuple(slot.get('color', [40, 120, 255]))
            
            if slot_type == 'player':
                player_index += 1
                player = Player(Vector2(pos_x, pos_y), slot_id, color=color)
                player.controls = PLAYER_CONTROLS.get(player_index, PLAYER_CONTROLS.get(1, {}))
                player.multi_player_mode = is_multiplayer
                player.can_go_down = is_multiplayer
                self.players.append(player)
            elif slot_type == 'bot':
                bot = HelperBot(Vector2(pos_x, pos_y), slot_id, color=color)
                bot.multi_player_mode = is_multiplayer
                bot.can_go_down = is_multiplayer
                self.players.append(bot)
        
        print(f"[GameEngine] Setup {len(self.players)} players (multiplayer: {is_multiplayer})")

    def setup_world(self):
        """Initialize world state."""
        self.zombies.clear()
        self.bullets.clear()
        self.world = World()
        print("[GameEngine] World initialized")

    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            info = pygame.display.Info()
            self.screen_width, self.screen_height = info.current_w, info.current_h
        else:
            self.screen_width, self.screen_height = 1200, 800
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))

    def update_camera(self):
        """Update camera to follow players."""
        if not self.players:
            return
        alive_players = [p for p in self.players if p.state == PlayerState.ALIVE]
        downed_players = [p for p in self.players if p.state == PlayerState.DOWNED]
        
        if len(self.players) == 1:
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
        """Handle pause menu button clicks."""
        
        # Save input dialogi bosilganda
        if hasattr(self, 'pause_save_input_active') and self.pause_save_input_active:
            if hasattr(self, 'pause_save_dialog_input') and self.pause_save_dialog_input.collidepoint(pos):
                # Input fokusini berish
                return
            
            if hasattr(self, 'pause_save_dialog_cancel') and self.pause_save_dialog_cancel.collidepoint(pos):
                self.pause_save_input_active = False
                self.pause_save_input_text = ""
                return
            
            if hasattr(self, 'pause_save_dialog_save') and self.pause_save_dialog_save.collidepoint(pos):
                if self.pause_save_input_text.strip():
                    # O'yinni saqlash
                    from Moduls.default.save_load import save_game
                    try:
                        # Default modulga saqlash
                        save_game(self, self.pause_save_input_text, self.mode, modul_name="default")
                        print(f"[INFO] O'yin '{self.pause_save_input_text}' nomida saqlandi")
                    except Exception as e:
                        print(f"[ERROR] Save xatosi: {e}")
                self.pause_save_input_active = False
                self.pause_save_input_text = ""
                return
        
        # Regular pause menu buttons
        if hasattr(self, 'pause_menu_buttons'):
            for btn_name, btn_rect in self.pause_menu_buttons.items():
                if btn_rect.collidepoint(pos):
                    if btn_name == "continue":
                        self.state = "PLAYING"
                        self.pause_bg_green = False
                        print("[INFO] O'yin davom etdi (Resume)")
                    elif btn_name == "save":
                        self.pause_save_input_active = True
                        self.pause_save_input_text = ""
                        print("[INFO] Save inputi ochildi")
                    elif btn_name == "restart":
                        self.restart_game()
                        self.state = "PLAYING"
                        self.pause_bg_green = False
                        print("[INFO] O'yin qayta boshlandi (Restart)")
                    elif btn_name == "main menu":
                        self.state = "MAIN_MENU"
                        self.pause_bg_green = False
                        print("[INFO] Asosiy menyuga qaytildi")
                    return

    def handle_game_over_click(self, pos):
        """Handle game over menu button clicks."""
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
            self.state = "MAIN_MENU"
            return

    def restart_game(self):
        """Restart the game."""
        print("[INFO] O'yin qayta boshlandi")
        self.setup_players(getattr(self, '_last_selected_slots', [{'type': 'player', 'id': 1, 'name': 'Player 1', 'pos_x': 0, 'pos_y': 0}]))
        self.setup_world()
        self.state = "PLAYING"
        self.game_start_time = pygame.time.get_ticks()

    def update_day_night_cycle(self):
        """Update day/night cycle and zombie strength."""
        day_length = 15 * 60 * 1000
        day_progress = (self.game_time % day_length) / day_length
        new_day = (self.game_time // day_length) + 1
        if new_day != self.current_day:
            self.current_day = new_day
            if self.current_day % 7 == 0:
                self.zombie_strength += 1
        self.is_night = day_progress >= 8 / 15

    def update_players(self, dt):
        """Update all players."""
        alive_positions = [p.position for p in self.players if p.state == PlayerState.ALIVE]
        for player in self.players:
            if player.state != PlayerState.DEAD:
                other_players = [p for p in self.players if p.id != player.id]
                new_bullets = player.update(dt, self.world.power_ups, self.zombies, other_players)
                self.bullets.extend(new_bullets)
        self.world.update(alive_positions)

    def update_zombies(self, dt):
        """Update all zombies."""
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
        """Update all bullets."""
        for bullet in self.bullets[:]:
            if not bullet.active:
                self.bullets.remove(bullet)
                continue
            bullet.update(dt)

    def spawn_zombies(self):
        """Spawn zombies based on game state and difficulty."""
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
        """Spawn a single zombie."""
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
        """Spawn power-ups when enough zombies are killed."""
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
        """Check and handle collisions between bullets/zombies and players/powerups."""
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

    def check_game_over(self):
        """Check if game is over (victory or all players dead/downed)."""
        alive_players = [p for p in self.players if p.state == PlayerState.ALIVE]
        downed_players = [p for p in self.players if p.state == PlayerState.DOWNED]
        dead_players = [p for p in self.players if p.state == PlayerState.DEAD]
        max_level = max((p.level for p in self.players), default=1)
        
        if max_level >= 999:
            self.state = "GAME_OVER"
            print("[INFO] O'yin tugadi (VICTORY)")
            return
        
        if len(self.players) > 0:
            if len(dead_players) == len(self.players):
                self.state = "GAME_OVER"
                print("[INFO] O'yin tugadi (GAME OVER)")
                return

    def handle_events(self):
        """Handle all input events."""
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                # Save input dialog faoliyat bo'lsa
                if hasattr(self, 'pause_save_input_active') and self.pause_save_input_active:
                    if event.key == pygame.K_RETURN:
                        # Enter bosilgan - save dialog ko'rinadi
                        if self.pause_save_input_text.strip():
                            from Moduls.default.save_load import save_game
                            try:
                                save_game(self, self.pause_save_input_text, self.mode, modul_name="default")
                                print(f"[INFO] O'yin '{self.pause_save_input_text}' nomida saqlandi")
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
        """Handle mouse clicks in pause/gameover menus."""
        if self.state == "PAUSED":
            self.handle_pause_click(pos)
        elif self.state == "GAME_OVER":
            self.handle_game_over_click(pos)

    def step_update(self, dt):
        """Update game logic (one frame)."""
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

    def render_pause_menu(self):
        """Render pause menu overlay."""
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
        
        # Save menu input
        if not hasattr(self, 'pause_save_input_active'):
            self.pause_save_input_active = False
            self.pause_save_input_text = ""
        
        if self.pause_save_input_active:
            # Save dialog
            dialog_width = 400
            dialog_height = 180
            dialog_x = center_x - dialog_width // 2
            dialog_y = 300
            pygame.draw.rect(self.screen, (50, 50, 50), (dialog_x, dialog_y, dialog_width, dialog_height))
            
            # Title
            save_title = self.font.render("Save Game", True, WHITE)
            self.screen.blit(save_title, (dialog_x + 20, dialog_y + 10))
            
            # Input box
            input_box_rect = pygame.Rect(dialog_x + 20, dialog_y + 60, dialog_width - 40, 40)
            pygame.draw.rect(self.screen, WHITE, input_box_rect, 2)
            input_text = self.small_font.render(self.pause_save_input_text, True, WHITE)
            self.screen.blit(input_text, (input_box_rect.x + 5, input_box_rect.y + 8))
            
            # Save button
            save_btn_rect = pygame.Rect(dialog_x + 20, dialog_y + 110, 170, 40)
            pygame.draw.rect(self.screen, (60, 180, 70), save_btn_rect, border_radius=8)
            save_btn_text = self.small_font.render("Save", True, WHITE)
            self.screen.blit(save_btn_text, save_btn_rect.move(50, 10))
            
            # Cancel button
            cancel_btn_rect = pygame.Rect(dialog_x + 210, dialog_y + 110, 170, 40)
            pygame.draw.rect(self.screen, (200, 100, 100), cancel_btn_rect, border_radius=8)
            cancel_btn_text = self.small_font.render("Cancel", True, WHITE)
            self.screen.blit(cancel_btn_text, cancel_btn_rect.move(45, 10))
            
            self.pause_save_dialog_input = input_box_rect
            self.pause_save_dialog_save = save_btn_rect
            self.pause_save_dialog_cancel = cancel_btn_rect
            return
        
        buttons = [
            ("Continue", 350),
            ("Save", 420),
            ("Restart", 490),
            ("Main Menu", 560)
        ]
        
        # Use pre-initialized buttons from pause_menu_buttons dict
        if not hasattr(self, 'pause_menu_buttons') or not self.pause_menu_buttons:
            self._init_pause_menu_buttons()
        
        for text, y in buttons:
            btn_rect = pygame.Rect(center_x - button_width // 2, y, button_width, button_height)
            pygame.draw.rect(self.screen, (74, 124, 89), btn_rect)
            rendered_text = self.small_font.render(text, True, WHITE)
            text_rect = rendered_text.get_rect(center=(center_x, y + button_height // 2))
            self.screen.blit(rendered_text, text_rect)

    def render_game_over(self):
        """Render game over screen."""
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill(BLACK)
        overlay.set_alpha(200)
        self.screen.blit(overlay, (0, 0))
        
        max_level = max((p.level for p in self.players), default=1)
        is_victory = max_level >= 999
        title_text = "VICTORY!" if is_victory else "GAME OVER"
        title_color = GREEN if is_victory else RED
        
        title = self.font.render(title_text, True, title_color)
        title_rect = title.get_rect(center=(self.screen_width // 2, 200))
        self.screen.blit(title, title_rect)
        
        days = self.current_day
        total_kills = sum(p.zombie_kills for p in self.players)
        stats = [
            f"Days Survived: {days}",
            f"Zombies Killed: {total_kills}",
            f"Max Level Reached: {max_level}",
        ]
        
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

    def _init_pause_menu_buttons(self):
        """Initialize pause menu buttons (called once when entering PAUSED state)."""
        center_x = self.screen_width // 2
        button_width = 150
        button_height = 50
        
        self.pause_menu_buttons = {
            "continue": pygame.Rect(center_x - button_width // 2, 350, button_width, button_height),
            "save": pygame.Rect(center_x - button_width // 2, 420, button_width, button_height),
            "restart": pygame.Rect(center_x - button_width // 2, 490, button_width, button_height),
            "main menu": pygame.Rect(center_x - button_width // 2, 560, button_width, button_height),
        }

    def render(self):
        """Render the game or menu overlay."""
        if self.state == "PLAYING":
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
            
            self.render_hud()
        
        elif self.state == "PAUSED":
            self.render_pause_menu()
        
        elif self.state == "GAME_OVER":
            self.render_game_over()

    def render_hud(self):
        """Render heads-up display with player stats."""
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
            if player2:
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

    def run(self, selected_slots):
        """Main game loop."""
        self._last_selected_slots = selected_slots
        self.setup_players(selected_slots)
        self.setup_world()
        
        running = True
        while running:
            running = self.handle_events()
            
            dt = self.clock.tick(60) / 1000.0
            self.game_time = pygame.time.get_ticks() - self.game_start_time
            
            self.step_update(dt)
            
            self.render()
            pygame.display.flip()
            
            if self.state == "MAIN_MENU":
                running = False


def run_game(screen, width, height, selected_slots):
    """Compatibility wrapper: create a GameEngine and run it."""
    engine = GameEngine(screen, width, height)
    engine.run(selected_slots)