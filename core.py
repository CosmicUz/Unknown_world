import math
from dataclasses import dataclass
from enum import Enum

# colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
LIGHT_BLUE = (135, 206, 235)
DARK_BLUE = (70, 130, 180)
ORANGE = (255, 165, 0)
BROWN = (139, 69, 19)
TREE_GREEN = (34, 139, 34)
LIGHT_GRAY = (200, 200, 200)
PURPLE = (128, 0, 128)

FPS = 60
BACKGROUND_COLOR = (45, 80, 22)


class GameState(Enum):
    MAIN_MENU = 1
    PLAYING = 2
    PAUSED = 3
    GAME_OVER = 4
    PLAY_MENU = 5
    LOAD_MENU = 6
    LOADING = 7


class GameMode(Enum):
    Offline = "offline"
    # Online = "online"


class WeaponType(Enum):
    PISTOL = 1
    DUAL_PISTOLS = 2
    M_16 = 3
    SHOT_GUN = 4
    AK_47 = 5
    DRONE = 6
    MG_3 = 7
    M_249 = 8
    MINI_GUN = 9


class PlayerState(Enum):
    ALIVE = 1
    DOWNED = 2
    DEAD = 3


@dataclass
class Vector2:
    x: float
    y: float

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)

    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self):
        length = self.length()
        if length == 0:
            return Vector2(0, 0)
        return Vector2(self.x / length, self.y / length)
