# Unknown world: unlimite

Unknown World: Unlimite is a 2D top-down survival shooter game built on Python and Pygame, designed for single-player and local multiplayer experiences. The project features a fully modular architecture, enabling extensive customization, easy addition of new game modes, and a scalable codebase for future growth.

Core Gameplay
You play as a survivor (alone or with friends/bots) fighting off waves of zombies in an open world. The game is fast-paced and strategic, combining classic shooter mechanics with RPG-inspired progression. Players level up by defeating zombies, unlock new weapons, and gain access to power-ups and unique abilities. The world is procedurally generated, filled with obstacles, trees, rocks, and scattered resources.

Main Features:

Survival Shooter: Fight endless waves of zombies, survive as long as possible.
Progression System: Level up, unlock new weapons (pistols, shotguns, rifles, miniguns, drones) and gain shields.
Dynamic World: Day/night cycle, procedurally generated terrain, environmental hazards.
Power-ups: Health and shield boosts spawn based on performance.
Multiplayer & Bots: Play locally with friends (keyboard sharing) or add AI bots.
Downed/Revive System: In multiplayer, downed players can be revived by teammates or bots.
Game Modes: Selectable at game start for different play experiences.
Modular Architecture
The biggest change in Unknown World: Unlimite is its modular system:

Moduls Folder: All game modes are stored in the Moduls/ directory. Each mode is a subfolder with its own game logic, assets, and save/load system. The default mode is found in Moduls/default/.
Dynamic Selection: At the Play menu, players can choose from available modes. The menu lists all detected modes, letting you switch gameplay experience without modifying the core engine.
Extensible Design: Adding a new mode is as easy as creating a new folder and implementing the required Python files (game_logic.py, etc.). Each mode can have custom gameplay, world generation, rules, or even save/load formats.
Technical Highlights
Code Organization:

All gameplay logic (player, world, zombies, bullets, bots, save/load) is encapsulated in the selected module.
The engine dynamically loads the correct module using Python's importlib, ensuring all imports are absolute and package-compliant.
Helper functions (safe_get, safe_int, safe_bool, safe_enum) guarantee robust loading from saved games, preventing crashes or missing data.
Saving & Loading:

Each mode has its own save_load.py system, supporting custom serialization.
Player progress, world state, and other data are stored in SQLite databases, allowing you to pick up exactly where you left off.
If save data is missing or partial, default values are automatically substituted.
Extensibility:

Developers can create new game modes, new enemies, weapons, or world features by working in their own module folder, without affecting others.
The engine will automatically detect and offer these new experiences in the Play menu.
Error Handling:

The system gracefully handles missing or corrupt save data, falling back on defaults or alerting the player.
All modules are loaded as Python packages (__init__.py in each folder), preventing import issues.
Example Gameplay Flow
Launch the Game: The start screen appears. Click "Play."
Choose Players/Bots: Select your survivors and bots for the session.
Select a Mode: The Play menu displays all available game modes (from the Moduls folder). Pick the one you want.
Survive: The world loads, and you battle waves of zombies, collect power-ups, level up, and unlock new gear.
Save/Load: At any time, save your progress. Later, load your save to resume from where you left off—even in a different mode.
Extend: Advanced users can create and add their own modes, rules, or gameplay variations for endless replayability.
Why Play "Unknown World: Unlimite"?
Customizable: Play your way with endless mode possibilities.
Replayable: Dynamic world, RPG progression, and varied modes keep gameplay fresh.
Community-Driven: Built for modders and Python developers—anyone can create new content.
Stable and Robust: Strong error handling and default value logic mean you’ll never lose progress due to corrupt saves or missing data.
Open Source: Learn, modify, and contribute to the project.
Summary:
Unknown World: Unlimite is more than just a shooter game—it's a platform for endless survival experiences, powered by a modular, extensible Python architecture. Whether you want classic zombie survival or to invent your own game mode, this project gives you the tools, stability, and flexibility to play, create, and share.
