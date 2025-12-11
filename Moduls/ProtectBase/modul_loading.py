import importlib
import traceback


def start_modul_game(screen, width, height, selected_slots, selected_modul="ProtectBase"):
    """
    Load the ProtectBase modul's `game_logic` and call its GameEngine.
    This function receives data from the play menu (selected players/bots)
    and starts the ProtectBase game mode.
    
    Parameters:
    - screen: Pygame display surface
    - width: Screen width
    - height: Screen height
    - selected_slots: List of player/bot configurations from play menu
        Each slot contains: {'type': 'player'/'bot', 'id': int, 'name': str, 'color': list}
    - selected_modul: Module name (default: "ProtectBase")
    """
    modul_name = selected_modul if selected_modul else "ProtectBase"
    
    try:
        game_logic = importlib.import_module(f"Moduls.{modul_name}.game_logic")
    except Exception as e:
        print(f"[modul_loading ProtectBase] Failed to import game_logic for {modul_name}: {e}")
        traceback.print_exc()
        if modul_name != "ProtectBase":
            try:
                game_logic = importlib.import_module("Moduls.ProtectBase.game_logic")
            except Exception as e2:
                print(f"[modul_loading ProtectBase] Fallback import also failed: {e2}")
                raise
        else:
            raise

    if hasattr(game_logic, "GameEngine"):
        try:
            engine = game_logic.GameEngine(screen, width, height)
            engine.run(selected_slots)
            return
        except Exception as e:
            print(f"[modul_loading ProtectBase] GameEngine.run raised: {e}")
            traceback.print_exc()

    if hasattr(game_logic, "run_game"):
        try:
            game_logic.run_game(screen, width, height, selected_slots)
        except Exception as e:
            print(f"[modul_loading ProtectBase] run_game raised: {e}")
            traceback.print_exc()
    else:
        try:
            if hasattr(game_logic, "setup_players"):
                game_logic.setup_players(None, selected_slots)
            if hasattr(game_logic, "setup_world"):
                game_logic.setup_world(None)
        except Exception as e:
            print(f"[modul_loading ProtectBase] Fallback setup failed: {e}")
            traceback.print_exc()
