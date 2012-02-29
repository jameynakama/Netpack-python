           |                 |
   \   -_)  _| _ \  _` |  _| | /
_| _|\___|\__|.__/\__,_|\__|_\_\
               _|

Netpack v1.2
(c) 2011 Royal Paw

by Jamey DeOrio
http://royal-paw.com
'jamey' at 'royal-paw' dot 'com'


 ---------------- [--- CONTENTS ---] ----------------

x1 - The Introduction

x2 - The Story

x3 - The Gameplay

     x3.a - The Save System

     x3.b - The Items

     x3.c - The Controls

x4 - The Change Log


 ---------------- [--- x1 - The Introduction ---] ---------------- 

Netpack was coded in Python and uses The Doryen Library, otherwise known as
libtcod. pxtone was used to compose the sound effects and music, and pygame was
used as the sound and music engine. py2exe was used to compile the Windows
distribution, as well as the pygame2exe compile script found on the pygame wiki.

I extend my humble thanks to the following:

Portland Indie Game Squad
Jotaf, Jice, and the rest of the libtcod gang
Daisuke Amaya (Pixel)
/r/indiegaming
TIGSource community
Tim W.
IndieGames.com
Gamasutra
Lewis Denby and PC Gamer
LordKaT
GEEMag.de (Love For Games)
SG.hu


 ---------------- [--- x2 - The Story ---] ------------------

After slashing your way through legions of the evil Paku King's imps and
gremlins, diving farther and farther into the depths of his underground lair,
you finally stand over his stinking body, triumphant, unwavering, and wrench the
Mace of the Four Winds from his cold grip. Revenge at long last! Unfortunately,
you spent your last scroll of identify on an iron chain a few floors up, and as
the Paku King's death rattle snickers through the caverns, the Mace of the Four
Winds melds itself to your hand. It's been haunted!

And again through the caverns echoes a new sensation, the chill of all the
tortured spirits of the monsters you slew, their silent, unanimous shriek
clambering underneath your skin, scraping across your bones, and sending you to
your knees. It becomes clear that your climb to the top will not go unnoticed,
that an entire horde of the undead now awaits your ascent.

"Well," you grunt, gripping the Mace of the Four Winds tighter, "how better to
rid this curse than to destroy every last spirit haunting this crooked
place...," and you rise.


 ---------------- [--- x3 - The Gameplay ---] ----------------

The only items in your inventory - for now - are the Haunted Mace of the Four
Winds and a few leftover appletinis.  While you can't drop the mace until the
curse is lifted, the curse does have one fortunate benefit: you now have the
ability to harm and ultimately annihilate ghosts. Your goal will be to clear
every floor of the four ghosts to continue your ascent, achieving the highest
score possible.

Gameplay proceeds similarly to early Pac-Man games, collecting pellets and
eating ghosts. However, you now have the ability to fight ghosts as well, and
each floor can be won by killing all the ghosts or by eating all the pellets.
There are benefits to clearing all the ghosts, but beware - any remaining
pellets in the maze will disappear.

The player gains a level when the experience bar is filled and for every 10,000
points earned. Ghosts level up according to the dungeon level.


   ----------------------
>-- x3.a The Save System -->
   ----------------------

Netpack has a single temporary save slot. Game data is automatically saved every
time the player ascends to the next floor. The save data only exists until the
next game is started or loaded. It is also deleted if the player wins the game.


   ----------------
>-- x3.b The Items -->
   ----------------

.                       - Pellets renew your health when needed and give you
                          experience when your health is full.
o                       - Power pellets grant you the brief ability to consume
                          ghosts, although the ghosts will quickly respawn from
                          their grave.
i                       - The Mace of the Four Winds is haunted, stuck to your
                          hand and drawing the undead toward you.
s                       - This iron chain seems to have been left behind....
# (grey)                - Some previous adventurers left messages in the maze.


>-- Fruits -->

a                       - Appletinis restore 1/3rd of your max health. Cheers!
s                       - Strawberry jam is a magical and mysterious element
                          that warps you to random places.
c                       - Cherry bombs are powerful explosives that harm
                          several enemies at once. Duck!
p (green)               - Scroll of pear spell slows down time for enemies. Two
                          in action together can stop time altogether.
o                       - Orange peels are gigantic and can be worn as
                          temporary armor.
p (brown)               - Pretzels, once untwisted, make for menacing whips,
                          until they break.
b                       - Banana nectar is rare and comes in small, dusty vials.
                          A single drop can bring you to the next p-level.


   ---------------------
>-- x3.c - The Controls -->
   ---------------------

Up, Down, Left, Right   - Move hero one step (bump into ghosts to fight)
                          . 8, 2, 4, and 6 also work
< (Shift-Comma)         - Move up one level
i                       - Open/close the inventory
s                       - Toggle sound effects 
F4                      - Toggle fullscreen 
Esc                     - Exits inventory screen or brings up quit menu
a-g                     - Use corresponding item from inventory


 ---------------- [--- x4 - The Change Log ---] ---------------- 

9-29-2011 v1.20
Final version save for small bug fixes, if they are brought to my attention.

- single-use temporary save slot
- fine-tuned difficulty (it is now pretty hard)
- ability to reset high score from the title screen

9-12-2011 v1.00
Another gigantic update and the first full public release!

- two different endings
- secret maze
- high scores (local)
- more animations

9-05-2011 v0.90
Big, big update. The gameplay and strategy is radically altered with the new
inventory system.

- new font for improved look and readability
- improved graphics/effects
- fruits (moving items)
- inventory system
- different game modes

8-14-2011 v0.61

- added sound effects and title screen music
- player's and ghosts' attack and defense are now based on dice rolls
- can now win levels by eating all the pellets

8-08-2011 v0.50
There is no change log yet! However, the following additions are planned:

- fruits (power-ups)
- high scores
- different ghost personalities and strengths
- changing the attack methods to use traditional dice (maybe)
- stats screen (maybe)
