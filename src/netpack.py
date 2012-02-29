#!/usr/bin/env python

import math, textwrap
import libtcodpy as libtcod
import pygame.mixer
import pygame._view
from sys import exit
from os.path import exists
from netpack_maps import *

global_debug = False

'''

# FIX!


# CURRENT:


# SOUNDS NEEDED:


# PLANNED:


# KNOWN BUGS:

- sometimes the orange (and other items?) animations won't play and then will play twice on next use
- at least once the game has crashed because an "Item doesn't have a time field" or something

'''

#-------------#
### GLOBALS ###
#-------------#

VERSION = '1.2'
FONT = 'font.png'
FPS = 20
START_LEVEL = 16

# dimensions
SCREEN_WIDTH = 37
SCREEN_HEIGHT = 37
LVL_WIDTH = 23
LVL_HEIGHT = 21

# status panel
BAR_WIDTH = 23
PANEL_HEIGHT = 7
PANEL_Y = 0

# message panel
MSG_X = 0
MSG_Y = PANEL_HEIGHT + LVL_HEIGHT
MSG_WIDTH = SCREEN_WIDTH
MSG_HEIGHT = SCREEN_HEIGHT - PANEL_HEIGHT - LVL_HEIGHT
BLANK_LINE = ""
for i in range(SCREEN_WIDTH):
    BLANK_LINE += " "

# timing
SPAWN_RATE = 9
RESPAWN_RATE = 14
GHOST_FLEE_TIME = 44

# points
EAT_POINTS = 200
KILL_POINTS = 600
LEVEL_UP_POINTS = 10000

# FOV
FOV_ALGO = 1
FOV_LIGHT_WALLS = True
FOV_RADIUS = 5

#-------------#
### CLASSES ###
#-------------#

class Object(object):

    def __init__(self, x, y, char, color, name, blocked=False):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.original_color = color
        self.name = name
        self.blocked = blocked

    def set_pos(self, x, y):
        self.x = x
        self.y = y

    def move(self, dx, dy):

        if player.state != 'dead': player.state = 'did-not-move'

        if not current_level.level_map[self.x][self.y].warp:
            if isinstance(self, Player):
                if not is_blocked(self.x + dx, self.y + dy):
                    self.x += dx
                    self.y += dy
                    player.state = 'moved'
            else:
                if not current_level.level_map[self.x + dx][self.y + dy].blocked and (player.x, player.y) != (self.x + dx, self.y + dy):
                    self.x += dx
                    self.y += dy
                    player.state = 'moved'

        else: # warping
            if self.x == 0 and dx == -1:
                self.set_pos(LVL_WIDTH - 1, self.y)
                player.state = 'moved'
            elif self.x == LVL_WIDTH - 1 and dx == 1:
                self.set_pos(0, self.y)
                player.state = 'moved'
            else:
                if not is_blocked(self.x + dx, self.y + dy):
                    self.x += dx
                    self.y += dy
                    player.state = 'moved'

    def draw(self):

        if self.name != 'strawberry jam stain' and self.name != 'charred floor 1' and self.name != 'charred floor 2':

            if current_level.dark:

                if libtcod.map_is_in_fov(fov_map, self.x, self.y):
                    libtcod.console_set_default_foreground(con, self.color)
                    libtcod.console_print(con, self.x, self.y, self.char)

            else:
                libtcod.console_set_default_foreground(con, self.color)
                libtcod.console_print(con, self.x, self.y, self.char)

        else:

            if current_level.dark:

                if libtcod.map_is_in_fov(fov_map, self.x, self.y):
                    if self.name == 'strawberry jam stain':
                        libtcod.console_put_char_ex(con, self.x, self.y, libtcod.CHAR_BLOCK1, libtcod.dark_pink, current_level.color_floor)
                    if self.name == 'charred floor 1':
                        libtcod.console_put_char_ex(con, self.x, self.y, libtcod.CHAR_BLOCK2, libtcod.dark_grey, current_level.color_floor)
                    if self.name == 'charred floor 2':
                        libtcod.console_put_char_ex(con, self.x, self.y, libtcod.CHAR_BLOCK1, libtcod.dark_grey, current_level.color_floor)

                else:
                    self.clear()

            else:
                if self.name == 'strawberry jam stain':
                    libtcod.console_put_char_ex(con, self.x, self.y, libtcod.CHAR_BLOCK1, libtcod.dark_pink, current_level.color_floor)
                if self.name == 'charred floor 1':
                    libtcod.console_put_char_ex(con, self.x, self.y, libtcod.CHAR_BLOCK2, libtcod.dark_grey, current_level.color_floor)
                if self.name == 'charred floor 2':
                    libtcod.console_put_char_ex(con, self.x, self.y, libtcod.CHAR_BLOCK1, libtcod.dark_grey, current_level.color_floor)

    def clear(self):
        libtcod.console_print(con, self.x, self.y, ' ')

    def coords(self):
        return (self.x, self.y)

class Player(Object):

    def __init__(self, x, y, char, color, name, blocked, level, attack_dice = '1d6', defense_dice = '1d4', lives = 3, hp = 10, score = 0):
        super(Player, self).__init__(x, y, char, color, name, blocked)
        self.startx = x
        self.starty = y
        self.score = 0
        self.level_up_score = self.score
        self.ghosts_eaten = 0

        self.max_hp = hp
        self.hp = hp
        self.exp = 0
        self.exp_next_level = 50
        self.level = level
        self.attack_dice = attack_dice
        self.defense_dice = defense_dice
        self.attack_bonus = 0
        self.defense_bonus = 0
        self.lives = lives
        self.state = None

        self.attack_base = 8
        self.attack_cap = 12
        self.defense_base = 8
        self.defense_cap = 12

        self.inventory = []
        self.items_in_use = []

    def take_damage(self, damage):

        if self.hp > 0:
            self.hp -= damage

    def attack(self, target):

        damage = throw_dice(self.attack_dice) - throw_dice(target.defense_dice) + player.attack_bonus

        if damage > 0:

            if player.attack_bonus > 0:
                effects_panel = libtcod.console_new(LVL_WIDTH, LVL_HEIGHT)
                libtcod.console_set_default_background(effects_panel, libtcod.white)
                libtcod.console_clear(effects_panel)
                libtcod.console_blit(effects_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
                message("CRACK!")
                for i in range(3):
                    libtcod.console_flush()
                libtcod.console_delete(effects_panel)

            message(self.name.capitalize() + " attacked " + target.name + " for " + str(damage) + " damage.", libtcod.sky)
            target.take_damage(damage)

            if play_sounds and not pygame.mixer.get_busy():
                sound_player_attack.play()

        else:

            message(self.name.capitalize() + " attacked " + target.name + ", but it had no effect.", libtcod.light_grey)

        player.state = 'moved'

    def level_up(self, score_string=None):

        if play_sounds: sound_level_up.play()

        self.level += 1

        # generating new attack dice
        old_dice = self.attack_dice.split('d')

        if int(old_dice[1]) != self.attack_cap:
            self.attack_dice = '%dd%d' % (int(old_dice[0]), int(old_dice[1]) + 2)
        else:
            self.attack_dice = '%dd%d' % (int(old_dice[0]) + 1, self.attack_base)
            self.attack_base += 2
            self.attack_cap += 2

        # generating new defense dice
        old_dice = self.defense_dice.split('d')

        if int(old_dice[1]) != self.defense_cap:
            self.defense_dice = '%dd%d' % (int(old_dice[0]), int(old_dice[1]) + 1)
        else:
            self.defense_dice = '%dd%d' % (int(old_dice[0]) + 1, self.defense_base)
            self.defense_cap += 2
            self.defense_base += 2

        # new hp cap
        self.max_hp += int(self.max_hp * 0.18)

        # if the player levels up from points, don't reset exp or increase the exp needed for next level
        if not score_string:
            self.exp_next_level += int(self.exp_next_level * 0.20)
            self.exp = 0
        else:
            message(score_string, libtcod.yellow)
        message("You reached level %d!" % player.level, libtcod.yellow)

    def add_to_score(self, points):

        if game_mode != 'god': self.score += points

        if (self.level_up_score + points) >= LEVEL_UP_POINTS:
            self.level_up('You scored 10,000 points!')
            self.level_up_score = self.level_up_score + points - LEVEL_UP_POINTS
        else:
            self.level_up_score += points

class Ghost(Object):

    def __init__(self, x, y, char, color, name, algo, flee_time, blocked=True):
        super(Ghost, self).__init__(x, y, char, color, name, blocked)

        self.level = 16 - current_level.dlvl + 1
        if current_level.dlvl < 13:
            self.level += 2
        if current_level.dlvl < 10:
            self.level += 3
        if current_level.dlvl < 7:
            self.level += 3
        if current_level.dlvl < 4:
            self.level += 4
        if current_level.dlvl == 2:
            self.level += 2
        if self.name in ('Ghost of the Paku King', 'The Living Paku Queen'):
            self.level = 33
        self.hp = int(self.level * 8)
        self.attack_dice = '%dd%d' % (current_level.sublvl + 1, int(self.level * 1.4))
        self.defense_dice = '%dd%d' % (3, int(self.attack_dice.split('d')[1]) * 0.5)

        self.algo = algo

        self.state = 'spawning'
        self.respawn_timer = RESPAWN_RATE
        self.flee_timer = current_level.level_flee_time
        self.startx = 0
        self.starty = 0

        if libtcod.random_get_int(0, 0, 1) == 1:
            self.direction = (1, 0)
        else:
            self.direction = (-1, 0)

    def chase(self):

        # move at half-speed if a pear is in play or freeze if there are two
        number_of_pears = 0
        for item in player.items_in_use:
            if item.name == 'scroll of pear':
                number_of_pears += 1
        if number_of_pears == 1:
            if item.time % 2 == 0:
                return
        elif number_of_pears > 1:
            return

        possible_moves = self.look()
        if not current_level.level_map[self.x][self.y].warp:
            if not current_level.level_map[self.x + self.direction[0]][self.y + self.direction[1]].blocked:
                possible_moves.append(self.direction)

        # if player is in front of ghost, attack instead of chase
        distance_to_player = get_distance(self.x, self.y, player.x, player.y)
        if distance_to_player == 1 and (player.x, player.y) == (self.x + self.direction[0], self.y + self.direction[1]) and player.hp != 0:

            self.attack()

        if self.name == 'Anne': # mimic a random ghost
            self.algo = libtcod.random_get_int(0, 0, 2)

        if possible_moves != []:

            if self.algo == 0: # aggressive

                if libtcod.random_get_int(0, 1, 100) <= 80:

                    # make the move that has the shortest distance to the player
                    lowest = SCREEN_WIDTH + SCREEN_HEIGHT # sort of arbitrary; just needs to be high

                    for move in possible_moves:

                        distance = get_distance(self.x + move[0], self.y + move[1], player.x, player.y)

                        if distance < lowest:
                            lowest = distance
                            this_move = move

                else:

                    this_move = possible_moves[libtcod.random_get_int(0, 0, len(possible_moves) - 1)]

            elif self.algo == 1: # turny

                # determining direction to turn in order to follow player
                if abs(possible_moves[0][0]) == 1: # going left or right
                    if self.x - player.x > 1 and (-1, 0) in possible_moves:
                        this_move = (-1, 0)
                    elif self.x - player.x < -1 and (1, 0) in possible_moves:
                        this_move = (1, 0)
                    else:
                        this_move = possible_moves[libtcod.random_get_int(0, 0, len(possible_moves) - 1)]
                elif abs(possible_moves[0][1]) == 1: # going up or down
                    if self.y - player.y > 1 and (0, -1) in possible_moves:
                        this_move = (0, -1)
                    elif self.y - player.y < -1 and (0, 1) in possible_moves:
                        this_move = (0, 1)
                    else:
                        this_move = possible_moves[libtcod.random_get_int(0, 0, len(possible_moves) - 1)]

            elif self.algo == 2: # more random

                if libtcod.random_get_int(0, 1, 100) <= 50:

                    # make the move that has the shortest distance to the player
                    lowest = SCREEN_WIDTH + SCREEN_HEIGHT # sort of arbitrary; just needs to be high

                    for move in possible_moves:

                        distance = get_distance(self.x + move[0], self.y + move[1], player.x, player.y)

                        if distance < lowest:
                            lowest = distance
                            this_move = move

                else:

                    this_move = possible_moves[libtcod.random_get_int(0, 0, len(possible_moves) - 1)]

        else:

            this_move = self.direction

        self.move(this_move[0], this_move[1])
        self.direction = this_move

    def attack(self):

        global game_state
        global game_mode

        damage = throw_dice(self.attack_dice) - throw_dice(player.defense_dice) - player.defense_bonus

        if damage > 0:

            if play_sounds:
                sound_ghost_attack.play()

            player.take_damage(damage)
            message(self.name + " attacked " + player.name + " for " + str(damage) + " damage.", libtcod.light_red)
        else:

            if play_sounds:
                sound_block.play()

            message(self.name + " attacked " + player.name + ", but it had no effect.", libtcod.light_sky)

    def flee(self):

        # ghosts flee slower than they chase
        if self.flee_timer % 3 == 0 and self.flee_timer > 0:

            possible_moves = self.look()
            if not current_level.level_map[self.x][self.y].warp:
                if not current_level.level_map[self.x + self.direction[0]][self.y + self.direction[1]].blocked:
                    possible_moves.append(self.direction)

            if possible_moves != []:
                # make the move that has the greatest distance to the player
                greatest = -1

                for move in possible_moves:

                    distance = get_distance(self.x + move[0], self.y + move[1], player.x, player.y)

                    if distance > greatest:
                        greatest = distance
                        this_move = move

            else:

                this_move = self.direction

            self.move(this_move[0], this_move[1])
            self.direction = this_move

        self.flee_timer -= 1

        if self.flee_timer == 0:

            change_ghost(self)
            self.flee_timer = current_level.level_flee_time

    def respawn(self):

        if self.respawn_timer != 0:
            self.respawn_timer -= 1
        else:
            change_ghost(self)
            self.set_pos(11, 7)
            self.respawn_timer = RESPAWN_RATE
            self.flee_timer = current_level.level_flee_time

    def look(self):
        '''
        Returns a list of open directions to the left and right.
        '''

        free_dir = []

        # if last move was horizontal
        if abs(self.direction[0]) == 1:
            # append free_dir with a tuple of coordinates for unblocked square
            if not current_level.level_map[self.x][self.y + 1].blocked:
                free_dir.append((0, 1)) # south
            if not current_level.level_map[self.x][self.y - 1].blocked:
                free_dir.append((0, -1)) #north
        # if last move was vertical
        elif abs(self.direction[1]) == 1:
            if not current_level.level_map[self.x + 1][self.y].blocked:
                free_dir.append((1, 0)) # east
            if not current_level.level_map[self.x - 1][self.y].blocked:
                free_dir.append((-1, 0)) # west

        return free_dir

    def take_damage(self, damage):

        if self.hp - damage > 0:
            self.hp -= damage
        else:

            if play_sounds:
                pygame.mixer.stop()
                sound_kill_ghost.play()

            self.state = 'dead'
            player.ghosts_killed += 1

            if self.name not in ('The Living Paku Queen', 'Ghost of the Paku King'):
                message(player.name.capitalize() + " vanquished %s." % self.name, libtcod.red)
            else:
                message(player.name.capitalize() + " dispatch %s." % self.name, libtcod.red)
            player.add_to_score(KILL_POINTS)
            current_level.ghosts.remove(self)
            current_level.effects.append(Effect(self.x, self.y, '%%', libtcod.red, 'ghost corpse'))

class Pellet(Object):

    def __init__(self, x, y, char, color, name, points=None, blocked=False):
        super(Pellet, self).__init__(x, y, char, name, color)
        self.points = points

class Item(Object):

    def __init__(self, x, y, char, color, name, use_message = "", obtainable = True):
        super(Item, self).__init__(x, y, char, color, name)
        self.obtainable = obtainable

        self.use_message = use_message
        self.target_exit = ()
        self.birth_turn = TURN

        if self.name in 'pretzel whip, orange peel':
            self.max_time = 10
            self.time = self.max_time
        if self.name == 'scroll of pear':
            self.max_time = 30
            self.time = self.max_time

        if self.x > 0:
            self.direction = (-1, 0)
        else:
            self.direction = (1, 0)

    def tick(self):

        self.time -= 1

    def get_target_exit(self):

        potential_exits = []
        for x in range(LVL_WIDTH):
            for y in range(LVL_HEIGHT):
                if current_level.level_map[x][y].warp:
                    if x == 0 and self.direction == (-1, 0):
                        potential_exits.append((x, y))
                    elif x > 0 and self.direction == (1, 0):
                        potential_exits.append((x, y))

        exit = potential_exits[libtcod.random_get_int(0, 0, len(potential_exits) - 1)]
        self.target_exit = (exit[0], exit[1])

    def look(self):
        '''
        Returns a list of open directions to the left and right.
        '''

        free_dir = []

        # if last move was horizontal
        if abs(self.direction[0]) == 1:
            # append free_dir with a tuple of coordinates for unblocked square
            if not current_level.level_map[self.x][self.y + 1].blocked:
                free_dir.append((0, 1)) # south
            if not current_level.level_map[self.x][self.y - 1].blocked:
                free_dir.append((0, -1)) #north
        # if last move was vertical
        elif abs(self.direction[1]) == 1:
            if not current_level.level_map[self.x + 1][self.y].blocked:
                free_dir.append((1, 0)) # east
            if not current_level.level_map[self.x - 1][self.y].blocked:
                free_dir.append((-1, 0)) # west

        return free_dir

    def bounce(self):

        if current_level.dlvl not in (3, 2, 1):

            if (self.x, self.y) == self.target_exit and TURN - self.birth_turn > 200:
                current_level.items.remove(self)

            possible_moves = self.look()
            if not current_level.level_map[self.x][self.y].warp:
                if not current_level.level_map[self.x + self.direction[0]][self.y + self.direction[1]].blocked:
                    possible_moves.append(self.direction)

            if possible_moves != []:

                if TURN - self.birth_turn > 200:

                    # seek the target exit after bouncing around randomly for however many turns
                    if libtcod.random_get_int(0, 1, 100) <= 80:

                        # make the move that has the shortest distance to its target exit
                        lowest = SCREEN_WIDTH + SCREEN_HEIGHT # sort of arbitrary; just needs to be high

                        for move in possible_moves:

                            distance = get_distance(self.x + move[0], self.y + move[1], self.target_exit[0], self.target_exit[1])

                            if distance < lowest:
                                lowest = distance
                                this_move = move

                    else:

                        this_move = possible_moves[libtcod.random_get_int(0, 0, len(possible_moves) - 1)]

                else:

                    this_move = possible_moves[libtcod.random_get_int(0, 0, len(possible_moves) - 1)]

            else:

                this_move = self.direction

            self.move(this_move[0], this_move[1])
            self.direction = this_move

class Effect(Object):

    def __init__(self, x, y, char, color, name):
        super(Effect, self).__init__(x, y, char, color, name)

class Tile(object):

    def __init__(self, blocked, warp = False, style = None):
        self.blocked = blocked
        self.warp = warp
        self.explored = False
        self.style = style

class Level(object):

    def __init__(self, dlvl, sublvl, map, color_wall, color_floor, dark=False):
        self.name = 'Level %d' % dlvl
        self.dlvl = dlvl
        self.sublvl = sublvl
        self.map = map
        self.level_map = [ [ Tile(False) for y in range(LVL_HEIGHT) ] for x in range(LVL_WIDTH) ]
        self.color_wall = color_wall
        self.color_floor = color_floor
        self.dark = dark

        if self.sublvl == 1:
            self.level_flee_time = GHOST_FLEE_TIME
        elif self.sublvl == 2:
            self.level_flee_time = int(GHOST_FLEE_TIME / 1.5)
        elif self.sublvl == 3:
            self.level_flee_time = GHOST_FLEE_TIME / 2

        self.ghosts = []
        self.pellets = []
        self.items = []
        self.corpses = []
        self.ghosts_in_cage = []
        self.effects = []

        self.items_to_spawn = 5

    def set_up(self):

        if self.dlvl >= 13: color = libtcod.Color(216, 216, 252)
        elif self.dlvl >= 10 and self.dlvl <= 12: color = libtcod.yellow
        elif self.dlvl >= 7 and self.dlvl <= 9: color = libtcod.red
        elif self.dlvl >= 4 and self.dlvl <= 6: color = libtcod.Color(216, 216, 252)
        elif self.dlvl >= 1 and self.dlvl <= 3: color = libtcod.dark_red

        for y in range(LVL_HEIGHT):
            for x in range(LVL_WIDTH):
                if self.map[y][x] == '1':
                    self.level_map[x][y].blocked = True
                elif self.map[y][x] == 'w':
                    self.level_map[x][y].warp = True
                elif self.map[y][x] == 'l':
                    self.level_map[x][y].blocked = True
                    self.level_map[x][y].style = 'top-left-corner'
                elif self.map[y][x] == 'r':
                    self.level_map[x][y].blocked = True
                    self.level_map[x][y].style = 'top-right-corner'
                elif self.map[y][x] == 'L':
                    self.level_map[x][y].blocked = True
                    self.level_map[x][y].style = 'bot-left-corner'
                elif self.map[y][x] == 'R':
                    self.level_map[x][y].blocked = True
                    self.level_map[x][y].style = 'bot-right-corner'
                elif self.map[y][x] == '=':
                    self.level_map[x][y].blocked = True
                    self.level_map[x][y].style = 'horizontal-bar'
                elif self.map[y][x] == 'v':
                    self.level_map[x][y].blocked = True
                    self.level_map[x][y].style = 'vertical-bar'
                elif self.map[y][x] == '-':
                    self.level_map[x][y].blocked = True
                    self.level_map[x][y].style = 'cage-door'
                elif self.map[y][x] == '.':
                    self.pellets.append(Pellet(x, y, '.', 'pellet', color, 10))
                elif self.map[y][x] == 'o':
                    self.pellets.append(Pellet(x, y, 'o', 'power pellet', color, 50))
                elif self.map[y][x] == 'B':
                    if current_level.dlvl != 1:
                        blinky = Ghost(x, y, 'B', libtcod.red, 'Blinky', algo=0, flee_time = self.level_flee_time)
                        blinky.startx = x
                        blinky.starty = y
                    else:
                        blinky = Ghost(x - 1, y, 'K', libtcod.grey, 'Ghost of the Paku King', algo=0, flee_time = self.level_flee_time)
                        pinky = Ghost(x + 1, y, 'Q', libtcod.light_yellow, 'The Living Paku Queen', algo=1, flee_time = self.level_flee_time)
                        pinky.state = 'aggressive'
                        blinky.startx, blinky.starty = x - 1, y
                        pinky.startx, pinky.starty = x + 1, y
                        self.ghosts.append(pinky)
                    blinky.state = 'aggressive'
                    self.ghosts.append(blinky)
                elif self.map[y][x] == 'P':
                    pinky = Ghost(x, y, 'P', libtcod.light_pink, 'Pinky', algo=0, flee_time = self.level_flee_time)
                    pinky.startx = x
                    pinky.starty = y
                    self.ghosts.append(pinky)
                elif self.map[y][x] == 'I':
                    inky = Ghost(x, y, 'I', libtcod.light_blue, 'Inky', algo=0, flee_time = self.level_flee_time)
                    inky.startx = x
                    inky.starty = y
                    self.ghosts.append(inky)
                elif self.map[y][x] == 'A':
                    anne = Ghost(x, y, 'A', libtcod.light_orange, 'Anne', algo=0, flee_time = self.level_flee_time)
                    anne.startx = x
                    anne.starty = y
                    self.ghosts.append(anne)
                elif self.map[y][x] == '@':
                    player.set_pos(x, y)
                    player.startx = x
                    player.starty = y

        if self.dlvl != 1:
            self.ghosts_in_cage = [pinky, inky, anne]

        if self.dlvl == 3:
            self.items.append(Item(9, 11, 'a', libtcod.dark_green, 'appletini', 'You suck down the appletini.'))
            self.items.append(Item(10, 11, 'p', libtcod.chartreuse, 'scroll of pear', 'You read the words on the scroll, and it crumbles away.'))
            self.items.append(Item(11, 11, 's', libtcod.pink, 'strawberry jam', 'You spread the jam on the ground, fall through the floor, and drop from the ceiling somewhere else.'))
            self.items.append(Item(12, 11, 'p', libtcod.chartreuse, 'scroll of pear', 'You read the words on the scroll, and it crumbles away.'))
            self.items.append(Item(13, 11, 'a', libtcod.dark_green, 'appletini', 'You suck down the appletini.'))

            self.effects.append(Effect(5, 11, '#', libtcod.dark_red, 'previous adventurer\'s corpse'))
            self.effects.append(Effect(10, 5, '#', libtcod.dark_red, 'previous adventurer\'s corpse'))
            self.effects.append(Effect(10, 13, '#', libtcod.dark_red, 'previous adventurer\'s corpse'))
            self.effects.append(Effect(9, 13, '#', libtcod.darker_grey, 'etching: "It\'s too late to turn back." - Davey'))

        if self.dlvl == 2:
            self.items.append(Item(2, 3, 'p', libtcod.dark_orange, 'pretzel whip', 'You untwist the pretzel and wield it.'))
            self.items.append(Item(20, 17, 'p', libtcod.dark_orange, 'pretzel whip', 'You untwist the pretzel and wield it.'))
            self.items.append(Item(2, 17, 'o', libtcod.Color(255, 165, 0), 'orange peel', 'You don the giant orange peel. You feel tougher.'))
            self.items.append(Item(20, 3, 'o', libtcod.Color(255, 165, 0), 'orange peel', 'You don the giant orange peel. You feel tougher.'))

            self.effects.append(Effect(17, 13, '#', libtcod.dark_red, 'previous adventurer\'s corpse'))

        if self.dlvl == 1:
            self.effects.append(Effect(10, 9, '/', libtcod.yellow, 'throne'))
            self.effects.append(Effect(11, 9, '-', libtcod.yellow, 'altar'))
            self.effects.append(Effect(12, 9, '\\', libtcod.yellow, 'throne'))
            self.level_map[10][9].blocked = True
            self.level_map[12][9].blocked = True

class SaveData(object):

    def __make_block(self, length):
        '''
        Creates a square block of random characters from the SaveData object's alphabets.
        '''

        self.__block = []
        for y in range(length):
            line = []
            for x in range(length):
                rand = libtcod.random_get_int(0, 0, len(self.__alphabets) - 1)
                line.append(self.__alphabets[rand][libtcod.random_get_int(0, 0, len(self.__alphabets[rand]) - 1)])
            self.__block.append(''.join(line) + '\n')

    def __encode_block(self):
        '''
        Generates three random 9-character keys using the SaveData object's alphabets.
        '''

        a, b, c = list(self.__alphabet_1), list(self.__alphabet_2), list(self.__alphabet_3)

        # makes the keys
        while a != [] and b != [] and c != []:
            index = libtcod.random_get_int(0, 0, len(a) - 1)
            self.__key_1.append(a.pop(index))
            index = libtcod.random_get_int(0, 0, len(b) - 1)
            self.__key_2.append(b.pop(index))
            index = libtcod.random_get_int(0, 0, len(c) - 1)
            self.__key_3.append(c.pop(index))

        # places the first two keys in the third row
        tmp = list(self.__block[2])
        for i in range(10):
            tmp[i + 2] = self.__key_1[i]
            tmp[i + 14] = self.__key_2[i]
        self.__block[2] = ''.join(tmp)
        # places the third key in the fourth row
        tmp = list(self.__block[3])
        for i in range(10):
            tmp[i + 17] = self.__key_3[i]
        self.__block[3] = ''.join(tmp)

    def __int2str(self, n, digits):
        '''
        Turns an integer into a string with leading zeros and obfuscates it using
        the keys.
        '''

        n = list(str(n))
        while len(n) < digits:
            n.insert(0, '0')

        for i in range(len(n)):
            # change each digit to one of the key's corresponding character
            which_key = libtcod.random_get_int(0, 1, 3)
            if which_key == 1:
                n[i] = self.__key_1[int(n[i])]
            elif which_key == 2:
                n[i] = self.__key_2[int(n[i])]
            else:
                n[i] = self.__key_3[int(n[i])]

        return n

    def __insert_data(self, row, col, data):
        '''
        Places a string of data into the block.
        '''

        tmp = list(self.__block[row])
        tmp[col:col+len(data)] = list(data)
        self.__block[row] = ''.join(tmp)

    def save(self):

        self.__block = []
        self.__key_1 = []
        self.__key_2 = []
        self.__key_3 = []

        # get 10 unique characters to form the block's alphabets
        # generate three of them to mix it up and prepare for three keys
        self.__possible_chars = list('abcdefghijklmnopqrstuvwxyz!@#$%^&*()1234567890-=[];,./_+{}:"<>?|`~')
        self.__alphabet_1 = []
        self.__alphabet_2 = []
        self.__alphabet_3 = []
        for i in range(10):
            self.__alphabet_1.append(self.__possible_chars.pop(libtcod.random_get_int(0, 0, len(self.__possible_chars) - 1)))
            self.__alphabet_2.append(self.__possible_chars.pop(libtcod.random_get_int(0, 0, len(self.__possible_chars) - 1)))
            self.__alphabet_3.append(self.__possible_chars.pop(libtcod.random_get_int(0, 0, len(self.__possible_chars) - 1)))
        self.__alphabet_1 = ''.join(self.__alphabet_1)
        self.__alphabet_2 = ''.join(self.__alphabet_2)
        self.__alphabet_3 = ''.join(self.__alphabet_3)
        self.__alphabets = (self.__alphabet_1, self.__alphabet_2, self.__alphabet_3)

        self.__make_block(30)
        self.__encode_block()

        # items

        # block locations:
        #
        # bananas     [3][4] - [3][5]
        # pretzels    [0][2] - [0][3]
        # oranges     [15][0] - [15][1]
        # pears       [13][14] - [13][15]
        # sberries    [19][17] - [19][18]
        # cherries    [13][10] - [13][11]
        # apples      [7][8] - [7][9]

        # inv stores just the names of the item objects in the player's inventory for easy iteration
        # inv must start with one of each item in order to make counts of 0 readable
        inv = ['banana nectar', 'pretzel whip', 'orange peel', 'scroll of pear', 'strawberry jam', 'cherry bomb', 'appletini']
        for item in player.inventory: inv.append(item.name)

        for item in inv:

            quantity = self.__int2str(inv.count(item) - 1, 2)

            if item == 'banana nectar':
                self.__insert_data(3, 4, quantity)
            elif item == 'pretzel whip':
                self.__insert_data(0, 2, quantity)
            elif item == 'orange peel':
                self.__insert_data(15, 0, quantity)
            elif item == 'scroll of pear':
                self.__insert_data(13, 14, quantity)
            elif item == 'strawberry jam':
                self.__insert_data(19, 17, quantity)
            elif item == 'cherry bomb':
                self.__insert_data(13, 10, quantity)
            elif item == 'appletini':
                self.__insert_data(7, 8, quantity)

        # player stats

        # block locations:
        #
        # plvl        [4][5] - [4][6]
        # dlvl        [4][8] - [4][9]
        # hp          [7][2] - [7][5]
        # xp          [9][16] - [9][19]
        # xp cap      [21][9] - [21][12]
        # ghosts      [12][0] - [12][1]
        # score       [5][5] - [5][10]
        # lives       [23][15] - [23][16]

        self.__insert_data(4, 5, self.__int2str(player.level, 2))
        self.__insert_data(4, 8, self.__int2str(current_level.dlvl, 2))
        self.__insert_data(7, 2, self.__int2str(player.hp, 4))
        self.__insert_data(9, 16, self.__int2str(player.exp, 4))
        self.__insert_data(21, 9, self.__int2str(player.exp_next_level, 4))
        self.__insert_data(12, 0, self.__int2str(player.ghosts_killed, 2))
        self.__insert_data(5, 5, self.__int2str(player.score, 6))
        self.__insert_data(23, 15, self.__int2str(player.lives, 1))

        # game mode

        if game_mode == 'normal':
            self.__insert_data(25, 14, self.__int2str(1, 2))
        elif game_mode == 'idfa':
            self.__insert_data(25, 14, self.__int2str(2, 2))
        elif game_mode == 'god':
            self.__insert_data(25, 14, self.__int2str(3, 2))

        # writing the block

        with open('sdata', 'r') as f:
            tmp = f.readline()
            tmp += f.readline()
            tmp += f.readline()
        with open('sdata', 'w') as f:
            f.write(tmp)
            f.write('\n')
            for line in self.__block: f.write(line)

    def load(self):

        global level_number
        global player
        global spawn_timer
        global game_msgs
        global possible_etchings
        global global_debug, ghosts_killed
        global game_mode

        if exists('sdata'):
            with open('sdata', 'r') as f:
                for i in range(4): f.readline()
                data = []
                for i in range(30): data.append(f.readline()[:-1])
        else:
            print "File error."

        # establishing a dictionary as the key, combining all three
        key_1 = data[2][2:13]
        key_2 = data[2][14:25]
        key_3 = data[3][17:28]
        key = {}
        for i in range(10):
            key[i] = str(key_1[i] + key_2[i] + key_3[i])

        bananas = list(data[3][4:6])
        pretzels = list(data[0][2:4])
        oranges = list(data[15][0:2])
        pears = list(data[13][14:16])
        sberries = list(data[19][17:19])
        cherries = list(data[13][10:12])
        apples = list(data[7][8:10])
        inv = {'bananas':bananas, 'pretzels':pretzels, 'oranges':oranges, 'pears':pears, 'sberries':sberries, 'cherries':cherries, 'apples':apples}
        for item in inv:
            for i in range(len(inv[item])):
                for number in key:
                    if inv[item][i] in key[number]:
                        inv[item][i] = str(number)
                        break
            inv[item] = int(''.join(inv[item]))

        plvl = list(data[4][5:7])
        dlvl = list(data[4][8:10])
        hp = list(data[7][2:6])
        xp = list(data[9][16:20])
        xp_next = list(data[21][9:13])
        ghosts = list(data[12][0:2])
        score = list(data[5][5:11])
        lives = list(data[23][15])
        player_data = {'plvl':plvl, 'dlvl':dlvl, 'hp':hp, 'xp':xp, 'xp_next':xp_next, 'ghosts':ghosts, 'score':score, 'lives': lives}
        for item in player_data:
            for i in range(len(player_data[item])):
                for number in key:
                    if player_data[item][i] in key[number]:
                        player_data[item][i] = str(number)
                        break
            player_data[item] = int(''.join(player_data[item]))

        player = Player(0, 0, '@', libtcod.yellow, 'you', blocked = True, level = player_data['plvl'])
        player.lives = player_data['lives']
        player.score = player_data['score']
        player.level_up_score = player.score - ((player.score / LEVEL_UP_POINTS) * LEVEL_UP_POINTS)

        mode = list(data[25][14:16])
        for i in range(len(mode)):
            for number in key:
                if mode[i] in key[number]:
                    mode[i] = str(number)
                    break
        mode = int(''.join(mode))
        if mode == 1: game_mode = 'normal'
        elif mode == 2: game_mode = 'idfa'
        elif mode == 3: game_mode = 'god'

        # leveling up attack and defense
        if game_mode in ('normal', 'idfa'):

            for i in range(player_data['plvl'] - 1):

                # attack
                old_dice = player.attack_dice.split('d')

                if int(old_dice[1]) != player.attack_cap:
                    player.attack_dice = '%dd%d' % (int(old_dice[0]), int(old_dice[1]) + 2)
                else:

                    player.attack_dice = '%dd%d' % (int(old_dice[0]) + 1, player.attack_base)
                    player.attack_base += 2
                    player.attack_cap += 2

                # defense
                old_dice = player.defense_dice.split('d')

                if int(old_dice[1]) != player.defense_cap:
                    player.defense_dice = '%dd%d' % (int(old_dice[0]), int(old_dice[1]) + 1)
                else:
                    player.defense_dice = '%dd%d' % (int(old_dice[0]) + 1, player.defense_base)
                    player.defense_cap += 2
                    player.defense_base += 2

                # new hp cap
                player.max_hp += int(player.max_hp * 0.25)

        else:

            player.attack_dice = '50d20'
            player.defense_dice = '50d12'

        player.hp = player_data['hp']
        player.exp_next_level = player_data['xp_next']
        player.exp = player_data['xp']

        for i in range(inv['apples']):
            player.inventory.append(Item(0, 0, 'a', libtcod.dark_green, 'appletini', 'You suck down the appletini.'))
        for i in range(inv['sberries']):
            player.inventory.append(Item(0, 0, 's', libtcod.pink, 'strawberry jam', 'You spread the jam on the ground, fall through the floor, and drop from the ceiling somewhere else.'))
        for i in range(inv['pears']):
            player.inventory.append(Item(0, 0, 'p', libtcod.chartreuse, 'scroll of pear', 'You read the words on the scroll, and it crumbles away.'))
        for i in range(inv['cherries']):
            player.inventory.append(Item(0, 0, 'c', libtcod.red, 'cherry bomb', 'You light the cherry bomb and duck. KABOOM!'))
        for i in range(inv['oranges']):
            player.inventory.append(Item(0, 0, 'o', libtcod.Color(255, 165, 0), 'orange peel', 'You don the giant orange peel. You feel tougher.'))
        for i in range(inv['pretzels']):
            player.inventory.append(Item(0, 0, 'p', libtcod.dark_orange, 'pretzel whip', 'You untwist the pretzel and wield it.'))
        for i in range(inv['bananas']):
            player.inventory.append(Item(0, 0, 'a', libtcod.light_yellow, 'banana nectar', 'You drip the banana nectar onto your tongue.'))

        level_number = player_data['dlvl']
        current_level = None

        player.ghosts_killed = player_data['ghosts']

        game_msgs = []
        spawn_timer = SPAWN_RATE

        possible_etchings = [
            'etching: "Lure all the ghosts to each power pellet. It\'s working for me." - JD',
            'etching: "Some say the only way to lift a haunting is to vanquish all the ghosts associated with it." - M. Eastwick',
            'etching: "Personally, I wouldn\'t drink any banana nectar unless my next level was far off." - Anon.',
            'etching: "May your pretzel whips be as salty as they are deadly...." - Laurent',
            'etching: "Pinky likes turning. Use it to your advantage." - Ascot',
            'etching: "Strawberry jam can get you out of most other kinds of jams." - Dirk',
            'etching: "Orange then pretzel. That\'s what my Ma always said." - Anon',
            'etching: "An honest man is always in trouble." - Henry F.',
            'etching: "Swing your weapon around if you want to waste some time." - A lazy samurai',
            'etching: "Sometimes it\'s better to lose a life than lose an item." - Banner',
            'etching: "It is what it is." - Officer Benson',
            'etching: "JD <3 MY"',
            'etching: "Try not to use appletinis while being attacked." - Geese',
            'etching: "Use pear spell to attack from behind." - DK',
            'etching: "It\'s a me." - Mario',
            'etching: "Hit, run, heal. Hit, run, heal."'
        ]

        load_next_level()

        libtcod.console_clear(0)
        fov_recompute = True

        with open('sdata', 'r') as f:
            tmp = f.readline()
            tmp += f.readline()
            tmp += f.readline()
        with open('sdata', 'w') as f:
            f.write(tmp)
            f.write('\n')

#---------------#
### FUNCTIONS ###
#---------------#

def render_all(level):

    global fov_map
    global fov_recompute

    if level.dark == False:

        # rendering level map
        for y in range(LVL_HEIGHT):
            for x in range(LVL_WIDTH):
                if level.level_map[x][y].blocked == True:
                    libtcod.console_set_char_background(con, x, y, level.color_wall, libtcod.BKGND_SET)
                else:
                    libtcod.console_set_char_background(con, x, y, level.color_floor, libtcod.BKGND_SET)

                libtcod.console_set_default_background(con, level.color_floor)
                libtcod.console_set_default_foreground(con, level.color_wall)

                if level.level_map[x][y].style == 'top-left-corner':
                    libtcod.console_put_char(con, x, y, 201, libtcod.BKGND_SET)
                elif level.level_map[x][y].style == 'top-right-corner':
                    libtcod.console_put_char(con, x, y, 187, libtcod.BKGND_SET)
                elif level.level_map[x][y].style == 'bot-left-corner':
                    libtcod.console_put_char(con, x, y, 200, libtcod.BKGND_SET)
                elif level.level_map[x][y].style == 'bot-right-corner':
                    libtcod.console_put_char(con, x, y, 188, libtcod.BKGND_SET)
                elif level.level_map[x][y].style == 'horizontal-bar':
                    libtcod.console_put_char(con, x, y, 205, libtcod.BKGND_SET)
                elif level.level_map[x][y].style == 'vertical-bar':
                    libtcod.console_put_char(con, x, y, 186, libtcod.BKGND_SET)
                elif level.level_map[x][y].style == 'cage-door':
                    libtcod.console_set_default_foreground(con, libtcod.white)
                    libtcod.console_put_char(con, x, y, 196, libtcod.BKGND_SET)

    else:

        if fov_recompute:
            fov_recompute = False
            libtcod.map_compute_fov(fov_map, player.x, player.y, FOV_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

            for y in range(LVL_HEIGHT):
                for x in range(LVL_WIDTH):
                    visible = libtcod.map_is_in_fov(fov_map, x, y)
                    wall = level.level_map[x][y].blocked
                    if not visible:
                        if level.level_map[x][y].explored:
                            if wall:
                                libtcod.console_set_char_background(con, x, y, level.color_wall * 0.3, libtcod.BKGND_SET)

                                libtcod.console_set_default_background(con, level.color_floor * 0.3)
                                libtcod.console_set_default_foreground(con, level.color_wall * 0.3)

                                if level.level_map[x][y].style == 'top-left-corner':
                                    libtcod.console_put_char(con, x, y, 201, libtcod.BKGND_SET)
                                elif level.level_map[x][y].style == 'top-right-corner':
                                    libtcod.console_put_char(con, x, y, 187, libtcod.BKGND_SET)
                                elif level.level_map[x][y].style == 'bot-left-corner':
                                    libtcod.console_put_char(con, x, y, 200, libtcod.BKGND_SET)
                                elif level.level_map[x][y].style == 'bot-right-corner':
                                    libtcod.console_put_char(con, x, y, 188, libtcod.BKGND_SET)
                                elif level.level_map[x][y].style == 'horizontal-bar':
                                    libtcod.console_put_char(con, x, y, 205, libtcod.BKGND_SET)
                                elif level.level_map[x][y].style == 'vertical-bar':
                                    libtcod.console_put_char(con, x, y, 186, libtcod.BKGND_SET)
                                elif level.level_map[x][y].style == 'cage-door':
                                    libtcod.console_set_default_foreground(con, libtcod.white * 0.3)
                                    libtcod.console_put_char(con, x, y, 196, libtcod.BKGND_SET)

                            else:
                                libtcod.console_set_char_background(con, x, y, level.color_floor * 0.3, libtcod.BKGND_SET)

                    else:
                        # in the player's FOV
                        if wall:
                            libtcod.console_set_char_background(con, x, y, level.color_wall * 0.6, libtcod.BKGND_SET)

                            libtcod.console_set_default_background(con, level.color_floor * 0.6)
                            libtcod.console_set_default_foreground(con, level.color_wall * 0.6)

                            if level.level_map[x][y].style == 'top-left-corner':
                                libtcod.console_put_char(con, x, y, 201, libtcod.BKGND_SET)
                            elif level.level_map[x][y].style == 'top-right-corner':
                                libtcod.console_put_char(con, x, y, 187, libtcod.BKGND_SET)
                            elif level.level_map[x][y].style == 'bot-left-corner':
                                libtcod.console_put_char(con, x, y, 200, libtcod.BKGND_SET)
                            elif level.level_map[x][y].style == 'bot-right-corner':
                                libtcod.console_put_char(con, x, y, 188, libtcod.BKGND_SET)
                            elif level.level_map[x][y].style == 'horizontal-bar':
                                libtcod.console_put_char(con, x, y, 205, libtcod.BKGND_SET)
                            elif level.level_map[x][y].style == 'vertical-bar':
                                libtcod.console_put_char(con, x, y, 186, libtcod.BKGND_SET)
                            elif level.level_map[x][y].style == 'cage-door':
                                libtcod.console_set_default_foreground(con, libtcod.white)
                                libtcod.console_put_char(con, x, y, 196, libtcod.BKGND_SET)

                        else:
                            libtcod.console_set_char_background(con, x, y, level.color_floor * 0.6, libtcod.BKGND_SET)


                        level.level_map[x][y].explored = True

    # rendering objects
    for effect in level.effects:
        effect.draw()
    for effect in level.effects:
        if effect.name == 'staircase': effect.draw()
    for corpse in level.corpses:
        corpse.draw()
    for pellet in level.pellets:
        pellet.draw()
    for item in level.items:
        item.draw()
    for ghost in level.ghosts:
        ghost.draw()
    player.draw()

    # render the message log
    libtcod.console_set_default_foreground(msg_panel, libtcod.white)
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(msg_panel, color)
        libtcod.console_print(msg_panel, MSG_X + 1, y, BLANK_LINE)
        libtcod.console_print(msg_panel, MSG_X + 1, y, line)
        y += 1
    libtcod.console_set_default_foreground(msg_panel, libtcod.white)
    libtcod.console_print_frame(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, False, libtcod.BKGND_OVERLAY, 0)

    # prepare to render the GUI panel
    libtcod.console_set_default_background(gui_panel, libtcod.black)
    libtcod.console_clear(gui_panel)

    # show the player's stats
    render_bar((SCREEN_WIDTH - LVL_WIDTH) / 2, 1, BAR_WIDTH, 'HP', player.hp, player.max_hp, libtcod.light_blue, libtcod.dark_red)
    render_bar((SCREEN_WIDTH - LVL_WIDTH) / 2, 2, BAR_WIDTH, 'XP', player.exp, player.exp_next_level, libtcod.light_violet, libtcod.dark_violet)

    libtcod.console_print(gui_panel, 7, 3, BLANK_LINE)
    libtcod.console_print(gui_panel, 7, 4, BLANK_LINE)
    libtcod.console_print(gui_panel, 7, 4, "SCORE: %d" % player.score)
    libtcod.console_print(gui_panel, 7, 5, "LIVES: %d" % player.lives)
    libtcod.console_set_alignment(gui_panel, libtcod.RIGHT)
    libtcod.console_print(gui_panel, LVL_WIDTH + 6, 4, "PLVL: %d" % player.level)
    libtcod.console_print(gui_panel, LVL_WIDTH + 6, 5, "DLVL: %d" % level.dlvl)
    libtcod.console_set_alignment(gui_panel, libtcod.LEFT)

    libtcod.console_set_default_foreground(gui_panel, libtcod.white)
    libtcod.console_print_frame(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, False, libtcod.BKGND_NONE, 0)

    # blit the contents of gui_panel and msg_panel to the root console
    libtcod.console_blit(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
    libtcod.console_blit(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, 0, 0, MSG_Y)

    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)

def clear_msgs():

    global game_msgs

    game_msgs = []

    for i in range(MSG_HEIGHT):
        libtcod.console_print(msg_panel, 0, i, BLANK_LINE)

def clear_all():

    for obj in object_list():
        obj.clear()

    player.clear()

def handle_keys():

    global game_state
    global fov_recompute
    global play_sounds
    global game_mode

    if player.state != 'dead' and (game_state == 'playing' or game_state == 'changing levels'):

        used_item = False
        key = libtcod.console_wait_for_keypress(True)

        if key.vk == libtcod.KEY_F4:
                libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
                libtcod.mouse_show_cursor(not libtcod.mouse_is_cursor_visible())
                if libtcod.console_is_fullscreen(): message(">> Fullscreen: ON")
                else: message(">> Fullscreen: OFF")

        elif key.vk == libtcod.KEY_ESCAPE:
            message(">> Really quit? Y/N/R")
            clear_all()
            render_all(current_level)
            libtcod.console_flush()

            while True:
                key = libtcod.console_wait_for_keypress(True)
                if key.c in (ord('y'), ord('Y'), ord('q'), ord('Q')) or key.vk in (libtcod.KEY_ENTER, libtcod.KEY_KPENTER):
                    game_state = 'quit'
                    exit(0)
                    return
                elif key.vk == libtcod.KEY_ESCAPE or key.c in (ord('n'), ord('N')):
                    message(">> Continue.")
                    break
                elif key.c in (ord('r'), ord('R')):
                    game_mode = title_screen()
                    if game_mode == 'load game':
                        sd = SaveData()
                        sd.load()
                    else:
                        hello_world()

                    libtcod.console_clear(0)
                    fov_recompute = True
                    return

        elif key.c == ord('s'):
            play_sounds = not play_sounds
            if play_sounds: message(">> Sound: ON")
            else: message(">> Sound: OFF")
        elif key.c in (ord('i'), ord('I')):
            used_item = open_inventory()

        # if player is on staircase and presses '<', let them go up
        if game_state == 'changing levels':
            if key.c == ord('<') and (player.x, player.y) == (11, 7) and current_level.dlvl != 1:
                if play_sounds: sound_go_up.play()
                sd = SaveData()
                sd.save()
                game_state = 'initializing level'

        # movement
        if key.vk in (libtcod.KEY_UP, libtcod.KEY_KP8) or key.c == ord('k'):
            player_move_or_attack(0, -1)
            fov_recompute = True
        elif key.vk in (libtcod.KEY_DOWN, libtcod.KEY_KP2) or key.c == ord('j'):
            player_move_or_attack(0, 1)
            fov_recompute = True
        elif key.vk in (libtcod.KEY_LEFT, libtcod.KEY_KP4) or key.c == ord('h'):
            player_move_or_attack(-1, 0)
            fov_recompute = True
        elif key.vk in (libtcod.KEY_RIGHT, libtcod.KEY_KP6) or key.c == ord('l'):
            player_move_or_attack(1, 0)
            fov_recompute = True
        elif used_item:
            player.state = 'moved'
        else:
            player.state = 'did-not-move'

        if player.state == 'moved' and player.items_in_use != []:
            use_items(player.items_in_use)

def player_dead():

    global fov_recompute
    global play_sounds
    global game_state
    global game_mode

    render_all(current_level)

    if play_sounds: sound_death.play()

    player.char = '#'
    player.color = libtcod.red
    player.state = 'dead'
    player.lives -= 1

    if player.lives == 0:
        message("Game over!", libtcod.red)
        message(">> Press ENTER to restart or ESC to quit....")
        render_all(current_level)
        libtcod.console_flush()

        if play_sounds: sound_game_over.play()

        if game_mode == 'normal':
            with open('sdata', 'r') as f:
                current_high_score = f.readline()
                if current_high_score[-2] == '!':
                    current_high_score = current_high_score[:-2]
                current_high_score = int(current_high_score[12:])
            if player.score > current_high_score:
                with open('sdata', 'w') as f:
                    f.write('High score: %d' % player.score)
                    f.write('\n')
                    f.write('Died on level %d.' % current_level.dlvl)
                    f.write('\n')
                    f.write('Vanquished %d ghosts.' % player.ghosts_killed)
                    f.write('\n')

        with open('sdata', 'r') as f:
            tmp = f.readline()
            tmp += f.readline()
            tmp += f.readline()
        with open('sdata', 'w') as f:
            f.write(tmp)
            f.write('\n')

        kill_screen()
        player.ghosts_killed = 0

        while True:

            key = libtcod.console_wait_for_keypress(True)
            if key.vk in (libtcod.KEY_ENTER, libtcod.KEY_KPENTER):
                game_mode = title_screen()
                hello_world()
                libtcod.console_clear(0)
                fov_recompute = True
                render_all(current_level)
                libtcod.console_flush()
                clear_all()
                return
            if key.vk == libtcod.KEY_ESCAPE:
                game_state = 'quit'
                exit(0)
                return

    else:
        message("You died.")
        message(">> Press ENTER to continue.")
        render_all(current_level)
        libtcod.console_flush()

        while True:
            key = libtcod.console_wait_for_keypress(True)
            if key.vk in (libtcod.KEY_ENTER, libtcod.KEY_KPENTER):
                libtcod.console_set_default_background(con, libtcod.black)
                libtcod.console_clear(con)
                current_level.items = []
                player.set_pos(player.startx, player.starty)
                player.hp = player.max_hp
                player.char = '@'
                player.color = libtcod.yellow
                player.state = 'did-not-move'
                player.items_in_use = []
                player.attack_bonus = 0
                player.defense_bonus = 0

                if play_sounds:
                    sound_go_up.play()

                # spawn them ther ghosts!
                if current_level.dlvl != 1:
                    for ghost in current_level.ghosts:
                        if ghost.state == 'fleeing': change_ghost(ghost)
                        if ghost.name != 'Blinky': current_level.ghosts_in_cage.append(ghost)

                    for ghost in current_level.ghosts:
                        ghost.set_pos(ghost.startx, ghost.starty)
                        if ghost.name != 'Blinky': ghost.state = 'spawning'
                        else: ghost.state = 'aggressive'

                else:
                    for ghost in current_level.ghosts:
                        ghost.set_pos(ghost.startx, ghost.starty)
                        ghost.state = 'aggressive'

                spawn_timer = SPAWN_RATE

                fov_recompute = True
                render_all(current_level)
                libtcod.console_flush()
                clear_all()

                break

def throw_dice(dice):
    '''
    Takes a classic dice combination (e.g. "2d10") and finds the total roll.
    '''

    number_of_dice = int(dice.split('d')[0])
    sides = int(dice.split('d')[1])

    total = 0
    for roll in range(number_of_dice):
        total += libtcod.random_get_int(0, 1, sides)

    return total

def spawn_ghosts():
    global spawn_timer

    if spawn_timer > 0:
        spawn_timer -= 1
    elif spawn_timer == 0:
        spawn_timer = SPAWN_RATE
        current_level.ghosts_in_cage[0].state = 'spawned'
        current_level.ghosts_in_cage.pop(0).set_pos(11, 7)

def player_move_or_attack(dx, dy):

    x = player.x + dx
    y = player.y + dy

    targets = []
    for ghost in current_level.ghosts:
        if ghost.x == x and ghost.y == y and ghost not in current_level.corpses:
            targets.append(ghost)

    eat = False
    for target in targets:
        if target.state == 'fleeing':
            capture(target)
            eat = True
        else:
            player.attack(targets[0])
            break

    if targets == [] or eat:
        player.move(dx, dy)

    get_pellets()
    if player.state == 'moved': check_for_items()

    # play step sound if no pellet or item
    if play_sounds and not pygame.mixer.get_busy():
        index = libtcod.random_get_int(0, 0, len(sound_step) - 1)
        sound_step[index].play()

def handle_ghosts():

    if player.state == 'moved':

        # main action
        for ghost in current_level.ghosts:

            if ghost.state == 'aggressive': ghost.chase()
            elif ghost.state == 'attacking': ghost.attack()
            elif ghost.state == 'fleeing': ghost.flee()
            elif ghost.state == 'captured': ghost.respawn()
            elif ghost.state == 'spawned': ghost.state = 'aggressive'
            elif ghost.state == 'dead': pass

def get_pellets():

    for i in range(len(current_level.pellets)):

        # if the player's coordinates match those of a pellet's, the pellet is popped
        if current_level.pellets[i].x == player.x and current_level.pellets[i].y == player.y:
            if current_level.pellets[i].name == 'power pellet':
                message(player.name.capitalize() + " collected a " + current_level.pellets[i].name + ".")
            player.add_to_score(current_level.pellets[i].points)

            # normal pellets restore health or give exp
            if current_level.pellets[i].name == 'pellet':

                if play_sounds and not pygame.mixer.get_busy():
                    index = libtcod.random_get_int(0, 0, len(sound_collect_pellet) - 1)
                    sound_collect_pellet[index].play()

                if player.hp < player.max_hp:
                    player.hp += int(player.max_hp / 30) + 1
                    if player.hp > player.max_hp:
                        player.hp = player.max_hp
                else:
                    if player.exp + 1 < player.exp_next_level:
                        player.exp += 1
                    else:
                        player.level_up()

            # the power pellet will change the ghosts to aggressive mode and reset the number of ghosts eaten
            if current_level.pellets[i].name == 'power pellet':

                if play_sounds and not pygame.mixer.get_busy():
                    index = libtcod.random_get_int(0, 0, len(sound_collect_pellet) - 1)
                    sound_collect_power_pellet.play()

                for ghost in current_level.ghosts:
                    if ghost.state == 'aggressive': change_ghost(ghost)
                player.ghosts_eaten = 0
            current_level.pellets.pop(i)
            break

def check_for_items():

    for item in current_level.items:
        if ((player.x, player.y) == (item.x, item.y)) and item.obtainable == True:
            if item.name[0] in 'aeio':
                message("You pick up an %s." % item.name, item.color)
            else:
                message("You pick up a %s." % item.name, item.color)
            player.inventory.append(item)
            current_level.items.pop(current_level.items.index(item))
            if play_sounds: sound_item.play()

        elif ((player.x, player.y) == (item.x, item.y)) and item.obtainable == False and item.name[:7] != 'charred':
            if item.name[0] in 'aeio':
                message("You see here an %s." % item.name, item.color)
            else:
                message("You see here a %s." % item.name, item.color)

    for effect in current_level.effects:

        if ((player.x, player.y) == (effect.x, effect.y)) and effect.name[:7] != 'charred':
            if effect.name[:7] != 'etching':
                if effect.name[0] in 'aeio':
                    message("You see here an %s." % effect.name)
                else:
                    message("You see here a %s." % effect.name)
            else:
                    message("You see here a faint message etched into the floor:")
                    message(effect.name[9:], libtcod.dark_grey)

def object_list():

    objects = []

    for effect in current_level.effects:
        objects.append(effect)
    for corpse in current_level.corpses:
        objects.append(corpse)
    for pellet in current_level.pellets:
        objects.append(pellet)
    for item in current_level.items:
        objects.append(item)
    for ghost in current_level.ghosts:
        objects.append(ghost)
    objects.append(player)

    return objects

def is_blocked(x, y):

    if current_level.level_map[x][y].blocked:
        return True

    for obj in object_list():
        if obj.blocked and obj.x == x and obj.y == y:
            return True

    return False

def change_ghost(ghost):

    if ghost.state == 'aggressive':

            ghost.color = libtcod.Color(70, 70, 235)
            ghost.char = ghost.char.lower()
            ghost.blocked = False
            ghost.state = 'fleeing'

            opposite_direction = []
            for i in ghost.direction:
                opposite_direction.append(i - (i * 2))
                ghost.direction = opposite_direction

    elif ghost.state == 'captured' or ghost.state == 'fleeing':

            ghost.color = ghost.original_color
            ghost.char = ghost.char.upper()
            ghost.blocked = True
            ghost.state = 'aggressive'

def capture(ghost):

    if play_sounds: sound_eat_ghost.play()

    ghost.color = ghost.original_color
    ghost.char = ghost.char.upper()
    if ghost.name != 'Blinky': ghost.set_pos(ghost.startx, ghost.starty)
    else: ghost.set_pos(11, 9)
    ghost.state = 'captured'

    # double the score for eating depending on how many ghosts have been eaten
    player.ghosts_eaten += 1

    points = EAT_POINTS
    for i in range(player.ghosts_eaten - 1):
        points *= 2
    player.add_to_score(points)

    message(player.name.capitalize() + " ate " + ghost.name + " for " + str(points) + " points.", libtcod.Color(50, 50, 215))

def get_distance(ax, ay, bx, by):

    length = abs(ax - bx) # length of triangle
    height = abs(ay - by) # height of triangle
    return math.sqrt((length * length) + (height * height))

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    '''
    Render a bar of any kind.
    '''

    # calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)

    # render the background first
    libtcod.console_set_default_background(gui_panel, back_color)
    libtcod.console_rect(gui_panel, x, y, total_width, 1, False, libtcod.BKGND_SET)

    # render the bar on top
    libtcod.console_set_default_background(gui_panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(gui_panel, x, y, bar_width, 1, False, libtcod.BKGND_SET)

    # write some values on top for clarity
    libtcod.console_set_default_foreground(gui_panel, libtcod.white)
    libtcod.console_set_alignment(gui_panel, libtcod.CENTER)
    libtcod.console_print(gui_panel, x + total_width / 2, y, name + ': ' + str(value) + '/' + str(maximum))
    libtcod.console_set_alignment(gui_panel, libtcod.LEFT)

def message(new_msg, color = libtcod.white):

    global game_msgs

    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH - 2)

    for line in new_msg_lines:

        # if the msg buffer is full, remove the first to make room
        if len(game_msgs) == MSG_HEIGHT - 2:
            del game_msgs[0]

        # add the new line
        game_msgs.append( (line, color) )

def win_level():
    global game_state

    if play_sounds and current_level.dlvl != 1:
        pygame.mixer.stop()
        sound_staircase.play()

    if current_level.dlvl not in (3, 2):
        current_level.items = []

    if current_level.dlvl != 1:
        message("A staircase collapses through the ceiling...")
        staircase = Effect(11, 7, '<', libtcod.white, 'staircase')
        current_level.effects.append(staircase)
        current_level.pellets = []
        game_state = 'changing levels'
    else:
        message("The seal to the throne room flickers and weakens.")
        message("Stand at the altar and hold the Mace of the Four Winds high!")
        current_level.level_map[11][8].blocked = False
        libtcod.console_put_char_ex(con, 11, 8, '-', libtcod.dark_grey, libtcod.darkest_purple)
        game_state = 'changing levels'

def load_next_level():

    global game_state, game_mode
    global level_number
    global current_level
    global fov_recompute
    global con, gui_panel, msg_panel, splash_panel, inv_panel

    con = libtcod.console_new(LVL_WIDTH, LVL_HEIGHT)
    gui_panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
    msg_panel = libtcod.console_new(SCREEN_WIDTH, MSG_HEIGHT)
    splash_panel = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
    inv_panel = libtcod.console_new(LVL_WIDTH, LVL_HEIGHT)

    level_number -= 1
    clear_msgs()
    libtcod.console_set_default_background(con, libtcod.black)

    player.items_in_use = []
    player.attack_bonus = 0
    player.defense_bonus = 0

    # settings for the four major boards
    if level_number >= 13:
        libtcod.console_clear(con)
        current_level = Level(dlvl = level_number, sublvl = 15 - level_number + 1, map = level_15_13, color_wall = libtcod.Color(252, 150, 138), color_floor = libtcod.darkest_grey)
        if level_number == 13:
            current_level.effects.append(Effect(6, 11, 's', libtcod.grey, 'iron chain'))
    elif level_number >= 10 and level_number <= 12:
        libtcod.console_clear(con)
        current_level = Level(dlvl = level_number, sublvl = 12 - level_number + 1, map = level_10_12, color_wall = libtcod.Color(92, 200, 252), color_floor = libtcod.darkest_grey)
    elif level_number >= 7 and level_number <= 9:
        libtcod.console_clear(con)
        current_level = Level(dlvl = level_number, sublvl = 9 - level_number + 1, map = level_7_9, color_wall = libtcod.Color(222,162,112), color_floor = libtcod.black)
    elif level_number >= 4 and level_number <= 6:
        libtcod.console_clear(con)
        current_level = Level(dlvl = level_number, sublvl = 6 - level_number + 1, map = level_4_6, color_wall = libtcod.Color(56, 56, 252), color_floor = libtcod.black)
    elif level_number == 3 and player.ghosts_killed >= 48 and game_mode == 'normal':
        libtcod.console_clear(con)
        current_level = Level(dlvl = level_number, sublvl = 2, map = level_3, color_wall = libtcod.dark_grey, color_floor = libtcod.Color(30, 0, 0))
    elif level_number == 2:
        libtcod.console_clear(con)
        current_level = Level(dlvl = level_number, sublvl = 3, map = level_2, color_wall = libtcod.dark_grey, color_floor = libtcod.Color(30, 0, 0))
    elif level_number == 1:
        libtcod.console_clear(con)
        current_level = Level(dlvl = level_number, sublvl = 3, map = level_1, color_wall = libtcod.dark_grey, color_floor = libtcod.darkest_purple)
    elif level_number == 3 and (player.ghosts_killed < 48 or game_mode != 'normal'):
        bad_ending_animation()
        bad_ending()
        return
    else:
        good_ending()
        return

    # dark levels
    if level_number in [13, 10, 7, 4, 3, 2, 1]:
        current_level.dark = True

    current_level.set_up()

    # place messages
    if current_level.dlvl not in (3, 2, 1):

        if libtcod.random_get_int(0, 1, 3) == 1:

            current_etching = possible_etchings.pop(libtcod.random_get_int(0, 0, len(possible_etchings) - 1))

            while True:
                effect_x = libtcod.random_get_int(0, 0, LVL_WIDTH - 2)
                effect_y = libtcod.random_get_int(0, 0, LVL_HEIGHT - 2)
                if not current_level.level_map[effect_x][effect_y].blocked:
                    break

            current_level.effects.append(Effect(effect_x, effect_y, '#', libtcod.darker_grey, current_etching))

    game_state = 'playing'

    fov_recompute = True
    if current_level.dlvl != START_LEVEL - 1 and current_level.dlvl not in (3, 2, 1):
        message("You walk up the stairs to %s." % current_level.name, libtcod.yellow)
    if current_level.dark and current_level.dlvl not in (3, 2, 1):
        message("It's dark in here!", current_level.color_wall)
    if current_level.dlvl == 3:
        message("A cold breeze scurries down your spine....", libtcod.desaturated_violet)
    if current_level.dlvl == 2:
        message("It's quiet.", libtcod.desaturated_violet)
    if current_level.dlvl == 1:
        message("....", libtcod.desaturated_violet)

def generate_item():
    '''
    Decides which item to generate and places it on a random warp point.
    '''

    potential_entries = []
    for x in range(LVL_WIDTH):
        for y in range(LVL_HEIGHT):
            if current_level.level_map[x][y].warp:
                potential_entries.append((x, y))

    entry = potential_entries[libtcod.random_get_int(0, 0, len(potential_entries) - 1)]
    x, y = entry[0], entry[1]

    which_item = libtcod.random_get_int(0, 1, 100)

    if which_item in range(0, 34): # 34%

        current_level.items.append(Item(x, y, 'a', libtcod.dark_green, 'appletini', 'You suck down the appletini.'))
        current_level.items[-1].get_target_exit()

    elif which_item in range(34, 44): # 10%

        current_level.items.append(Item(x, y, 'c', libtcod.red, 'cherry bomb', 'You light the cherry bomb and duck. KABOOM!'))
        current_level.items[-1].get_target_exit()

    elif which_item in range(44, 59): # 15%

        current_level.items.append(Item(x, y, 's', libtcod.pink, 'strawberry jam', 'You spread the jam on the ground, fall through the floor, and drop from the ceiling somewhere else.'))
        current_level.items[-1].get_target_exit()

    elif which_item in range(59, 75): # 16%

        current_level.items.append(Item(x, y, 'o', libtcod.Color(255, 165, 0), 'orange peel', 'You don the giant orange peel. You feel tougher.'))
        current_level.items[-1].get_target_exit()

    elif which_item in range(75, 83): # 8%

        current_level.items.append(Item(x, y, 'p', libtcod.dark_orange, 'pretzel whip', 'You untwist the pretzel and wield it.'))
        current_level.items[-1].get_target_exit()

    elif which_item in range(83, 95): # 12%

        current_level.items.append(Item(x, y, 'p', libtcod.chartreuse, 'scroll of pear', 'You read the words on the scroll, and it crumbles away.'))
        current_level.items[-1].get_target_exit()

    elif which_item in range(95, 100): # 5%

        current_level.items.append(Item(x, y, 'b', libtcod.light_yellow, 'banana nectar', 'You drip the banana nectar onto your tongue.'))
        current_level.items[-1].get_target_exit()

    else:
        print "Item error."

def blit_effects(panel, frames, color, coords, flush = False, FPSmod = FPS):
    '''
    Blits the animations of certain effects by coordinate and color.
    '''

    lx, ly = range(LVL_WIDTH), range(LVL_HEIGHT)
    libtcod.console_set_default_foreground(panel, color)

    for frame in frames:
        for pair in coords:
            x, y = player.x + pair[0], player.y + pair[1]
            if x in lx and y in ly:
                libtcod.console_put_char(panel, x, y, frame, libtcod.BKGND_NONE)

        libtcod.console_blit(panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)

        if flush:

            for i in range(FPS / FPSmod):
                libtcod.console_flush()

def hello_world():

    global level_number
    global player
    global spawn_timer
    global game_msgs
    global possible_etchings
    global global_debug, ghosts_killed

    possible_etchings = [
        'etching: "Lure all the ghosts to each power pellet. It\'s working for me." - JD',
        'etching: "Some say the only way to lift a haunting is to vanquish all the ghosts associated with it." - M. Eastwick',
        'etching: "Personally, I wouldn\'t drink any banana nectar unless my next level was far off." - Anon.',
        'etching: "May your pretzel whips be as salty as they are deadly...." - Laurent',
        'etching: "Pinky likes turning. Use it to your advantage." - Ascot',
        'etching: "Strawberry jam can get you out of most other kinds of jams." - Dirk',
        'etching: "Orange then pretzel. That\'s what my Ma always said." - Anon',
        'etching: "An honest man is always in trouble." - Henry F.',
        'etching: "Swing your weapon around if you want to waste some time." - A lazy samurai',
        'etching: "Sometimes it\'s better to lose a life than lose an item." - Banner',
        'etching: "It is what it is." - Officer Benson',
        'etching: "JD <3 MY"',
        'etching: "Try not to use appletinis while being attacked." - Geese',
        'etching: "Use pear spell to attack from behind." - DK',
        'etching: "It\'s a me." - Mario',
        'etching: "Hit, run, heal. Hit, run, heal."'
    ]

    if game_mode == 'god':
        player = Player(0, 0, '@', libtcod.yellow, 'you', blocked = True, level = 1, attack_dice = '50d20', defense_dice = '50d12', lives = 3)
        player.defense = 1000
        for i in range(25):
            player.inventory.append(Item(0, 0, 'a', libtcod.dark_green, 'appletini', 'You suck down the appletini.'))
            player.inventory.append(Item(0, 0, 'b', libtcod.light_yellow, 'banana nectar', 'You drip the banana nectar onto your tongue.'))
            player.inventory.append(Item(0, 0, 'p', libtcod.chartreuse, 'scroll of pear', 'You read the words on the scroll, and it crumbles away.'))
            player.inventory.append(Item(0, 0, 'p', libtcod.dark_orange, 'pretzel whip', 'You untwist the pretzel and wield it.'))
            player.inventory.append(Item(0, 0, 's', libtcod.pink, 'strawberry jam', 'You spread the jam on the ground, fall through the floor, and drop from the ceiling somewhere else.'))
            player.inventory.append(Item(0, 0, 'o', libtcod.Color(255, 165, 0), 'orange peel', 'You don the giant orange peel. You feel tougher.'))
            player.inventory.append(Item(0, 0, 'c', libtcod.red, 'cherry bomb', 'You light the cherry bomb and duck. KABOOM!'))
    elif game_mode == 'idfa':
        player = Player(0, 0, '@', libtcod.yellow, 'you', blocked = True, level = 1)
        player.defense = 1000
        for i in range(25):
            player.inventory.append(Item(0, 0, 'a', libtcod.dark_green, 'appletini', 'You suck down the appletini.'))
            player.inventory.append(Item(0, 0, 'b', libtcod.light_yellow, 'banana nectar', 'You drip the banana nectar onto your tongue.'))
            player.inventory.append(Item(0, 0, 'p', libtcod.chartreuse, 'scroll of pear', 'You read the words on the scroll, and it crumbles away.'))
            player.inventory.append(Item(0, 0, 'p', libtcod.dark_orange, 'pretzel whip', 'You untwist the pretzel and wield it.'))
            player.inventory.append(Item(0, 0, 's', libtcod.pink, 'strawberry jam', 'You spread the jam on the ground, fall through the floor, and drop from the ceiling somewhere else.'))
            player.inventory.append(Item(0, 0, 'o', libtcod.Color(255, 165, 0), 'orange peel', 'You don the giant orange peel. You feel tougher.'))
            player.inventory.append(Item(0, 0, 'c', libtcod.red, 'cherry bomb', 'You light the cherry bomb and duck. KABOOM!'))
    else:
        player = Player(0, 0, '@', libtcod.yellow, 'you', blocked = True, level = 1)
        for i in range(5):
            player.inventory.append(Item(0, 0, 'a', libtcod.dark_green, 'appletini', 'You suck down the appletini.'))

    level_number = START_LEVEL
    current_level = None

    player.ghosts_killed = 0

    game_msgs = []
    spawn_timer = SPAWN_RATE

    if global_debug: #DEBUG
        player.score = 200000
        for i in range(20):
            player.inventory.append(Item(0, 0, 'c', libtcod.red, 'cherry bomb', 'You light the cherry bomb and duck. KABOOM!'))
        player.ghosts_killed = 22

    if game_state != 'quit': load_next_level()

def use_items(items):

    global fov_recompute

    effects_panel = libtcod.console_new(LVL_WIDTH, LVL_HEIGHT)

    lx, ly = range(LVL_WIDTH), range(LVL_HEIGHT)

    for item in items:

        if item.name == 'appletini':

            if (player.hp + player.max_hp / 3) < player.max_hp:
                player.hp += player.max_hp / 3
            else:
                player.hp = player.max_hp

            player.items_in_use.remove(item)

            matrix = [ [0 for y in range(3)] for x in range(3) ]

            for y in range(len(matrix)):
                for x in range(len(matrix[0])):
                    matrix[y][x] = libtcod.random_get_int(0, 0, 1)

            for effect in current_level.effects:
                effect.draw()
            for corpse in current_level.corpses:
                corpse.draw()
            for pellet in current_level.pellets:
                pellet.draw()
            for litem in current_level.items:
                litem.draw()
            for ghost in current_level.ghosts:
                ghost.draw()
            player.draw()
            libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)
            libtcod.console_set_default_foreground(effects_panel, libtcod.light_green)

            if play_sounds: sound_appletini.play()

            for frame in (':', '`', "-", "."):
                for y in range(len(matrix)):
                    for x in range(len(matrix[0])):
                        if matrix[y][x] == 1 and not (y == 1 and x == 1) and (player.x + x - 1 in range(LVL_WIDTH) and player.y + y - 1 in range(LVL_HEIGHT)):
                            libtcod.console_print(effects_panel, player.x + x - 1, player.y + y - 1, frame)
                            libtcod.console_blit(effects_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)

                for i in range(FPS / 5):
                    libtcod.console_flush()

            libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
            for obj in object_list(): obj.clear()
            libtcod.console_flush()

        elif item.name == 'cherry bomb':

            player.items_in_use.remove(item)

            for effect in current_level.effects:
                effect.draw()
            for corpse in current_level.corpses:
                corpse.draw()
            for pellet in current_level.pellets:
                pellet.draw()
            for litem in current_level.items:
                litem.draw()
            for ghost in current_level.ghosts:
                ghost.draw()
            player.draw()
            libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)

            if play_sounds: sound_cherry_bomb.play()

            '''
            # #
             @
            # #
            '''
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK3,), libtcod.dark_red, ((1, -1), (-1, 1), (1, 1), (-1, -1)), True, 8 )
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK3,), libtcod.dark_grey, ((0, -1), (0, 1), (1, 0), (-1, 0)), True, 8 )

            blit_effects( effects_panel, (' ',), libtcod.white, ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (0, 1), (1, 0), (-1, 0)) )

            '''
             #
            #@#
             #
            '''
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK3,), libtcod.dark_red, ((-1, 0), (1, 0), (0, -1), (0, 1)), True, 6)
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK3,), libtcod.dark_grey, ((-1, -1), (1, -1), (-1, 1), (1, 1)), True, 6)

            blit_effects( effects_panel, (' ',), libtcod.white, ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)) )

            '''
              ###
             #   #
            #     #
            #  @  #
            #     #
             #   #
              ###
            '''
            coords1 = ( (-3, -1), (-3, 0), (-3, 1), (-2, -2), (-2, 2), (-1, -3), (-1, 3), (0, -3), (0, 3), (3, -1), (3, 0), (3, 1), (2, -2), (2, 2), (1, -3), (1, 3))
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK3,), libtcod.dark_red, coords1)
            coords2 = ( (-2, -1), (-1, -2), (-2, 1), (-1, 2), (2, -1), (1, -2), (2, 1), (1, 2) )
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK3,), libtcod.dark_grey, coords2)
            coords3 = ( (-3, -2), (-2, -3), (-3, 2), (-2, 3), (3, -2), (2, -3), (3, 2), (2, 3) )
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK2,), libtcod.dark_grey, coords3)
            coords4 = ( (-1, 0), (1, 0), (0, -1), (0, 1) )
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK3,), libtcod.Color(255, 165, 0), coords4)
            coords5 = ( (-2, 0), (-1, -1), (-1, 1), (0, 2), (0, -2), (2, 0), (1, -1), (1, 1) )
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK2,), libtcod.red, coords5, True, 3)

            coords = []
            coords.extend(coords1)
            coords.extend(coords2)
            coords.extend(coords3)
            coords.extend(coords4)
            coords.extend(coords5)
            blit_effects( effects_panel, (' ',), libtcod.white, coords)

            '''
             #
            # #
             @
            # #
             #
            '''
            coords1 = ( (-2, -1), (2, -1), (0, -2), (-2, 1), (2, 1), (0, 2) )
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK2,), libtcod.dark_red, coords1 )
            coords2 = ( (-1, 0), (1, 0), (0, -1), (0, 1) )
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK2,), libtcod.dark_grey, coords2, True, 5 )

            coords = []
            coords.extend(coords1)
            coords.extend(coords2)
            blit_effects( effects_panel, (' ',), libtcod.white, coords )

            '''
             # #
            # @ #
             # #
            '''
            coords = ( (-1, -1), (-1, 1), (-2, 0), (1, -1), (1, 1), (2, 0) )
            blit_effects( effects_panel, (libtcod.CHAR_BLOCK1,), libtcod.dark_grey, coords, True, 3 )
            blit_effects( effects_panel, (' ',), libtcod.white, coords )

            '''
            DONE!
            '''
            ghosts_hit = []
            for ghost in current_level.ghosts:
                hit = False
                if ghost.state in ('aggressive fleeing attacking'):
                    if abs(ghost.x - player.x) <= 3 and abs(ghost.y - player.y) <= 1:
                        hit = True
                    elif abs(ghost.x - player.x) <= 1 and abs(ghost.y - player.y) <= 3:
                        hit = True
                    elif abs(ghost.x - player.x) <= 2 and abs(ghost.y - player.y) <= 2:
                        hit = True

                    if hit == True:
                        ghosts_hit.append(ghost.name)

            while ghosts_hit != []:
                for name in ghosts_hit:
                    for ghost in current_level.ghosts:
                        if ghost.name == name:
                            damage = throw_dice('1d%d' % (16 - current_level.dlvl) * 4) + ((16 - current_level.dlvl) * 2)
                            message("The blast hits %s for %d damage!" % (ghost.name, damage))
                            ghosts_hit.remove(name)
                            ghost.take_damage(damage)
                            break
                    break

            current_level.effects.append(Effect(player.x, player.y, ' ', libtcod.white, 'charred floor 1'))
            lx, ly = range(LVL_WIDTH), range(LVL_HEIGHT)
            for coord in (-1, 1):
                if player.x + coord in lx and player.y + coord in ly:
                    if not current_level.level_map[player.x + coord][player.y].blocked:
                        current_level.effects.append(Effect(player.x + coord, player.y, ' ', libtcod.white, 'charred floor 2'))
                    if not current_level.level_map[player.x][player.y + coord].blocked:
                        current_level.effects.append(Effect(player.x, player.y + coord, ' ', libtcod.white, 'charred floor 2'))
                    for effect in current_level.effects:
                        if effect.name in ('strawberry jam stain', 'ghost corpse') or effect.name[:7] == 'etching':
                            if effect.x == player.x + coord and effect.y == player.y:
                                current_level.effects.remove(effect)
                            elif effect.x == player.x and effect.y == player.y + coord:
                                current_level.effects.remove(effect)
                            elif effect.x == player.x and effect.y == player.y:
                                current_level.effects.remove(effect)

            libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
            for obj in object_list(): obj.clear()
            libtcod.console_flush()

        elif item.name == 'strawberry jam':

            current_level.effects.append(Effect(player.x, player.y, ' ', item.color, 'strawberry jam stain'))

            while True:
                x = libtcod.random_get_int(0, 0, LVL_WIDTH-2)
                y = libtcod.random_get_int(0, 0, LVL_HEIGHT-2)
                if not current_level.level_map[x][y].blocked and (x, y) not in ((10,11), (11,11), (12,11)): break

            if play_sounds: sound_strawberry_jam.play()

            player.clear()
            player.set_pos(x, y)

            player.items_in_use.remove(item)
            get_pellets()

            libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
            for obj in object_list(): obj.clear()
            libtcod.console_flush()

            fov_recompute = True

        elif item.name == 'orange peel':

            player.defense_bonus = throw_dice('2d%d' % (16 - current_level.dlvl) * 3)

            if item.time == item.max_time:

                for corpse in current_level.corpses:
                    corpse.draw()
                for pellet in current_level.pellets:
                    pellet.draw()
                for litem in current_level.items:
                    litem.draw()
                for ghost in current_level.ghosts:
                    ghost.draw()
                player.draw()
                libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)

                if play_sounds: sound_orange_peel.play()

                blit_effects( effects_panel, ('-', '~', '-', '=', ' '), item.color, ((1, 0), (-1, 0)), True, 7 )

                for i in range(4):
                    libtcod.console_flush()

                blit_effects( effects_panel, ('(',), item.color, ((-1, 0),) )
                blit_effects( effects_panel, (')',), item.color, ((1, 0),), True, 6 )
                blit_effects( effects_panel, (' ',), item.color, ((-1, 0),) )
                blit_effects( effects_panel, (' ',), item.color, ((1, 0),), True, 6 )
                blit_effects( effects_panel, ('(',), item.color, ((-1, 0),) )
                blit_effects( effects_panel, (')',), item.color, ((1, 0),), True, 6 )

                libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
                for obj in object_list(): obj.clear()
                libtcod.console_flush()

            if item.time <= 0:
                message("The orange peel decays away.", item.color)
                player.defense_bonus = 0
                player.items_in_use.remove(item)

            item.tick()

        elif item.name == 'scroll of pear':

            if item.time == item.max_time:

                libtcod.console_clear(effects_panel)

                for corpse in current_level.corpses:
                    corpse.draw()
                for pellet in current_level.pellets:
                    pellet.draw()
                for litem in current_level.items:
                    litem.draw()
                for ghost in current_level.ghosts:
                    ghost.draw()
                player.draw()
                libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)
                libtcod.console_set_default_foreground(effects_panel, libtcod.chartreuse)

                sound_scroll_of_pear.play()

                blit_effects( effects_panel, ('/', '-', '\\', '|', '/', '-', '\\', '|'), libtcod.chartreuse, ((0, -1), (0, 1), (-1, 0), (1, 0)), True, 20 )

                for i in range(5):
                    libtcod.console_flush()

                libtcod.console_set_default_background(effects_panel, libtcod.darker_grey)
                libtcod.console_clear(effects_panel)

                for obj in object_list():
                    libtcod.console_set_default_foreground(effects_panel, obj.color)
                    libtcod.console_print(effects_panel, obj.x, obj.y, obj.char)

                blit_effects( effects_panel, ('*',), libtcod.chartreuse, ((0, -1), (0, 1), (-1, 0), (1, 0)), True, 5 )

                libtcod.console_clear(effects_panel)

                for obj in object_list():
                    libtcod.console_set_default_foreground(effects_panel, obj.color)
                    libtcod.console_print(effects_panel, obj.x, obj.y, obj.char)

                libtcod.console_set_default_foreground(effects_panel, libtcod.chartreuse)

                blit_effects( effects_panel, ('-',), libtcod.chartreuse, ((0, -2), (0, 2), (-2, 0), (2, 0)), True, 5 )

                libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
                for obj in object_list(): obj.clear()
                libtcod.console_flush()

            if item.time <= 0:
                message("You feel the effects of the pear spell fade.", item.color)
                player.items_in_use.remove(item)

            item.tick()

        elif item.name == 'pretzel whip':

            player.attack_bonus = throw_dice('2d%d' % (16 - current_level.dlvl) * 2)

            if item.time <= 0:
                message("The pretzel whip crumbles away.", item.color)
                player.attack_bonus = 0
                player.items_in_use.remove(item)

            item.tick()

            for obj in object_list(): obj.clear()

        elif item.name == 'banana nectar':

            player.level_up()

            player.items_in_use.remove(item)

            for corpse in current_level.corpses:
                corpse.draw()
            for pellet in current_level.pellets:
                pellet.draw()
            for litem in current_level.items:
                litem.draw()
            for ghost in current_level.ghosts:
                ghost.draw()
            player.draw()
            libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)
            libtcod.console_set_default_foreground(effects_panel, libtcod.yellow)

            blit_effects( effects_panel, ('.', '|', ':'), libtcod.yellow, ((0, -1),), True, 4 )

            libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
            for obj in object_list(): obj.clear()
            libtcod.console_flush()

        else:
            pass

    libtcod.console_delete(effects_panel)

def get_hex(n):

    h = '%x' % n

    if len(h) == 1:
        return '0' + h
    else:
        return h

def get_random_line(key = None):

    line = ''

    for i in range(9):
        line += get_hex(libtcod.random_get_int(0, 0, 255))
    for i in range(2):
        tmp = '%x' % libtcod.random_get_int(0, 0, 4095)
        while len(tmp) < 3: tmp = '0' + tmp
        line += tmp
    tmp = libtcod.random_get_int(0, 0, 2)
    if tmp == 0: line += 'o'
    elif tmp == 1: line += 'w'
    else: line += 't'
    tmp = libtcod.random_get_int(0, 0, 5)
    if tmp == 0: line += 'Re'
    elif tmp == 1: line += '44'
    elif tmp == 2: line += '5S'
    elif tmp == 3: line += 'ip'
    elif tmp == 4: line += 'zP'
    else: line += 'EN'
    tmp = oct(libtcod.random_get_int(0, 0, 500000))
    while len(tmp) < 8:
        tmp = '0' + tmp
    line += tmp
    line += get_hex(libtcod.random_get_int(0, 0, 64))

    if key != None:
        tmp = list(line)
        tmp[4] = '%x' % key
        line = ''.join(tmp)

    return line

### SCREENS ###

def royal_paw_splash():

    pygame.mixer.music.play()

    lerp_index = 0.0
    while lerp_index <= 1:

        libtcod.console_set_default_foreground(splash_panel, libtcod.color_lerp(libtcod.black, libtcod.white, lerp_index))
        libtcod.console_set_alignment(splash_panel, libtcod.CENTER)
        libtcod.console_print(splash_panel, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 'ROYAL PAW PRESENTS...')
        libtcod.console_set_alignment(splash_panel, libtcod.LEFT)

        libtcod.console_blit(splash_panel, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
        libtcod.console_flush()

        lerp_index += 0.1

        key = libtcod.console_check_for_keypress()
        if key.vk == libtcod.KEY_ENTER: return

    for i in range(FPS * 2):
        libtcod.console_flush()
        key = libtcod.console_check_for_keypress()
        if key.vk == libtcod.KEY_ENTER: return

    lerp_index = 1
    while lerp_index >= 0:

        libtcod.console_set_default_foreground(splash_panel, libtcod.color_lerp(libtcod.black, libtcod.white, lerp_index))
        libtcod.console_set_alignment(splash_panel, libtcod.CENTER)
        libtcod.console_print(splash_panel, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 'ROYAL PAW PRESENTS...')
        libtcod.console_set_alignment(splash_panel, libtcod.LEFT)

        libtcod.console_blit(splash_panel, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
        libtcod.console_flush()

        lerp_index -= 0.1

        key = libtcod.console_check_for_keypress()
        if key.vk == libtcod.KEY_ENTER: return

def pigs_splash():

    lerp_index = 0.0
    while lerp_index <= 1:

        y = 0
        for line in range(len(pigs_logo)):
            for char in range(len(pigs_logo[0])):

                if line < 4:
                    libtcod.console_set_default_foreground(splash_panel, libtcod.white)
                    libtcod.console_set_default_background(splash_panel, libtcod.black)
                else:
                    libtcod.console_set_default_background(splash_panel, libtcod.color_lerp(libtcod.black, libtcod.white, lerp_index))

                if line >= 4 and line <= 28 and char >= 0 and char <= 33 and pigs_logo[line][char] not in 'M@':
                    libtcod.console_set_default_foreground(splash_panel, libtcod.color_lerp(libtcod.black, libtcod.pink, lerp_index))
                elif pigs_logo[line][char] == '@':
                    libtcod.console_set_default_foreground(splash_panel, libtcod.color_lerp(libtcod.black, libtcod.sky, lerp_index))
                elif pigs_logo[line][char] == 'M':
                    libtcod.console_set_default_foreground(splash_panel, libtcod.black)
                elif line > 28:
                    libtcod.console_set_default_foreground(splash_panel, libtcod.black)

                libtcod.console_print_ex(splash_panel, char, y, libtcod.BKGND_SET, libtcod.LEFT, pigs_logo[line][char])
            y += 1

        libtcod.console_blit(splash_panel, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
        libtcod.console_flush()

        lerp_index += 0.1

        key = libtcod.console_check_for_keypress()
        if key.vk == libtcod.KEY_ENTER: return

    for i in range(FPS * 4):
        libtcod.console_flush()
        key = libtcod.console_check_for_keypress()
        if key.vk == libtcod.KEY_ENTER: return

    lerp_index = 1.0
    while lerp_index >= 0:

        y = 0
        for line in range(len(pigs_logo)):
            for char in range(len(pigs_logo[0])):

                if line < 4:
                    libtcod.console_set_default_foreground(splash_panel, libtcod.color_lerp(libtcod.black, libtcod.white, lerp_index))
                    libtcod.console_set_default_background(splash_panel, libtcod.black)
                else:
                    libtcod.console_set_default_background(splash_panel, libtcod.color_lerp(libtcod.black, libtcod.white, lerp_index))

                if line >= 4 and line <= 28 and char >= 0 and char <= 33 and pigs_logo[line][char] not in '@M':
                    libtcod.console_set_default_foreground(splash_panel, libtcod.color_lerp(libtcod.black, libtcod.pink, lerp_index))
                elif pigs_logo[line][char] == '@':
                    libtcod.console_set_default_foreground(splash_panel, libtcod.color_lerp(libtcod.black, libtcod.sky, lerp_index))
                elif pigs_logo[line][char] == 'M':
                    libtcod.console_set_default_foreground(splash_panel, libtcod.black)
                elif line > 28:
                    libtcod.console_set_default_foreground(splash_panel, libtcod.black)

                libtcod.console_print_ex(splash_panel, char, y, libtcod.BKGND_SET, libtcod.LEFT, pigs_logo[line][char])
            y += 1

        libtcod.console_blit(splash_panel, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
        libtcod.console_flush()

        lerp_index -= 0.1

        key = libtcod.console_check_for_keypress()
        if key.vk == libtcod.KEY_ENTER: return

def title_screen():

    global game_state
    global global_debug

    libtcod.console_set_default_background(splash_panel, libtcod.black)
    libtcod.console_clear(splash_panel)
    title_screen_state = 'creating'

    if exists('sdata'):
        with open('sdata', 'r') as f:
            current_high_score = f.readline()
            current_high_score = current_high_score[12:]
    else:
        with open('sdata', 'w') as f:
            f.write('High score: 0\n\n\n\n')
        current_high_score = '0'

    with open('sdata', 'r') as f:
        for i in range(4): f.readline()
        tmp = f.readline()
        if tmp != '':
            save_slot = True
            data = []
            f.seek(0)
            for i in range(4): f.readline()
            for i in range(30): data.append(f.readline()[:-1])
            key_1 = data[2][2:13]
            key_2 = data[2][14:25]
            key_3 = data[3][17:28]
            key = {}
            for i in range(10):
                key[i] = str(key_1[i] + key_2[i] + key_3[i])
            plvl = list(data[4][5:7])
            dlvl = list(data[4][8:10])
            player_data = {'plvl':plvl, 'dlvl':dlvl}
            for item in player_data:
                for i in range(len(player_data[item])):
                    for number in key:
                        if player_data[item][i] in key[number]:
                            player_data[item][i] = str(number)
                            break
                print player_data[item]
                player_data[item] = int(''.join(player_data[item]))
        else: save_slot = False

    while True:

        if title_screen_state == 'creating':
            player_icon = Player(11, 26, '@', libtcod.yellow, 'icon', blocked = True, level = 1)
            player_icon.state = 'normal'
            color = libtcod.Color(0, 0, 1)
            hue = 50
            color_direction = 'up'
            title_screen_state = 'created'
            reset_button = 0

        if color_direction == 'up': hue += 5
        else: hue -= 5
        if hue < 10:
            color_direction = 'up'
            reset_button = 0
        elif hue > 350:
            color_direction = 'down'
            reset_button = 0
        libtcod.color_set_hsv(color, hue, 0.6, 0.8)
        libtcod.console_set_default_foreground(splash_panel, color)

        for y in range(20):
            for x in range(SCREEN_WIDTH):
                libtcod.console_print(splash_panel, x, y, netpack_logo[y][x])
        libtcod.console_set_default_foreground(splash_panel, libtcod.white)
        for y in range(21, SCREEN_HEIGHT):
            for x in range(SCREEN_WIDTH):
                libtcod.console_print(splash_panel, x, y, netpack_logo[y][x])

        libtcod.console_set_default_foreground(splash_panel, color)
        for x in range(LVL_WIDTH):
            libtcod.console_print(splash_panel, x, player_icon.y, netpack_logo[player_icon.y][x])
        libtcod.console_set_default_foreground(splash_panel, libtcod.yellow)
        libtcod.console_print(splash_panel, player_icon.x, player_icon.y, player_icon.char)

        libtcod.console_set_default_foreground(splash_panel, libtcod.white)
        libtcod.console_print_ex(splash_panel, 0, 2, libtcod.BKGND_NONE, libtcod.LEFT, "HIGH SCORE: %s" % current_high_score)
        libtcod.console_print_ex(splash_panel, 10, 22, libtcod.BKGND_NONE, libtcod.LEFT, "(c) 2011 ROYAL PAW")
        libtcod.console_set_default_foreground(splash_panel, libtcod.grey)
        libtcod.console_print_ex(splash_panel, 21, 2, libtcod.BKGND_NONE, libtcod.LEFT, "('RR' to reset)")
        libtcod.console_set_default_foreground(splash_panel, libtcod.white)

        if not save_slot:
            libtcod.console_set_default_foreground(splash_panel, libtcod.darker_grey)
            libtcod.console_print_ex(splash_panel, 15, 34, libtcod.BKGND_NONE, libtcod.LEFT, "[EMPTY]")
        else:
            libtcod.console_print_ex(splash_panel, 15, 34, libtcod.BKGND_NONE, libtcod.LEFT, "[DLVL: %s / PLVL: %s]" % (player_data['dlvl'] - 1, player_data['plvl']))

        libtcod.console_blit(splash_panel, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
        libtcod.console_flush()

        title_key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)

        if title_key.vk == libtcod.KEY_F4:
            libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
            libtcod.mouse_show_cursor(not libtcod.mouse_is_cursor_visible())

        elif title_key.c == ord('R'):
            reset_button += 1

        if reset_button == 2:
            with open('sdata', 'r') as f:
                for i in range(4): f.readline()
                data = []
                for i in range(30): data.append(f.readline())
            with open('sdata', 'w') as f:
                f.write('High score: 0\n\n\n\n')
                for line in data: f.write(line)
            current_high_score = '0'
            reset_button = 0

        elif title_key.vk in (libtcod.KEY_ENTER, libtcod.KEY_KPENTER):
            sound_select.play()
            pygame.mixer.music.stop()
            if player_icon.state != 'load game':
                with open('sdata', 'r') as f:
                    tmp = f.readline()
                    tmp += f.readline()
                    tmp += f.readline()
                with open('sdata', 'w') as f:
                    f.write(tmp)
                    f.write('\n')
            return player_icon.state

        elif title_key.vk == libtcod.KEY_ESCAPE:
            game_state = 'quit'
            exit(0)
            return

        """
        # DEBUG
        if title_key.c == ord('w'):
            pygame.mixer.music.stop()
            global_debug = True
            return 'normal'
        """

        # movement
        if (title_key.vk in (libtcod.KEY_UP, libtcod.KEY_KP8) or title_key.c == ord('k')) and player_icon.state != 'normal':
            if player_icon.state == 'load game': player_icon.state = 'god'
            elif player_icon.state == 'god': player_icon.state = 'idfa'
            elif player_icon.state == 'idfa': player_icon.state = 'normal'
            sound_cursor.play()
            player_icon.y -= 2
        elif (title_key.vk in (libtcod.KEY_DOWN, libtcod.KEY_KP2) or title_key.c == ord('j')):
            if (save_slot and player_icon.state != 'load game') or (not save_slot and player_icon.state != 'god'):
                if player_icon.state == 'normal': player_icon.state = 'idfa'
                elif player_icon.state == 'idfa': player_icon.state = 'god'
                elif player_icon.state == 'god': player_icon.state = 'load game'
                sound_cursor.play()
                player_icon.y += 2

def kill_screen():

    for y in range(LVL_HEIGHT):
        for x in range((LVL_WIDTH / 2) + 1, LVL_WIDTH):

            color_fore = libtcod.Color(libtcod.random_get_int(0, 0, 255), libtcod.random_get_int(0, 0, 255), libtcod.random_get_int(0, 0, 255))
            libtcod.console_set_default_foreground(con, color_fore)

            color_back = libtcod.Color(libtcod.random_get_int(0, 0, 255), libtcod.random_get_int(0, 0, 255), libtcod.random_get_int(0, 0, 255))
            libtcod.console_set_default_background(con, color_back)

            if libtcod.random_get_int(0, 1, 100) > 75:
                libtcod.console_put_char_ex(con, x, y, libtcod.random_get_int(0, 0, 255), color_fore, color_back)
            else:
                libtcod.console_put_char(con, x, y, libtcod.random_get_int(0, 0, 255), libtcod.BKGND_NONE)

            libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)

    libtcod.console_flush()

    libtcod.console_set_default_background(con, libtcod.black)

    clear_all()

def open_inventory():

    global game_state

    inv_panel = libtcod.console_new(LVL_WIDTH, LVL_HEIGHT)

    libtcod.console_set_default_foreground(inv_panel, libtcod.white)
    libtcod.console_print_frame(inv_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, True, libtcod.BKGND_NONE, 0)
    libtcod.console_set_alignment(splash_panel, libtcod.CENTER)
    libtcod.console_print(inv_panel, LVL_WIDTH / 2 - 4, 0, "INVENTORY")
    libtcod.console_set_alignment(splash_panel, libtcod.LEFT)

    simple_item_list = []
    for item_simple in player.inventory:
        simple_item_list.append(item_simple.name)

    option_list = []

    while True:

        # print item list
        printed_list = []

        i = 0
        libtcod.console_set_default_foreground(inv_panel, libtcod.desaturated_violet)
        libtcod.console_print(inv_panel, 2, i+2, "x - Haunted Mace of\n    the Four Winds")
        for item in player.inventory:

            if item.name not in printed_list:
                libtcod.console_set_default_foreground(inv_panel, item.color)
                libtcod.console_print(inv_panel, 2, i+5, "%s - %s" % (alphabet[len(printed_list)], item.name.capitalize()))
                i += 1
                libtcod.console_set_default_foreground(inv_panel, libtcod.light_grey)
                libtcod.console_print(inv_panel, 6, i+5, "x %d" % (simple_item_list.count(item.name)))
                i += 1
                option_list.append((item, alphabet[len(printed_list)]))
                printed_list.append(item.name)

        libtcod.console_blit(inv_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        libtcod.console_flush()

        key = libtcod.console_wait_for_keypress(True)

        if key.vk == libtcod.KEY_ESCAPE or key.c in (ord('i'), ord('I')):
            break

        if key.c == ord('x'):
            if not current_level.level_map[11][8].blocked and (player.x, player.y) == (11, 9):
                good_ending_animation()
                game_state = 'initializing level'
                break
            else:
                message("You lazily swing the Mace of the Four Winds back and forth.", libtcod.desaturated_violet)
                libtcod.console_delete(inv_panel)
                return True

        for item in option_list:

            if key.c in (ord(item[1]), ord(item[1].upper())):
                message(item[0].use_message, item[0].color)
                render_all(current_level)
                libtcod.console_flush()

                for pitem in player.inventory:
                    if pitem.name == item[0].name:
                        player.items_in_use.append(pitem)
                        player.inventory.remove(pitem)
                        libtcod.console_delete(inv_panel)
                        return True

    libtcod.console_delete(inv_panel)

    return False

def bad_ending_animation():

    effects_panel = libtcod.console_new(LVL_WIDTH, LVL_HEIGHT)

    clear_msgs()
    libtcod.console_print_frame(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, False, libtcod.BKGND_OVERLAY, 0)
    libtcod.console_blit(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, 0, 0, MSG_Y)
    libtcod.console_flush()

    for effect in current_level.effects:
        effect.draw()
    for corpse in current_level.corpses:
        corpse.draw()
    for pellet in current_level.pellets:
        pellet.draw()
    for litem in current_level.items:
        litem.draw()
    for ghost in current_level.ghosts:
        ghost.draw()
    player.draw()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)

    for times in range(4):
        libtcod.console_set_default_background(effects_panel, libtcod.lighter_grey)
        for y in range(LVL_HEIGHT):
            for x in range(LVL_WIDTH):
                libtcod.console_print_ex(effects_panel, x, y, libtcod.BKGND_SET, libtcod.LEFT, ' ')
        libtcod.console_blit(effects_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        for i in range(FPS / 4): libtcod.console_flush()
        libtcod.console_set_default_background(effects_panel, libtcod.black)
        for y in range(LVL_HEIGHT):
            for x in range(LVL_WIDTH):
                libtcod.console_print_ex(effects_panel, x, y, libtcod.BKGND_SET, libtcod.LEFT, ' ')
        libtcod.console_blit(effects_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        for i in range(FPS / 4): libtcod.console_flush()

    libtcod.console_delete(effects_panel)

def bad_ending():

    global game_mode

    clear_msgs()
    libtcod.console_print_frame(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, False, libtcod.BKGND_OVERLAY, 0)
    libtcod.console_blit(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, 0, 0, MSG_Y)

    if play_sounds: pygame.mixer.music.play()

    FPS = 60
    libtcod.sys_set_fps(FPS)

    libtcod.console_clear(con)

    # put the frame
    libtcod.console_set_default_foreground(con, libtcod.white)
    libtcod.console_set_default_background(con, libtcod.black)
    libtcod.console_print_frame(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, False, libtcod.BKGND_NONE, 0)

    # write the ending
    end_message = "You find a hidden tunnel and crawl your way to the surface. Although the air is fresh, the curse remains, and you can't help but feel a longing to return and finish your original quest...."

    new_message_lines = textwrap.wrap(end_message, LVL_WIDTH - 2)

    iy = 0
    for line in new_message_lines:
        ix = 0
        for letter in line:
            libtcod.console_print(con, ix + 1, iy + 2, letter)
            ix += 1
            if play_sounds and not pygame.mixer.get_busy():
                index = libtcod.random_get_int(0, 0, len(sound_collect_pellet) - 1)
                sound_collect_pellet[index].play()
            libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
            for i in range(3): libtcod.console_flush()
            key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
            if key.vk == libtcod.KEY_ENTER: pass
        iy += 1

    for i in range(FPS / 2): libtcod.console_flush()
    libtcod.console_print(con, 1, 14, "GHOSTS VANQUISHED:")
    if play_sounds and not pygame.mixer.get_busy():
        index = libtcod.random_get_int(0, 0, len(sound_step) - 1)
        sound_step[index].play()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_flush()
    for i in range(FPS / 2): libtcod.console_flush()

    i = 0
    while i <= player.ghosts_killed:
        libtcod.console_print(con, 1, 14, "GHOSTS VANQUISHED: %d" % i)
        i += 1
        if play_sounds and not pygame.mixer.get_busy():
            index = libtcod.random_get_int(0, 0, len(sound_step) - 1)
            sound_step[index].play()
        libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        libtcod.console_flush()
        key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
        if key.vk == libtcod.KEY_ENTER: pass

    for i in range(FPS / 2): libtcod.console_flush()
    libtcod.console_print(con, 10, 15, "x 500 points")
    if play_sounds and not pygame.mixer.get_busy():
        index = libtcod.random_get_int(0, 0, len(sound_step) - 1)
        sound_step[index].play()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_flush()

    for i in range(FPS / 2): libtcod.console_flush()
    libtcod.console_print(con, 1, 17, "SCORE:")
    if play_sounds and not pygame.mixer.get_busy():
        index = libtcod.random_get_int(0, 0, len(sound_step) - 1)
        sound_step[index].play()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_flush()

    bonus = player.ghosts_killed * 500

    for i in range(FPS / 2): libtcod.console_flush()
    libtcod.console_print(con, 1, 17, "SCORE: %d + %d" % (player.score, bonus))
    if play_sounds and not pygame.mixer.get_busy():
        index = libtcod.random_get_int(0, 0, len(sound_step) - 1)
        sound_step[index].play()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_flush()
    for i in range(FPS / 2): libtcod.console_flush()

    libtcod.console_print(con, 1, 17, "SCORE:               ")

    total_score = player.score

    libtcod.console_set_default_background(gui_panel, libtcod.black)
    libtcod.console_clear(gui_panel)

    render_bar((SCREEN_WIDTH - LVL_WIDTH) / 2, 1, BAR_WIDTH, 'HP', player.hp, player.max_hp, libtcod.light_blue, libtcod.dark_red)
    render_bar((SCREEN_WIDTH - LVL_WIDTH) / 2, 2, BAR_WIDTH, 'XP', player.exp, player.exp_next_level, libtcod.light_violet, libtcod.dark_violet)

    libtcod.console_print(gui_panel, 7, 3, BLANK_LINE)
    libtcod.console_print(gui_panel, 7, 4, BLANK_LINE)
    libtcod.console_print(gui_panel, 7, 4, "SCORE: %d" % player.score)
    libtcod.console_print(gui_panel, 7, 5, "LIVES: %d" % player.lives)
    libtcod.console_set_alignment(gui_panel, libtcod.RIGHT)
    libtcod.console_print(gui_panel, LVL_WIDTH + 6, 4, "PLVL: %d" % player.level)
    libtcod.console_print(gui_panel, LVL_WIDTH + 6, 5, "DLVL: %d" % current_level.dlvl)
    libtcod.console_set_alignment(gui_panel, libtcod.LEFT)

    libtcod.console_set_default_foreground(gui_panel, libtcod.white)
    libtcod.console_print_frame(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, False, libtcod.BKGND_NONE, 0)

    libtcod.console_blit(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

    while bonus != 0:
        libtcod.console_print(con, 1, 17, "SCORE:               ")
        libtcod.console_print(con, 1, 17, "SCORE: %d + %d" % (total_score, bonus))
        total_score += 10
        bonus -= 10
        player.score = total_score
        if play_sounds and not pygame.mixer.get_busy():
            index = libtcod.random_get_int(0, 0, len(sound_step) - 1)
            sound_step[index].play()
        libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        if total_score % 100 == 0:
            libtcod.console_print(gui_panel, 7, 4, "SCORE: %d" % player.score)
            libtcod.console_print_frame(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, False, libtcod.BKGND_NONE, 0)
            libtcod.console_blit(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
            libtcod.console_flush()
            key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
            if key.vk == libtcod.KEY_ENTER: pass

    libtcod.console_print(con, 1, 17, "SCORE:              ")
    libtcod.console_print(con, 1, 17, "SCORE: %d" % total_score)
    libtcod.console_print(gui_panel, 7, 4, "SCORE: %d" % player.score)
    libtcod.console_print_frame(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, False, libtcod.BKGND_NONE, 0)

    libtcod.console_blit(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)

    if game_mode == 'normal':
        with open('sdata', 'r') as f:
            current_high_score = f.readline()
            if current_high_score[-2] == '!':
                current_high_score = current_high_score[:-2]
            current_high_score = int(current_high_score[12:])
        if player.score > current_high_score:
            with open('sdata', 'w') as f:
                f.write('High score: %d' % player.score)
                f.write('\n')
                f.write('Escaped the maze without solving the curse.')
                f.write('\n')
                f.write('Vanquished %d ghosts.' % player.ghosts_killed)
                f.write('\n')

    with open('sdata', 'r') as f:
        tmp = f.readline()
        tmp += f.readline()
        tmp += f.readline()
    with open('sdata', 'w') as f:
        f.write(tmp)
        f.write('\n')

    # render the message log
    message('x', libtcod.black)
    message('x', libtcod.black)
    message(">> Press ENTER to restart or ESC to quit....")
    libtcod.console_set_default_foreground(msg_panel, libtcod.white)
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(msg_panel, color)
        libtcod.console_print(msg_panel, MSG_X + 1, y, BLANK_LINE)
        libtcod.console_print(msg_panel, MSG_X + 1, y, line)
        y += 1
    libtcod.console_set_default_foreground(msg_panel, libtcod.white)
    libtcod.console_print_frame(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, False, libtcod.BKGND_OVERLAY, 0)
    libtcod.console_blit(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, 0, 0, MSG_Y)

    libtcod.console_flush()

    FPS = 20
    libtcod.sys_set_fps(FPS)

    player.ghosts_killed = 0

    while True:

        key = libtcod.console_wait_for_keypress(True)
        if key.vk in (libtcod.KEY_ENTER, libtcod.KEY_KPENTER):
            game_mode = title_screen()
            hello_world()
            libtcod.console_clear(0)
            fov_recompute = True
            return
        if key.vk == libtcod.KEY_ESCAPE:
            for panel in (con, gui_panel, msg_panel, splash_panel, inv_panel):
                libtcod.console_delete(panel)
            libtcod.console_clear(0)
            exit(0)
            return

def good_ending_animation():

    effects_panel = libtcod.console_new(LVL_WIDTH, LVL_HEIGHT)
    render_all(current_level)

    clear_msgs()
    libtcod.console_print_frame(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, False, libtcod.BKGND_OVERLAY, 0)
    libtcod.console_blit(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, 0, 0, MSG_Y)
    libtcod.console_flush()

    for num in range(5):

        matrix = [ [0 for y in range(3)] for x in range(3) ]

        for y in range(len(matrix)):
            for x in range(len(matrix[0])):
                matrix[y][x] = libtcod.random_get_int(0, 0, 1)

        for effect in current_level.effects:
            effect.draw()
        for corpse in current_level.corpses:
            corpse.draw()
        for pellet in current_level.pellets:
            pellet.draw()
        for litem in current_level.items:
            litem.draw()
        for ghost in current_level.ghosts:
            ghost.draw()
        player.draw()
        libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)
        libtcod.console_set_default_foreground(effects_panel, libtcod.white)

        #if play_sounds: sound_appletini.play()

        if play_sounds:
            index = libtcod.random_get_int(0, 0, len(sound_break) - 1)
            sound_break[index].play()
        for frame in (':', '`', "-", "."):
            for y in range(len(matrix)):
                for x in range(len(matrix[0])):
                    if matrix[y][x] == 1 and not (y == 1 and x == 1) and (player.x + x - 1 in range(LVL_WIDTH) and player.y + y - 1 in range(LVL_HEIGHT)):
                        libtcod.console_print(effects_panel, player.x + x - 1, player.y + y - 1, frame)
                        libtcod.console_blit(effects_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
                        key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
                        if key.vk == libtcod.KEY_ENTER: pass

            for i in range(FPS / 5):
                libtcod.console_flush()
                key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
                if key.vk == libtcod.KEY_ENTER: pass

    for effect in current_level.effects:
        effect.draw()
    for corpse in current_level.corpses:
        corpse.draw()
    for pellet in current_level.pellets:
        pellet.draw()
    for litem in current_level.items:
        litem.draw()
    for ghost in current_level.ghosts:
        ghost.draw()
    player.draw()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)

    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    for second in range(FPS): libtcod.console_flush()

    height = player.y - 1
    if play_sounds: sound_light.play()
    while height >= 0:
        libtcod.console_set_default_background(effects_panel, libtcod.white)
        libtcod.console_print_ex(effects_panel, player.x, height, libtcod.BKGND_SET, libtcod.LEFT, ' ')
        height -= 1
        libtcod.console_blit(effects_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        libtcod.console_flush()
        key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
        if key.vk == libtcod.KEY_ENTER: pass

    current_level.dark = False
    render_all(current_level)
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)
    libtcod.console_flush()

    if play_sounds:
        sound_souls.play()
    for i in range(FPS * 5):
        for y in range(player.y - 1, -1, -1):
            color_fore = libtcod.Color(libtcod.random_get_int(0, 0, 255), libtcod.random_get_int(0, 0, 255), libtcod.random_get_int(0, 0, 255))
            libtcod.console_set_default_foreground(effects_panel, color_fore)
            if libtcod.random_get_int(0, 1, 100) > 15:
                libtcod.console_put_char(effects_panel, player.x, y, libtcod.random_get_int(0, 0, 255))
            if libtcod.random_get_int(0, 1, 20) == 1:
                libtcod.console_put_char(effects_panel, player.x + 1, y, libtcod.random_get_int(0, 0, 255))
            if libtcod.random_get_int(0, 1, 20) == 1:
                libtcod.console_put_char(effects_panel, player.x - 1, y, libtcod.random_get_int(0, 0, 255))
            if libtcod.random_get_int(0, 1, 40) == 1:
                libtcod.console_put_char(effects_panel, player.x + 2, y, libtcod.random_get_int(0, 0, 255))
            if libtcod.random_get_int(0, 1, 40) == 1:
                libtcod.console_put_char(effects_panel, player.x - 2, y, libtcod.random_get_int(0, 0, 255))
            libtcod.console_blit(effects_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        libtcod.console_flush()
        libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)
        key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
        if key.vk == libtcod.KEY_ENTER: pass
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, effects_panel, 0, 0)
    libtcod.console_flush()

    for second in range(FPS): libtcod.console_flush()

    for y in range(LVL_HEIGHT):
        color_back = libtcod.Color(libtcod.random_get_int(0, 0, 255), libtcod.random_get_int(0, 0, 255), libtcod.random_get_int(0, 0, 255))
        libtcod.console_set_default_background(effects_panel, color_back)
        for x in range(LVL_WIDTH):
            libtcod.console_print_ex(effects_panel, x, y, libtcod.BKGND_SET, libtcod.LEFT, ' ')
        libtcod.console_blit(effects_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        for i in range(2): libtcod.console_flush()
        if play_sounds:
            index = libtcod.random_get_int(0, 0, len(sound_crash) - 1)
            sound_crash[index].play()
    for i in range(FPS): libtcod.console_flush()
    libtcod.console_set_default_background(effects_panel, libtcod.lightest_grey)
    if play_sounds:
        sound_close_up.play()
    for y in range(LVL_HEIGHT, -1, -1):
        for x in range(LVL_WIDTH):
            libtcod.console_print_ex(effects_panel, x, y, libtcod.BKGND_SET, libtcod.LEFT, ' ')
        libtcod.console_blit(effects_panel, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        libtcod.console_flush()
        key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
        if key.vk == libtcod.KEY_ENTER: pass

    libtcod.console_delete(effects_panel)

def good_ending():

    global game_mode

    pygame.mixer.music.load('snd/good_end.ogg')
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play()

    clear_msgs()
    libtcod.console_print_frame(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, False, libtcod.BKGND_OVERLAY, 0)
    libtcod.console_blit(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, 0, 0, MSG_Y)

    #if play_sounds: pygame.mixer.music.play()

    FPS = 60
    libtcod.sys_set_fps(FPS)

    libtcod.console_set_default_background(con, libtcod.lightest_grey)
    libtcod.console_clear(con)

    # put the frame
    libtcod.console_set_default_foreground(con, libtcod.black)
    libtcod.console_set_default_background(con, libtcod.lightest_grey)
    libtcod.console_print_frame(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, False, libtcod.BKGND_SET, 0)

    # write the ending
    end_message = "You raise the Mace of the Four Winds high and bring it down upon the altar, smashing it into 100 pieces and releasing the souls therein. Layers of technicolor light wash over you and carry you to the surface. You're free!"

    libtcod.console_set_default_foreground(con, libtcod.black)

    new_message_lines = textwrap.wrap(end_message, LVL_WIDTH - 2)

    iy = 0
    for line in new_message_lines:
        ix = 0
        for letter in line:
            libtcod.console_print(con, ix + 1, iy + 2, letter)
            ix += 1
            if play_sounds and not pygame.mixer.get_busy():
                index = libtcod.random_get_int(0, 0, len(sound_a_major) - 1)
                sound_a_major[index].play()
            libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
            for i in range(3): libtcod.console_flush()
            key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
            if key.vk == libtcod.KEY_ENTER: pass
        iy += 1

    for i in range(FPS / 2): libtcod.console_flush()
    libtcod.console_print(con, 1, 14, "GHOSTS VANQUISHED:")
    if play_sounds and not pygame.mixer.get_busy():
        index = libtcod.random_get_int(0, 2, len(sound_a_major) - 2)
        sound_a_major[index].play()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_flush()
    for i in range(FPS / 2): libtcod.console_flush()

    i = 0
    while i <= player.ghosts_killed:
        libtcod.console_print(con, 1, 14, "GHOSTS VANQUISHED: %d" % i)
        i += 1
        if play_sounds and not pygame.mixer.get_busy():
            index = libtcod.random_get_int(0, 2, len(sound_a_major) - 2)
            sound_a_major[index].play()
        libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        libtcod.console_flush()
        key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
        if key.vk == libtcod.KEY_ENTER: pass

    for i in range(FPS / 2): libtcod.console_flush()
    libtcod.console_print(con, 10, 15, "x 500 points")
    if play_sounds and not pygame.mixer.get_busy():
        index = libtcod.random_get_int(0, 2, len(sound_a_major) - 2)
        sound_a_major[index].play()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_flush()

    for i in range(FPS / 2): libtcod.console_flush()
    libtcod.console_print(con, 1, 17, "SCORE:")
    if play_sounds and not pygame.mixer.get_busy():
        index = libtcod.random_get_int(0, 2, len(sound_a_major) - 2)
        sound_a_major[index].play()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_flush()

    bonus = player.ghosts_killed * 500

    for i in range(FPS / 2): libtcod.console_flush()
    libtcod.console_print(con, 1, 17, "SCORE: %d + %d" % (player.score, bonus))
    if play_sounds and not pygame.mixer.get_busy():
        index = libtcod.random_get_int(0, 2, len(sound_a_major) - 2)
        sound_a_major[index].play()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_flush()
    for i in range(FPS / 2): libtcod.console_flush()

    libtcod.console_print(con, 1, 17, "SCORE:               ")

    total_score = player.score

    libtcod.console_set_default_background(gui_panel, libtcod.black)
    libtcod.console_clear(gui_panel)

    render_bar((SCREEN_WIDTH - LVL_WIDTH) / 2, 1, BAR_WIDTH, 'HP', player.hp, player.max_hp, libtcod.light_blue, libtcod.dark_red)
    render_bar((SCREEN_WIDTH - LVL_WIDTH) / 2, 2, BAR_WIDTH, 'XP', player.exp, player.exp_next_level, libtcod.light_violet, libtcod.dark_violet)

    libtcod.console_print(gui_panel, 7, 3, BLANK_LINE)
    libtcod.console_print(gui_panel, 7, 4, BLANK_LINE)
    libtcod.console_print(gui_panel, 7, 4, "SCORE: %d" % player.score)
    libtcod.console_print(gui_panel, 7, 5, "LIVES: %d" % player.lives)
    libtcod.console_set_alignment(gui_panel, libtcod.RIGHT)
    libtcod.console_print(gui_panel, LVL_WIDTH + 6, 4, "PLVL: %d" % player.level)
    libtcod.console_print(gui_panel, LVL_WIDTH + 6, 5, "DLVL: %d" % current_level.dlvl)
    libtcod.console_set_alignment(gui_panel, libtcod.LEFT)

    libtcod.console_set_default_foreground(gui_panel, libtcod.white)
    libtcod.console_print_frame(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, False, libtcod.BKGND_NONE, 0)

    libtcod.console_blit(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

    while bonus != 0:
        libtcod.console_print(con, 1, 17, "SCORE:               ")
        libtcod.console_print(con, 1, 17, "SCORE: %d + %d" % (total_score, bonus))
        total_score += 10
        bonus -= 10
        player.score = total_score
        if play_sounds and not pygame.mixer.get_busy():
            index = libtcod.random_get_int(0, 2, len(sound_a_major) - 2)
            sound_a_major[index].play()
        libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        if total_score % 100 == 0:
            libtcod.console_print(gui_panel, 7, 4, "SCORE: %d" % player.score)
            libtcod.console_print_frame(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, False, libtcod.BKGND_NONE, 0)
            libtcod.console_blit(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
            libtcod.console_flush()
            key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
            if key.vk == libtcod.KEY_ENTER: pass

    libtcod.console_print(con, 1, 17, "SCORE:              ")
    libtcod.console_print(con, 1, 17, "SCORE: %d" % total_score)
    libtcod.console_print(gui_panel, 7, 4, "SCORE: %d" % player.score)
    libtcod.console_print_frame(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, False, libtcod.BKGND_NONE, 0)
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)

    bonus = 50000

    for i in range(FPS / 2): libtcod.console_flush()
    libtcod.console_print(con, 1, 17, "SCORE: %d + %d" % (player.score, bonus))
    if play_sounds and not pygame.mixer.get_busy():
        index = libtcod.random_get_int(0, 2, len(sound_a_major) - 2)
        sound_a_major[index].play()
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
    libtcod.console_flush()

    for i in range(FPS / 2): libtcod.console_flush()
    while bonus != 0:
        libtcod.console_print(con, 1, 17, "SCORE:               ")
        libtcod.console_print(con, 1, 17, "SCORE: %d + %d" % (total_score, bonus))
        total_score += 10
        bonus -= 10
        player.score = total_score
        if play_sounds and not pygame.mixer.get_busy():
            index = libtcod.random_get_int(0, 2, len(sound_a_major) - 2)
            sound_a_major[index].play()
        libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)
        if total_score % 100 == 0:
            libtcod.console_print(gui_panel, 7, 4, "SCORE: %d" % player.score)
            libtcod.console_print_frame(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, False, libtcod.BKGND_NONE, 0)
            libtcod.console_blit(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
            libtcod.console_flush()
            key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
            if key.vk == libtcod.KEY_ENTER: pass

    libtcod.console_print(con, 1, 17, "SCORE:              ")
    libtcod.console_print(con, 1, 17, "SCORE: %d!" % total_score)
    libtcod.console_print(gui_panel, 7, 4, "SCORE: %d" % player.score)
    libtcod.console_print_frame(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, False, libtcod.BKGND_NONE, 0)
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)

    libtcod.console_blit(gui_panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
    libtcod.console_blit(con, 0, 0, LVL_WIDTH, LVL_HEIGHT, 0, (SCREEN_WIDTH - LVL_WIDTH) / 2, PANEL_HEIGHT)

    if game_mode == 'normal':
        with open('sdata', 'r') as f:
            current_high_score = f.readline()
            if current_high_score[-2] == '!':
                current_high_score = current_high_score[:-2]
            current_high_score = int(current_high_score[12:])
        if player.score > current_high_score:
            with open('sdata', 'w') as f:
                f.write('High score: %d!' % player.score)
                f.write('\n')
                f.write('Defeated the Paku Queen.')
                f.write('\n')
                f.write('Vanquished %d ghosts.' % player.ghosts_killed)
                f.write('\n')

    with open('sdata', 'r') as f:
        tmp = f.readline()
        tmp += f.readline()
        tmp += f.readline()
    with open('sdata', 'w') as f:
        f.write(tmp)
        f.write('\n')

    # render the message log
    message('x', libtcod.black)
    message('x', libtcod.black)
    message(">> Press ENTER to restart or ESC to quit....")
    libtcod.console_set_default_foreground(msg_panel, libtcod.white)
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(msg_panel, color)
        libtcod.console_print(msg_panel, MSG_X + 1, y, BLANK_LINE)
        libtcod.console_print(msg_panel, MSG_X + 1, y, line)
        y += 1
    libtcod.console_set_default_foreground(msg_panel, libtcod.white)
    libtcod.console_print_frame(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, False, libtcod.BKGND_OVERLAY, 0)
    libtcod.console_blit(msg_panel, 0, 0, SCREEN_WIDTH, MSG_HEIGHT, 0, 0, MSG_Y)

    libtcod.console_flush()

    FPS = 20
    libtcod.sys_set_fps(FPS)

    player.ghosts_killed = 0

    while True:

        key = libtcod.console_wait_for_keypress(True)
        if key.vk in (libtcod.KEY_ENTER, libtcod.KEY_KPENTER):
            pygame.mixer.music.stop()
            game_mode = title_screen()
            hello_world()
            libtcod.console_clear(0)
            fov_recompute = True
            return
        if key.vk == libtcod.KEY_ESCAPE:
            pygame.mixer.music.stop()
            for panel in (con, gui_panel, msg_panel, splash_panel, inv_panel):
                libtcod.console_delete(panel)
            libtcod.console_clear(0)
            exit(0)
            return

#----------#
### INIT ###
#----------#

game_state = 'initializing'

# creating the screen and consoles
libtcod.console_set_custom_font(FONT, libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_ASCII_INROW)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Netpack v%s' % VERSION, False, libtcod.RENDERER_SDL)
libtcod.sys_set_fps(FPS)
con = libtcod.console_new(LVL_WIDTH, LVL_HEIGHT)
gui_panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
msg_panel = libtcod.console_new(SCREEN_WIDTH, MSG_HEIGHT)
splash_panel = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
inv_panel = libtcod.console_new(LVL_WIDTH, LVL_HEIGHT)

possible_etchings = []

play_sounds = True
while True:

    pygame.mixer.init(44100, 16, 2)

    sound_collect_pellet = []
    for i in range(1, 9):
        sound_collect_pellet.append( pygame.mixer.Sound('snd/a_minor_%d.wav' % i) )
    sound_step = []
    for i in range(1, 5):
        sound_step.append( pygame.mixer.Sound('snd/step%d.wav' % i) )
    sound_a_major = []
    for i in range(1, 9):
        sound_a_major.append( pygame.mixer.Sound('snd/a_minor_%d.wav' % i) )
    sound_crash = []
    for i in range(1, 4):
        sound_crash.append( pygame.mixer.Sound('snd/crash%d.wav' % i) )
    sound_break = []
    for i in range(1, 4):
        sound_break.append( pygame.mixer.Sound('snd/break%d.wav' % i) )
    sound_a_major[2] = pygame.mixer.Sound('snd/a_major_3.wav')
    sound_a_major[5] = pygame.mixer.Sound('snd/a_major_6.wav')
    sound_collect_power_pellet = pygame.mixer.Sound('snd/p_pellet.wav')
    sound_player_attack = pygame.mixer.Sound('snd/player_attack.wav')
    sound_ghost_attack = pygame.mixer.Sound('snd/ghost_attack.wav')
    sound_block = pygame.mixer.Sound('snd/block.wav')
    sound_kill_ghost = pygame.mixer.Sound('snd/kill_ghost.wav')
    sound_eat_ghost = pygame.mixer.Sound('snd/eat.wav')
    sound_staircase = pygame.mixer.Sound('snd/staircase.wav')
    sound_go_up = pygame.mixer.Sound('snd/go_up.wav')
    sound_level_up = pygame.mixer.Sound('snd/level_up.wav')
    sound_death = pygame.mixer.Sound('snd/death.wav')
    sound_game_over = pygame.mixer.Sound('snd/game_over.wav')
    sound_cursor = pygame.mixer.Sound('snd/cursor.wav')
    sound_select = pygame.mixer.Sound('snd/select.wav')
    sound_appletini = pygame.mixer.Sound('snd/appletini.wav')
    sound_orange_peel = pygame.mixer.Sound('snd/orange_peel.wav')
    sound_scroll_of_pear = pygame.mixer.Sound('snd/scroll_of_pear.wav')
    sound_strawberry_jam = pygame.mixer.Sound('snd/strawberry_jam.wav')
    sound_cherry_bomb = pygame.mixer.Sound('snd/cherry_bomb.wav')
    sound_item = pygame.mixer.Sound('snd/item.wav')
    sound_light = pygame.mixer.Sound('snd/light.wav')
    sound_souls = pygame.mixer.Sound('snd/souls.wav')
    sound_close_up = pygame.mixer.Sound('snd/close_up.wav')

    pygame.mixer.music.load('snd/title.ogg')

    break

TURN = 0

royal_paw_splash()
pigs_splash()
game_mode = title_screen()
libtcod.console_clear(0)

# FOV setup
fov_map = libtcod.map_new(LVL_WIDTH, LVL_HEIGHT)
for y in range(LVL_HEIGHT):
    for x in range(LVL_WIDTH):
        libtcod.map_set_properties(fov_map, x, y, True, True)
fov_recompute = True

alphabet = 'abcdefghjklmnopqrstuvwyz'

if game_mode == 'load game':
    sd = SaveData()
    sd.load()
else:
    hello_world()
    message("Welcome to Netpack v%s!" % VERSION, libtcod.yellow)

#---------------#
### MAIN LOOP ###
#---------------#

while not libtcod.console_is_window_closed():

    if game_state == 'quit': break

    # initialize new level
    if game_state == 'initializing level':
        load_next_level()
        TURN = 0

    # render screen
    render_all(current_level)
    libtcod.console_flush()

    # debug msgs


#    if current_level.ghosts != []:
#
#        print "\nTURN %d\n" % TURN
#
#        print "ghost stats"
#        print "lev: %d" % current_level.ghosts[0].level
#        print "hp : %d" % current_level.ghosts[0].hp
#        print "pow: %s" % current_level.ghosts[0].attack_dice
#        print "def: %s" % current_level.ghosts[0].defense_dice
#
#        print "\nplayer stats"
#        print "lev: %d" % player.level
#        print "hp : %d" % player.hp
#        print "pow: %s + %d" % (player.attack_dice, player.attack_bonus)
#        print "def: %s + %d" % (player.defense_dice, player.defense_bonus)

    # clear positions from console
    clear_all()

    # player takes turn
    if player.hp <= 0: player_dead()
    handle_keys()
    if game_state == 'quit': break
    if player.state == 'moved':
        TURN += 1

    # items bounce
    for item in current_level.items:
        if TURN % 2 == 0 and player.state == 'moved':
            item.bounce()

    # ghosts take turns
    if current_level.ghosts_in_cage != [] and player.state == 'moved': spawn_ghosts()
    if player.state == 'moved': handle_ghosts()

    # items generate
    if player.state == 'moved' and game_state == 'playing' and len(current_level.ghosts) > 0 and current_level.items_to_spawn > 0:
        if current_level.dlvl > 3:
            if libtcod.random_get_int(0, 1, 95) == 1:
                generate_item()
                current_level.items_to_spawn -= 1

    # check win conditions
    if game_state == 'playing':
        if current_level.ghosts == [] or current_level.pellets == []: win_level()

for panel in (con, gui_panel, msg_panel, splash_panel, inv_panel):
    libtcod.console_delete(panel)
libtcod.console_clear(0)
