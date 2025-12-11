import importlib
import traceback

def start_modul_game(screen, width, height, selected_slots, selected_modul="default"):
    """
    Load the chosen modul's `game_logic` and call its `run_game` entrypoint.
    """
    modul_name = selected_modul if selected_modul else "default"
    try:
        game_logic = importlib.import_module(f"Moduls.{modul_name}.game_logic")
    except Exception as e:
        print(f"[modul_loading] Failed to import game_logic for {modul_name}: {e}")
        traceback.print_exc()
        if modul_name != "default":
            try:
                game_logic = importlib.import_module("Moduls.default.game_logic")
            except Exception as e2:
                print(f"[modul_loading] Fallback import also failed: {e2}")
                raise

    # Prefer class-based GameEngine if present
    if hasattr(game_logic, "GameEngine"):
        try:
            engine = game_logic.GameEngine(screen, width, height)
            engine.run(selected_slots)
            return
        except Exception as e:
            print(f"[modul_loading] GameEngine.run raised: {e}")
            traceback.print_exc()

    if hasattr(game_logic, "run_game"):
        try:
            game_logic.run_game(screen, width, height, selected_slots)
        except Exception as e:
            print(f"[modul_loading] run_game raised: {e}")
            traceback.print_exc()
    else:
        # If run_game is not provided, attempt to set up players/world and run a simple loop
        try:
            # simple fallback: call setup_players + setup_world then return
            if hasattr(game_logic, "setup_players"):
                game_logic.setup_players(None, selected_slots)
            if hasattr(game_logic, "setup_world"):
                game_logic.setup_world(None)
        except Exception as e:
            print(f"[modul_loading] Fallback setup failed: {e}")
            traceback.print_exc()
