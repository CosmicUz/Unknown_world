# Unknown World: Unlimited

A survival action game built with Python and Pygame where you fight against waves of zombies.

## Features

- Single player and multiplayer modes (up to 2 players)
- Bot companions that help fight zombies
- Multiple weapon types that unlock as you level up
- Day/night cycle with increased zombie spawns at night
- Power-up system for health and shield regeneration
- Save/Load game functionality
- Revive system in multiplayer mode

## Gameplay

Survive as long as possible against endless waves of zombies. Kill zombies to level up and unlock better weapons. In multiplayer mode, players can revive each other when downed.

### Zombie Types
- **Walker** - Standard slow zombie
- **Runner** - Fast moving zombie
- **Tanker** - High health zombie

### Weapons (unlock by leveling up)
1. Pistol (Level 1)
2. Dual Pistols (Level 5)
3. M-16 (Level 10)
4. Shotgun (Level 15)
5. AK-47 (Level 20)
6. Drone (Level 30)
7. M-249 (Level 50)
8. MG-3 (Level 75)
9. Mini Gun (Level 100)

## Controls

### Player 1
- **Movement**: W, A, S, D
- **Shoot**: Space or F

### Player 2
- **Movement**: Arrow keys
- **Shoot**: K

### General
- **Pause**: ESC
- **Fullscreen**: F11

## Project Structure

```
├── run_game.py          # Entry point - start screen
├── menu.py              # Game menu system
├── core.py              # Core constants, enums, Vector2 class
├── loading.py           # Loading screen
├── network.py           # Multiplayer networking
├── session.py           # Game session management
└── Moduls/
    └── default/
        ├── player.py        # Player class
        ├── zombie.py        # Zombie enemies
        ├── bullet.py        # Projectile system
        ├── world.py         # World/map generation
        ├── game_logic.py    # Core game engine
        ├── helper_bot.py    # AI bot companion
        ├── save_load.py     # Save/load functionality
        ├── modul_loading.py # Module loading system
        └── modul_network.py # Module networking
```

## Requirements

- Python 3.11+
- Pygame 2.6.1
- NumPy

## Running the Game

The game runs as a desktop application. Start the game workflow or run:

```bash
python run_game.py
```

Click the START button on the main screen, then select players/bots from the play menu and press Start to begin.

## How to Play

1. Click START on the main screen
2. Select player configuration (Player 1, Player 2, or Bot)
3. Click Start to begin the game
4. Move around and zombies will be automatically targeted
5. Press shoot button to fire at nearest zombie
6. Collect power-ups (green circles) to restore health/shield
7. Survive and level up to unlock better weapons
8. Press ESC to pause and access save/load options
