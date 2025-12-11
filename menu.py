import sys
import os
import random
import re
import pygame
from loading import LoadingScreen
from core import WHITE, BLACK, FPS
from Moduls.default.save_load import save_game, delete_save, list_saved_games, load_game_data, load_from_data, save_last_session, AUTOSAVE_PATH
from network import HostServer, Client, get_local_ip
from session import Session
import importlib
import Moduls.default.game_logic as game_logic

MODULS_PATH = os.path.join(os.path.dirname(__file__), 'Moduls')


def get_modul_dirs(require_modul_network=False):
    """Return a list of available module directory names."""
    mods = []
    for d in os.listdir(MODULS_PATH):
        full_dir = os.path.join(MODULS_PATH, d)
        if os.path.isdir(full_dir):
            has_logic = os.path.exists(os.path.join(full_dir, 'game_logic.py'))
            has_net = os.path.exists(os.path.join(full_dir, 'modul_network.py'))
            if has_logic and (not require_modul_network or has_net):
                mods.append(d)
    return mods


class Menu:
    def __init__(self, screen=None, screen_width=1200, screen_height=800):
        self.screen_width = screen_width
        self.screen_height = screen_height
        if screen is not None:
            self.screen = screen
        else:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Unknown World: Infinite - Menu")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)

        # Menu state
        self.state = "MAIN_MENU"
        self.mouse_down = False
        self.mouse_pos = (0, 0)

        # For loading
        self.loading_active = False
        self.loading_percent = 0
        self.loading_selected_slots = []
        self.loading_selected_modul = "default"
        
        # Save/load UI
        self.save_input_active = False
        self.save_input_text = ""
        self.show_save_success = False
        self.save_slot_full = False
        self.load_menu_active = False
        self.available_saves = []
        self.selected_save = None
        self.load_input_text = ""
        self.load_menu_page = 0

        # Multiplayer/session
        self.session = Session()
        self.host_server = None
        self.client = None
        self.is_host = False
        self.is_client = False
        self.host_ip = get_local_ip()

        # Slots & modul selection
        self.selected_modul = "default"
        self.selected_create_modul = "default"
        self.load_selected_modul = "default"
        self.load_modul_dropdown_open = False
        
        # Game engine pointer
        self.game_engine = None
        
        # ✅ Slot sistemasi - Default holatda faqat P1
        self.selected_slots = [
            {'type': 'player', 'id': 1, 'name': 'Player 1', 'pos_x': 0, 'pos_y': 0, 'color': [40, 120, 255]}
        ]
        
        # Add menu
        self.add_menu_active = False
        self.add_menu_slot_index = -1  # Qaysi slotga qo'shmoqchi
        self.add_menu_rects = []

    def ensure_player1_exists(self):
        """✅ Har doim P1 mavjudligini ta'minlaydi"""
        has_p1 = any(s.get('id') == 1 and s.get('type') == 'player' for s in self.selected_slots)
        if not has_p1:
            self.selected_slots = [
                {'type': 'player', 'id': 1, 'name': 'Player 1', 'pos_x': 0, 'pos_y': 0, 'color': [40, 120, 255]}
            ] + self.selected_slots

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.mouse_down = True
                    self.mouse_pos = event.pos
                    self.handle_mouse_click(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.mouse_down = False
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                if event.key == pygame.K_ESCAPE:
                    if self.state == "PLAYING":
                        self.state = "MAIN_MENU"
                # Text input for join IP and load name
                if self.state == "JOIN_INPUT_MENU":
                    if event.key == pygame.K_RETURN:
                        self.join_ip_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.join_ip_value = getattr(self, 'join_ip_value', '')[:-1]
                    else:
                        ch = event.unicode
                        if ch and len(getattr(self, 'join_ip_value', '')) < 40:
                            self.join_ip_value = getattr(self, 'join_ip_value', '') + ch
                if self.state == "LOAD_MENU" and getattr(self, 'load_menu_btns', None):
                    if event.key == pygame.K_RETURN:
                        self.load_input_text = getattr(self, 'load_input_text', '')
                    elif event.key == pygame.K_BACKSPACE:
                        self.load_input_text = getattr(self, 'load_input_text', '')[:-1]
                    else:
                        ch = event.unicode
                        if ch and len(getattr(self, 'load_input_text', '')) < 40 and ch.isalnum():
                            self.load_input_text = getattr(self, 'load_input_text', '') + ch
        return True

    def handle_mouse_click(self, pos):
        mx, my = pos
        if self.state == "MAIN_MENU":
            self.handle_main_menu_click(pos)
        elif self.state == "PLAY_MENU":
            self.handle_play_menu_click(pos)
        elif self.state == "LOAD_MENU":
            self.handle_load_menu_click(pos)
        elif self.state == "MULTIPLAYER_MENU":
            self.handle_multiplayer_menu_click(pos)
        elif self.state == "CREATE_MULTIPLAYER_MENU":
            self.handle_create_multiplayer_menu_click(pos)
        elif self.state == "JOIN_INPUT_MENU":
            self.handle_join_input_mouse_click(pos)
        elif self.state == "CLIENT_MENU":
            self.handle_client_menu_mouse_click(pos)

    def start_loading(self, selected_slots, selected_modul="default"):
        if self.loading_active:
            return
        self.loading_active = True
        self.loading_selected_slots = list(selected_slots)
        self.loading_selected_modul = selected_modul
        # Loading qilish
        self._do_loading()

    def _do_loading(self):
        try:
            if getattr(self, 'selected_save', None):
                load_selected_modul = getattr(self, 'load_selected_modul', 'default')
                self._do_loading_from_save(self.selected_save, modul_name=load_selected_modul)
            else:
                # Game engine setup
                modul_name = self.loading_selected_modul if self.loading_selected_modul else "default"
                try:
                    modul_loading_path = f"Moduls.{modul_name}.modul_loading"
                    modul_loading = importlib.import_module(modul_loading_path)
                except Exception as e:
                    print(f"[loading] ERROR importing modul_loading for {modul_name}: {e}")
                    modul_loading = importlib.import_module("Moduls.default.modul_loading")
                
                # Engine setup
                modul_game_logic = importlib.import_module(f"Moduls.{modul_name}.game_logic")
                if hasattr(modul_game_logic, "GameEngine"):
                    engine = modul_game_logic.GameEngine(self.screen, self.screen_width, self.screen_height)
                    engine.setup_players(self.loading_selected_slots)
                    engine.setup_world()
                    self.game_engine = engine
                    self.state = "PLAYING"
        except Exception as e:
            print(f"[MENU] Loading failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.loading_active = False

    def _do_loading_from_save(self, save_name, modul_name="default"):
        """Load saved DB and start a GameEngine with the loaded data."""
        try:
            data = load_game_data(save_name, modul_name=modul_name)
            if data is None:
                print(f"[MENU] Save '{save_name}' not found or corrupted")
                return
            engine = game_logic.GameEngine(self.screen, self.screen_width, self.screen_height)
            load_from_data(engine, data)
            self.game_engine = engine
            self.state = "PLAYING"
        except Exception as e:
            print(f"[MENU] _do_loading_from_save failed: {e}")

    # ==================== MAIN MENU ====================
    def render_main_menu(self):
        self.screen.fill((45, 80, 22))
        title = self.font.render("Unknown World: Infinite", True, WHITE)
        title_rect = title.get_rect(center=(self.screen_width // 2, 180))
        self.screen.blit(title, title_rect)
        
        center_x = self.screen_width // 2
        button_width = 260
        button_height = 70
        gap = 40
        start_y = 320

        play_rect = pygame.Rect(center_x - button_width // 2, start_y, button_width, button_height)
        pygame.draw.rect(self.screen, (24, 134, 42), play_rect, border_radius=18)
        play_text = self.font.render("Play", True, WHITE)
        self.screen.blit(play_text, play_text.get_rect(center=play_rect.center))

        multi_rect = pygame.Rect(center_x - button_width // 2, start_y + button_height + gap, button_width, button_height)
        pygame.draw.rect(self.screen, (70, 160, 230), multi_rect, border_radius=18)
        multi_text = self.font.render("Multiplayer", True, WHITE)
        self.screen.blit(multi_text, multi_text.get_rect(center=multi_rect.center))

        exit_rect = pygame.Rect(center_x - button_width // 2, start_y + 2 * (button_height + gap), button_width, button_height)
        pygame.draw.rect(self.screen, (200, 100, 100), exit_rect, border_radius=18)
        exit_text = self.font.render("Exit", True, WHITE)
        self.screen.blit(exit_text, exit_text.get_rect(center=exit_rect.center))

    def handle_main_menu_click(self, pos):
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
            # ✅ Play menyusiga o'tishda P1 mavjudligini tekshirish
            self.ensure_player1_exists()
            self.state = "PLAY_MENU"
        elif multi_rect.collidepoint(mx, my):
            self.state = "MULTIPLAYER_MENU"
        elif exit_rect.collidepoint(mx, my):
            pygame.quit()
            sys.exit()

    # ==================== PLAY MENU ====================
    def render_play_menu(self):
        self.screen.fill((70, 160, 230))
        center_x = self.screen_width // 2
        
        # Modul tanlash dropdown
        dropdown_y = 30
        dropdown_width = 200
        dropdown_height = 40
        dropdown_x = center_x - dropdown_width // 2
        
        available_moduls = get_modul_dirs()
        dropdown_rect = pygame.Rect(dropdown_x, dropdown_y, dropdown_width, dropdown_height)
        pygame.draw.rect(self.screen, (100, 100, 100), dropdown_rect, border_radius=8)
        
        # Tanlangan modul ko'rsatish
        modul_text = self.small_font.render(f"Module: {self.selected_modul}", True, WHITE)
        self.screen.blit(modul_text, (dropdown_x + 10, dropdown_y + 8))
        
        # Dropdown asl dropdown o'rniga style menu
        if not hasattr(self, 'modul_dropdown_open'):
            self.modul_dropdown_open = False
            self.modul_dropdown_rect = dropdown_rect
        
        # Dropdown ochilgan bo'lsa variantlarni ko'rsatish
        if self.modul_dropdown_open:
            modul_rects = []
            for idx, mod in enumerate(available_moduls):
                mod_y = dropdown_y + dropdown_height + 10 + idx * 30
                mod_rect = pygame.Rect(dropdown_x, mod_y, dropdown_width, 28)
                color = (60, 150, 230) if mod == self.selected_modul else (80, 80, 80)
                pygame.draw.rect(self.screen, color, mod_rect, border_radius=4)
                mod_name_text = self.small_font.render(mod, True, WHITE)
                self.screen.blit(mod_name_text, (dropdown_x + 10, mod_y + 5))
                modul_rects.append((mod, mod_rect))
            self.modul_dropdown_rects = modul_rects
        
        # Title
        title = self.font.render("Select Players", True, WHITE)
        self.screen.blit(title, (center_x - title.get_width() // 2, 130))
        
        # ✅ Slotlar - 4 ta slot
        slot_width = 200
        slot_height = 60
        slot_gap = 20
        slot_start_y = 210
        
        # Slot rectangles storage
        self.play_slot_rects = []
        self.play_add_btn_rects = []
        self.play_remove_btn_rects = []
        
        for i in range(4):
            slot_x = center_x - slot_width // 2
            slot_y = slot_start_y + i * (slot_height + slot_gap)
            slot_rect = pygame.Rect(slot_x, slot_y, slot_width, slot_height)
            
            # ✅ Slotdagi ma'lumotni olish
            if i < len(self.selected_slots):
                slot_data = self.selected_slots[i]
                slot_name = slot_data.get('name', 'Unknown')
                slot_type = slot_data.get('type', 'player')
                slot_id = slot_data.get('id', 0)
                
                # Slot color based on type
                if slot_type == 'player':
                    color = (24, 134, 42) if slot_id == 1 else (60, 150, 230)
                else:  # bot
                    color = (200, 120, 50)
                
                pygame.draw.rect(self.screen, color, slot_rect, border_radius=12)
                
                # Slot text
                text = self.small_font.render(slot_name, True, WHITE)
                text_rect = text.get_rect(center=(slot_rect.centerx, slot_rect.centery))
                self.screen.blit(text, text_rect)
                
                # ✅ Remove button (X) - faqat P1 emas bo'lsa
                if not (slot_type == 'player' and slot_id == 1):
                    remove_btn_size = 24
                    remove_btn_x = slot_rect.right - remove_btn_size - 8
                    remove_btn_y = slot_rect.top + (slot_height - remove_btn_size) // 2
                    remove_btn_rect = pygame.Rect(remove_btn_x, remove_btn_y, remove_btn_size, remove_btn_size)
                    
                    pygame.draw.rect(self.screen, (200, 50, 50), remove_btn_rect, border_radius=6)
                    x_text = self.small_font.render("X", True, WHITE)
                    self.screen.blit(x_text, x_text.get_rect(center=remove_btn_rect.center))
                    
                    self.play_remove_btn_rects.append((i, remove_btn_rect))
            
            else:
                # ✅ Bo'sh slot - Add button ko'rsatish
                pygame.draw.rect(self.screen, (180, 180, 180), slot_rect, border_radius=12)
                
                # Add button
                add_btn_width = 80
                add_btn_height = 36
                add_btn_x = slot_rect.centerx - add_btn_width // 2
                add_btn_y = slot_rect.centery - add_btn_height // 2
                add_btn_rect = pygame.Rect(add_btn_x, add_btn_y, add_btn_width, add_btn_height)
                
                pygame.draw.rect(self.screen, (60, 180, 70), add_btn_rect, border_radius=8)
                add_text = self.small_font.render("+ Add", True, WHITE)
                self.screen.blit(add_text, add_text.get_rect(center=add_btn_rect.center))
                
                self.play_add_btn_rects.append((i, add_btn_rect))
            
            self.play_slot_rects.append(slot_rect)
        
        # ✅ Bottom buttons
        btn_width = 140
        btn_height = 50
        btn_gap = 30
        btn_y = slot_start_y + 4 * (slot_height + slot_gap) + 40
        total_width = btn_width * 3 + btn_gap * 2
        start_x = center_x - total_width // 2

        start_rect = pygame.Rect(start_x, btn_y, btn_width, btn_height)
        pygame.draw.rect(self.screen, (24, 134, 42), start_rect, border_radius=10)
        start_text = self.small_font.render("Start", True, WHITE)
        self.screen.blit(start_text, start_text.get_rect(center=start_rect.center))

        load_rect = pygame.Rect(start_x + btn_width + btn_gap, btn_y, btn_width, btn_height)
        pygame.draw.rect(self.screen, (70, 100, 200), load_rect, border_radius=10)
        load_text = self.small_font.render("Load", True, WHITE)
        self.screen.blit(load_text, load_text.get_rect(center=load_rect.center))

        back_rect = pygame.Rect(start_x + 2 * (btn_width + btn_gap), btn_y, btn_width, btn_height)
        pygame.draw.rect(self.screen, (200, 100, 100), back_rect, border_radius=10)
        back_text = self.small_font.render("Back", True, WHITE)
        self.screen.blit(back_text, back_text.get_rect(center=back_rect.center))
        
        self.play_bottom_buttons = {
            "start": start_rect,
            "load": load_rect,
            "back": back_rect
        }

    def render_add_menu(self):
        """✅ Add menu - O'yinchi yoki Bot tanlash"""
        menu_width = int(self.screen_width * 0.8)
        menu_height = 140
        menu_x = self.screen_width // 2 - menu_width // 2
        menu_y = self.screen_height // 2 - menu_height // 2
        
        # Overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(120)
        self.screen.blit(overlay, (0, 0))
        
        # Menu background
        pygame.draw.rect(self.screen, (220, 220, 220), (menu_x, menu_y, menu_width, menu_height), border_radius=16)
        
        # Title
        title = self.small_font.render("Select Player or Bot", True, (40, 40, 40))
        self.screen.blit(title, (menu_x + 20, menu_y + 15))
        
        # Options
        slot_w = 90
        slot_h = 70
        gap = 15
        start_x = menu_x + 20
        start_y = menu_y + 50
        
        self.add_menu_rects = []
        
        # ✅ Mavjud variantlar
        options = [
            {'type': 'player', 'id': 2, 'name': 'Player 2', 'color': [255, 120, 40]},
            {'type': 'bot', 'id': 101, 'name': 'Bot 1', 'color': [200, 120, 50]},
            {'type': 'bot', 'id': 102, 'name': 'Bot 2', 'color': [200, 120, 50]},
            {'type': 'bot', 'id': 103, 'name': 'Bot 3', 'color': [200, 120, 50]},
            {'type': 'bot', 'id': 104, 'name': 'Bot 4', 'color': [200, 120, 50]},
            {'type': 'bot', 'id': 105, 'name': 'Bot 5', 'color': [200, 120, 50]},
        ]
        
        for i, obj in enumerate(options):
            slot_x = start_x + i * (slot_w + gap)
            slot_rect = pygame.Rect(slot_x, start_y, slot_w, slot_h)
            
            # ✅ Allaqachon tanlangan ekanligini tekshirish
            is_selected = any(s.get('id') == obj['id'] for s in self.selected_slots)
            
            # Color
            if is_selected:
                color = (140, 140, 140)  # Gray for already selected
            elif obj['type'] == 'player':
                color = (60, 150, 230)
            else:
                color = (200, 120, 50)
            
            pygame.draw.rect(self.screen, color, slot_rect, border_radius=10)
            
            # Text
            name_parts = obj['name'].split()
            line1 = self.small_font.render(name_parts[0], True, WHITE)
            line2 = self.small_font.render(name_parts[1] if len(name_parts) > 1 else "", True, WHITE)
            
            self.screen.blit(line1, line1.get_rect(center=(slot_rect.centerx, slot_rect.centery - 10)))
            self.screen.blit(line2, line2.get_rect(center=(slot_rect.centerx, slot_rect.centery + 10)))
            
            self.add_menu_rects.append((obj, slot_rect, is_selected))
        
        # Close button (X)
        close_btn_size = 30
        close_btn_x = menu_x + menu_width - close_btn_size - 10
        close_btn_y = menu_y + 10
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        pygame.draw.rect(self.screen, (200, 50, 50), close_btn_rect, border_radius=6)
        x_text = self.font.render("X", True, WHITE)
        self.screen.blit(x_text, x_text.get_rect(center=close_btn_rect.center))
        self.add_menu_close_btn = close_btn_rect

    def handle_play_menu_click(self, pos):
        mx, my = pos
        
        # ✅ Modul dropdown
        if hasattr(self, 'modul_dropdown_rect') and self.modul_dropdown_rect.collidepoint(mx, my):
            self.modul_dropdown_open = not self.modul_dropdown_open
            return
        
        # Dropdown elem tanlandi
        if self.modul_dropdown_open and hasattr(self, 'modul_dropdown_rects'):
            for modul_name, mod_rect in self.modul_dropdown_rects:
                if mod_rect.collidepoint(mx, my):
                    self.selected_modul = modul_name
                    self.modul_dropdown_open = False
                    return
        
        # Dropdown yopamiz agar boshqa joyni bosgansa
        self.modul_dropdown_open = False
        
        # ✅ Add menu active bo'lsa
        if self.add_menu_active:
            # Close button
            if hasattr(self, 'add_menu_close_btn') and self.add_menu_close_btn.collidepoint(pos):
                self.add_menu_active = False
                return
            
            # Option selection
            for obj, slot_rect, is_selected in self.add_menu_rects:
                if slot_rect.collidepoint(pos):
                    if not is_selected:
                        # ✅ Tanlangan slotga qo'shish
                        new_slot = {
                            'type': obj['type'],
                            'id': obj['id'],
                            'name': obj['name'],
                            'pos_x': 0,
                            'pos_y': 0,
                            'color': obj.get('color', [200, 120, 50])
                        }
                        
                        if self.add_menu_slot_index < len(self.selected_slots):
                            self.selected_slots.insert(self.add_menu_slot_index, new_slot)
                        else:
                            self.selected_slots.append(new_slot)
                        
                        print(f"[MENU] Added {obj['name']} to slot {self.add_menu_slot_index}")
                    
                    self.add_menu_active = False
                    return
            return
        
        # ✅ Add button clicks
        for i, add_btn_rect in self.play_add_btn_rects:
            if add_btn_rect.collidepoint(mx, my):
                self.add_menu_active = True
                self.add_menu_slot_index = i
                return
        
        # ✅ Remove button clicks
        for i, remove_btn_rect in self.play_remove_btn_rects:
            if remove_btn_rect.collidepoint(mx, my):
                if i < len(self.selected_slots):
                    removed = self.selected_slots.pop(i)
                    print(f"[MENU] Removed {removed['name']} from slot {i}")
                    # ✅ P1 ni qayta qo'shish
                    self.ensure_player1_exists()
                return
        
        # ✅ Bottom buttons
        if hasattr(self, 'play_bottom_buttons'):
            if self.play_bottom_buttons["start"].collidepoint(mx, my):
                self.ensure_player1_exists()
                self.start_loading(self.selected_slots, self.selected_modul)
            elif self.play_bottom_buttons["load"].collidepoint(mx, my):
                self.state = "LOAD_MENU"
            elif self.play_bottom_buttons["back"].collidepoint(mx, my):
                self.state = "MAIN_MENU"

    # ==================== LOAD MENU ====================
    def render_load_menu(self):
        self.screen.fill((40, 40, 60))
        center_x = self.screen_width // 2

        # Modul tanlash dropdown
        dropdown_y = 20
        dropdown_width = 200
        dropdown_height = 40
        dropdown_x = center_x - dropdown_width // 2
        
        available_moduls = get_modul_dirs()
        dropdown_rect = pygame.Rect(dropdown_x, dropdown_y, dropdown_width, dropdown_height)
        pygame.draw.rect(self.screen, (100, 100, 100), dropdown_rect, border_radius=8)
        
        # Tanlangan modul ko'rsatish
        modul_text = self.small_font.render(f"Module: {getattr(self, 'load_selected_modul', 'default')}", True, WHITE)
        self.screen.blit(modul_text, (dropdown_x + 10, dropdown_y + 8))
        
        # Dropdown asl dropdown o'rniga style menu
        if not hasattr(self, 'load_modul_dropdown_open'):
            self.load_modul_dropdown_open = False
            self.load_modul_dropdown_rect = dropdown_rect
        
        # Dropdown ochilgan bo'lsa variantlarni ko'rsatish
        if self.load_modul_dropdown_open:
            modul_rects = []
            for idx, mod in enumerate(available_moduls):
                mod_y = dropdown_y + dropdown_height + 10 + idx * 30
                mod_rect = pygame.Rect(dropdown_x, mod_y, dropdown_width, 28)
                current_modul = getattr(self, 'load_selected_modul', 'default')
                color = (60, 150, 230) if mod == current_modul else (80, 80, 80)
                pygame.draw.rect(self.screen, color, mod_rect, border_radius=4)
                mod_name_text = self.small_font.render(mod, True, WHITE)
                self.screen.blit(mod_name_text, (dropdown_x + 10, mod_y + 5))
                modul_rects.append((mod, mod_rect))
            self.load_modul_dropdown_rects = modul_rects

        # Input box
        input_y = 80
        input_w = 260
        input_h = 40
        input_rect = pygame.Rect(center_x - input_w // 2, input_y, input_w, input_h)
        pygame.draw.rect(self.screen, WHITE, input_rect, 2)
        input_text = self.small_font.render(getattr(self, "load_input_text", ""), True, WHITE)
        self.screen.blit(input_text, (input_rect.x + 10, input_rect.y + 8))

        # Buttons
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
        
        self.screen.blit(self.small_font.render("Delete", True, WHITE), del_btn_rect.move(20, 8))
        self.screen.blit(self.small_font.render("Load", True, WHITE), load_btn_rect.move(30, 8))
        self.screen.blit(self.small_font.render("Back", True, WHITE), back_btn_rect.move(30, 8))

        # Save list - tanlangan modul uchun savlarni ko'rsatish
        load_selected_modul = getattr(self, 'load_selected_modul', 'default')
        search = getattr(self, "load_input_text", "").lower()
        all_saves = list_saved_games(modul_name=load_selected_modul)
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
            
            name_text = self.font.render(f"{i + page * page_size}. {save_name}", True, WHITE)
            self.screen.blit(name_text, slot_rect.move(20, 10))
            
            try:
                data = load_game_data(save_name, modul_name=load_selected_modul)
                player_count = sum(1 for p in data.get("player", []) if p.get("type", "player") == "player")
                bot_count = sum(1 for p in data.get("player", []) if p.get("type", "player") == "bot")
                play_time = data.get("meta", {}).get("game_time", 0)
                minutes = play_time // 60000
                hours = minutes // 60
                minutes = minutes % 60
                time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
                info = f"Players: {player_count} | Bots: {bot_count} | Time: {time_str}"
            except Exception:
                info = "Corrupted or missing data"
            info_text = self.small_font.render(info, True, WHITE)
            self.screen.blit(info_text, slot_rect.move(20, 40))

    def handle_load_menu_click(self, pos):
        mx, my = pos
        
        # ✅ Modul dropdown
        if hasattr(self, 'load_modul_dropdown_rect') and self.load_modul_dropdown_rect.collidepoint(mx, my):
            self.load_modul_dropdown_open = not self.load_modul_dropdown_open
            return
        
        # Dropdown elem tanlandi
        if self.load_modul_dropdown_open and hasattr(self, 'load_modul_dropdown_rects'):
            for modul_name, mod_rect in self.load_modul_dropdown_rects:
                if mod_rect.collidepoint(mx, my):
                    self.load_selected_modul = modul_name
                    self.load_modul_dropdown_open = False
                    self.selected_save = None  # Yangi modul tanlanganda selected_save reset qilish
                    return
        
        # Dropdown yopamiz agar boshqa joyni bosgansa
        self.load_modul_dropdown_open = False
        
        # Button clicks
        if hasattr(self, 'load_menu_btns'):
            if self.load_menu_btns["delete"].collidepoint(pos):
                if hasattr(self, 'selected_save') and self.selected_save:
                    load_selected_modul = getattr(self, 'load_selected_modul', 'default')
                    delete_save(self.selected_save, modul_name=load_selected_modul)
                    self.selected_save = None
            elif self.load_menu_btns["load"].collidepoint(pos):
                if hasattr(self, 'selected_save') and self.selected_save:
                    load_selected_modul = getattr(self, 'load_selected_modul', 'default')
                    self.start_loading(self.selected_slots, "load_save")
            elif self.load_menu_btns["back"].collidepoint(pos):
                self.state = "PLAY_MENU"
        
        # Slot selection
        if hasattr(self, 'load_menu_slots_rects'):
            for save_name, slot_rect in self.load_menu_slots_rects:
                if slot_rect.collidepoint(mx, my):
                    self.selected_save = save_name

    # ==================== MULTIPLAYER MENU ====================
    def render_multiplayer_menu(self):
        self.screen.fill((70, 160, 230))
        center_x = self.screen_width // 2
        button_width = 220
        button_height = 70
        gap = 38
        start_y = 230

        title = self.font.render("Multiplayer", True, WHITE)
        title_rect = title.get_rect(center=(center_x, 140))
        self.screen.blit(title, title_rect)

        create_rect = pygame.Rect(center_x - button_width // 2, start_y, button_width, button_height)
        pygame.draw.rect(self.screen, (24, 134, 42), create_rect, border_radius=18)
        create_text = self.font.render("Create", True, WHITE)
        self.screen.blit(create_text, create_text.get_rect(center=create_rect.center))

        join_rect = pygame.Rect(center_x - button_width // 2, start_y + button_height + gap, button_width, button_height)
        pygame.draw.rect(self.screen, (70, 100, 200), join_rect, border_radius=18)
        join_text = self.font.render("Join", True, WHITE)
        self.screen.blit(join_text, join_text.get_rect(center=join_rect.center))

        back_rect = pygame.Rect(center_x - button_width // 2, start_y + 2 * (button_height + gap), button_width, button_height)
        pygame.draw.rect(self.screen, (200, 100, 100), back_rect, border_radius=18)
        back_text = self.font.render("Back", True, WHITE)
        self.screen.blit(back_text, back_text.get_rect(center=back_rect.center))

        self.multiplayer_buttons = {"create": create_rect, "join": join_rect, "back": back_rect}

    def handle_multiplayer_menu_click(self, pos):
        btns = getattr(self, 'multiplayer_buttons', {})
        if not btns:
            return
        if btns['create'].collidepoint(pos):
            self.state = 'CREATE_MULTIPLAYER_MENU'
        elif btns['join'].collidepoint(pos):
            self.state = 'JOIN_INPUT_MENU'
        elif btns['back'].collidepoint(pos):
            self.state = 'MAIN_MENU'

    def render_create_multiplayer_menu(self):
        self.screen.fill((70, 160, 230))
        center_x = self.screen_width // 2
        text = self.font.render("Multiplayer Create (Coming Soon)", True, WHITE)
        self.screen.blit(text, (center_x - text.get_width() // 2, 200))

    def handle_create_multiplayer_menu_click(self, pos):
        pass

    def render_join_multiplayer_menu(self):
        self.screen.fill((50, 120, 190))
        center_x = self.screen_width // 2
        text = self.font.render("Multiplayer Join (Coming Soon)", True, WHITE)
        self.screen.blit(text, (center_x - text.get_width() // 2, 200))

    def handle_join_input_mouse_click(self, pos):
        pass

    def render_client_menu(self):
        self.screen.fill((50, 120, 190))
        center_x = self.screen_width // 2
        text = self.font.render("Client Menu (Coming Soon)", True, WHITE)
        self.screen.blit(text, (center_x - text.get_width() // 2, 200))

    def handle_client_menu_mouse_click(self, pos):
        pass

    # ==================== LOADING ====================
    def render_loading(self):
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))
        
        text = self.font.render("Loading...", True, WHITE)
        self.screen.blit(text, (self.screen_width // 2 - text.get_width() // 2, 280))
        
        bar_x = self.screen_width // 2 - 150
        bar_y = 360
        bar_w = 300
        bar_h = 30
        pygame.draw.rect(self.screen, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h))
        fill = int(bar_w * (self.loading_percent / 100.0))
        pygame.draw.rect(self.screen, (60, 180, 70), (bar_x, bar_y, fill, bar_h))

    # ==================== MAIN RENDER ====================
    def render(self):
        if self.state == "MAIN_MENU":
            self.render_main_menu()
        elif self.state == "PLAY_MENU":
            self.render_play_menu()
        elif self.state == "LOAD_MENU":
            self.render_load_menu()
        elif self.state == "MULTIPLAYER_MENU":
            self.render_multiplayer_menu()
        elif self.state == "CREATE_MULTIPLAYER_MENU":
            self.render_create_multiplayer_menu()
        elif self.state == "JOIN_INPUT_MENU":
            self.render_join_multiplayer_menu()
        elif self.state == "CLIENT_MENU":
            self.render_client_menu()
        
        # Add menu overlay
        if self.add_menu_active:
            self.render_add_menu()
        
        # Loading overlay
        if self.loading_active:
            self.render_loading()

    def run(self):
        running = True
        
        while running:
            # Agar game engine active bo'lsa, menu handle_events skip qilish
            if self.game_engine is not None:
                # Game loopini menu loopiga birlashtirish
                game_running = self.game_engine.handle_events()
                if not game_running:
                    # Pygame QUIT bo'lsa
                    running = False
                    break
                
                dt = self.game_engine.clock.tick(60) / 1000.0
                self.game_engine.game_time = pygame.time.get_ticks() - self.game_engine.game_start_time
                
                self.game_engine.step_update(dt)
                self.game_engine.render()
                pygame.display.flip()
                
                # Game MAIN_MENU ga qaytsa, loopni tugat
                if self.game_engine.state == "MAIN_MENU":
                    self.game_engine = None
                    self.state = "MAIN_MENU"
                    continue
            else:
                # Menu loopi
                running = self.handle_events()
                self.render()
                pygame.display.flip()
                self.clock.tick(FPS)


if __name__ == "__main__":
    pygame.init()
    menu = Menu()
    menu.run()