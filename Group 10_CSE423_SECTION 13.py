from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import time
import random

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
CENTER_X = WINDOW_WIDTH // 2   
CENTER_Y = WINDOW_HEIGHT // 2  


STATE_MENU = 0
STATE_PLAYING = 1
STATE_PAUSED = 2
STATE_GAME_OVER = 3
STATE_VICTORY = 4


CAM_THIRD_PERSON = 0
CAM_FIRST_PERSON = 1
CAM_ORBIT = 2


# 3D BOUNDARY

CORRIDOR_MIN_X = -320.0
CORRIDOR_MAX_X =  320.0
CORRIDOR_MIN_Z =   35.0
CORRIDOR_MAX_Z =  165.0

# 3 Combat Lanes
LANE_LEFT_X = -180.0
LANE_CENTER_X =  0.0
LANE_RIGHT_X =  180.0

PLAYER_FIXED_Y = -120.0   # Fixed player depth
STREAM_SPAWN_Y = 1100.0   # Spawn for entities
STREAM_DESPAWN_Y = -350.0 

# Projectile Boundaries
PROJECTILE_MAX_Y = 1250.0 

FOV_Y = 95.0
ASPECT_RATIO = 1.25


SPEED_LOW = 0
SPEED_MEDIUM = 1
SPEED_HIGH = 2
SPEED_MULTIPLIERS = [0.65, 0.90, 1.25]
SPEED_LABELS = ["LOW (0.65x)", "MEDIUM (0.9x)", "HIGH (1.25x)"]


def clamp(val, min_val, max_val):
    return max(min_val, min(max_val, val))


class SparkParticle:
    
    def __init__(self, pos, color=(1.0, 0.75, 0.2), speed=200.0, lifetime=0.35):
        self.pos = [pos[0], pos[1], pos[2]]
        angle = random.uniform(0.0, 6.283)
        z_angle = random.uniform(-0.85, 0.85)
        sp = random.uniform(speed * 0.35, speed)
        self.vel = [
            sp * math.cos(angle),
            sp * math.sin(angle),
            sp * z_angle
        ]
        self.color = color
        self.lifetime = lifetime
        self.age = 0.0
        self.active = True

    def update(self, dt):
        self.age += dt
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        self.pos[2] += self.vel[2] * dt
        if self.age >= self.lifetime:
            self.active = False


class SpaceGate:
   
    def __init__(self, y):
        self.y = y

    def update(self, dt, speed):
        self.y -= speed * dt
        if self.y < STREAM_DESPAWN_Y:
            self.y += 1800.0


class Projectile:
    def __init__(self, pos, speed=1200.0, lifetime=1.2, is_enemy=False, vx=0.0):
        self.pos = [pos[0], pos[1], pos[2]]
        self.speed = speed
        self.vx = vx
        self.radius = 4.0
        self.lifetime = lifetime
        self.age = 0.0
        self.active = True
        self.hit_target = False  
        self.is_enemy = is_enemy


    def update(self, dt):
        
        self.age += dt
        self.pos[0] += self.vx * dt
        if getattr(self, 'is_enemy', False):
            self.pos[1] -= self.speed * dt
        else:
            self.pos[1] += self.speed * dt
        
        if self.age >= self.lifetime or self.pos[1] >= PROJECTILE_MAX_Y or self.pos[1] <= STREAM_DESPAWN_Y:
            self.active = False


class EnemyShip:
    def __init__(self, is_boss=False, wave=1):
        self.pos = [0.0, STREAM_SPAWN_Y, 85.0]
        self.target_y = PLAYER_FIXED_Y + 450.0
        self.is_boss = is_boss
        
        if is_boss:
            if wave == 1: self.hp = 8
            elif wave == 2: self.hp = 10
            else: self.hp = 15
            self.fire_timer = 0.5
            self.radius = 50.0
        else:
            if wave == 1: self.hp = 4
            elif wave == 2: self.hp = 5
            else: self.hp = 6
            self.fire_timer = 1.0
            self.radius = 35.0
            
        self.active = True

    def update(self, dt, player_x, player_z):
        if self.pos[1] > self.target_y:
            self.pos[1] -= 350.0 * dt
        else:
            self.pos[1] = self.target_y

    
        self.pos[0] += (player_x - self.pos[0]) * 1.2 * dt
        self.pos[2] += (player_z - self.pos[2]) * 1.2 * dt

class Obstacle:
    def __init__(self, x, y, z):
        self.pos = [x, y, z]
        self.radius = 20.0
        self.active = True

    def update(self, dt, speed):
        self.pos[1] -= speed * dt
        if self.pos[1] < STREAM_DESPAWN_Y:
            self.active = False


class Coin:
    def __init__(self, x, y, z):
        self.pos = [x, y, z]
        self.radius = 15.0
        self.rotation = 0.0
        self.active = True

    def update(self, dt, speed):
        self.pos[1] -= speed * dt
        self.rotation = (self.rotation + 180.0 * dt) % 360.0
        if self.pos[1] < STREAM_DESPAWN_Y:
            self.active = False


class HeartCollectible:
    def __init__(self, x, y, z):
        self.pos = [x, y, z]
        self.radius = 18.0
        self.time_val = 0.0
        self.active = True

    def update(self, dt, speed):
        self.pos[1] -= speed * dt
        self.time_val += dt
        if self.pos[1] < STREAM_DESPAWN_Y:
            self.active = False


class PowerUp:
    def __init__(self, x, y, z):
        self.pos = [x, y, z]
        self.radius = 20.0
        self.rotation = 0.0
        self.active = True

    def update(self, dt, speed):
        self.pos[1] -= speed * dt
        self.rotation = (self.rotation + 120.0 * dt) % 360.0
        if self.pos[1] < STREAM_DESPAWN_Y:
            self.active = False


class GameState:
    def __init__(self):
        self.state = STATE_MENU
        self.camera_mode = CAM_THIRD_PERSON
        self.speed_mode = SPEED_LOW  
        
        # Player 3D Coordinates
        self.player_x = 0.0
        self.player_y = PLAYER_FIXED_Y
        self.player_z = 85.0
        self.player_roll = 0.0 
        self.anim_time = 0.0
        
        # Weapon 
        self.projectiles = []
        self.obstacles = []
        self.obstacle_spawn_timer = 0.0
        self.orbs_killed = 0
        self.enemy_ship = None
        self.enemy_ships_killed = 0
        self.enemy_delay = 0.0
        self.wave_transition_timer = 0.0
        self.fire_cooldown = 0.15 
        self.fire_timer = 0.0
        self.projectile_speed = 1200.0
        self.cannon_side = 0     # 0 = Left Cannon... 1 = Right Cannon
        self.shots_fired = 0
        self.missed_bullets = 0
        
        
        self.scroll_speed = 300.0
        self.grid_offset = 0.0
        
        self.pylons = []
        self.init_pylons()
        self.gates = [SpaceGate(float(y)) for y in range(200, 1800, 600)]
        
        
        self.stars_bg = []
        self.stars_mid = []
        self.stars_fg = []
        self.init_stars()
        
        
        self.particles = []
        
        # Orbit Camera Angles
        self.orbit_yaw = 0.0
        self.orbit_pitch = 25.0
        self.orbit_distance = 320.0
        
        
        self.score = 0
        self.lives = 3
        self.max_lives = 4
        self.wave = 1
        self.escaped_count = 0
        
        # Collectibles Power-Ups
        self.coins = []
        self.coins_collected = 0
        self.coin_spawn_timer = 1.0
        
        self.hearts = []
        self.heart_spawn_timer = 18.0
        
        self.powerups = []
        self.powerup_spawn_timer = 12.0
        self.powerup_triple_timer = 0.0
        self.shield_active = False
        

        
        self.cheat_mode = False
        

        
        self.magnet_mode = False
        
        
        self.last_time = time.time()
        self.delta_time = 0.016
        self.fps = 60.0
        self.frame_count = 0
        self.fps_timer = time.time()

    def get_speed_multiplier(self):
        return SPEED_MULTIPLIERS[self.speed_mode]

    def cycle_speed(self):
        self.speed_mode = (self.speed_mode + 1) % 3

    def spawn_sparks(self, pos, count=12, color=(1.0, 0.75, 0.2), speed=220.0):
        
        for _ in range(count):
            self.particles.append(SparkParticle(pos, color=color, speed=speed))

    def init_pylons(self):
        
        self.pylons = []
        for y_pos in range(-300, 1300, 200):
            self.pylons.append(float(y_pos))

    def init_stars(self):
        
        self.stars_bg = []
        self.stars_mid = []
        self.stars_fg = []
        
        #(Violet / Cyan)
        for i in range(40):
            sx = ((i * 79) % 860) - 430.0
            sy = ((i * 53) % 1600) - 350.0
            sz = ((i * 37) % 260) + 10.0
            self.stars_bg.append([sx, sy, sz])
            
        #(White / Ice Blue)
        for i in range(40):
            sx = ((i * 67) % 760) - 380.0
            sy = ((i * 43) % 1500) - 300.0
            sz = ((i * 29) % 220) + 15.0
            self.stars_mid.append([sx, sy, sz])
            
        #(Gold / Starlight)
        for i in range(20):
            sx = ((i * 97) % 680) - 340.0
            sy = ((i * 61) % 1400) - 250.0
            sz = ((i * 47) % 190) + 25.0
            self.stars_fg.append([sx, sy, sz])

    def reset(self):
        self.state = STATE_PLAYING
        self.speed_mode = SPEED_LOW
        self.player_x = 0.0
        self.player_y = PLAYER_FIXED_Y
        self.player_z = 85.0
        self.player_roll = 0.0
        self.grid_offset = 0.0
        self.anim_time = 0.0
        self.init_pylons()
        self.gates = [SpaceGate(float(y)) for y in range(200, 1800, 600)]
        self.init_stars()
        self.particles = []
        self.camera_mode = CAM_THIRD_PERSON
        self.projectiles = []
        self.obstacles = []
        self.obstacle_spawn_timer = 0.0
        self.orbs_killed = 0
        self.enemy_ship = None
        self.enemy_ships_killed = 0
        self.enemy_delay = 0.0
        self.wave_transition_timer = 0.0
        self.fire_timer = 0.0
        self.cannon_side = 0
        self.shots_fired = 0
        self.missed_bullets = 0
        self.score = 0
        self.lives = 3
        self.coins = []
        self.coins_collected = 0
        self.coin_spawn_timer = 1.0
        self.hearts = []
        self.heart_spawn_timer = 18.0
        self.powerups = []
        self.powerup_spawn_timer = 12.0
        self.powerup_triple_timer = 0.0
        self.shield_active = False
        self.wave = 1
        self.escaped_count = 0
        self.last_time = time.time()


game = GameState()


def draw_player_spaceship(px, py, pz, roll, anim_time=0.0):

    glPushMatrix()
    glTranslatef(px, py, pz)
    
    
    glRotatef(roll, 0.0, 1.0, 0.0)
    
    
    glScalef(0.72, 0.72, 0.72)
    
    
    glColor3f(0.12, 0.22, 0.44)
    glPushMatrix()
    glScalef(0.75, 2.35, 0.44)
    glutSolidCube(40)
    glPopMatrix()
    
    
    glColor3f(0.18, 0.35, 0.65)
    glPushMatrix()
    glTranslatef(0.0, -4.0, 9.0)
    glScalef(0.45, 1.8, 0.25)
    glutSolidCube(36)
    glPopMatrix()
    
    
    glColor3f(0.25, 0.55, 0.92)
    glPushMatrix()
    glTranslatef(0.0, 36.0, -3.0)
    glRotatef(-90.0, 1.0, 0.0, 0.0)
    gluCylinder(gluNewQuadric(), 13.5, 2.0, 44.0, 14, 6)
    glPopMatrix()

    
    glColor3f(0.25, 0.92, 1.0)
    glPushMatrix()
    glTranslatef(0.0, 11.0, 9.5)
    glScalef(0.58, 1.35, 0.52)
    gluSphere(gluNewQuadric(), 13.0, 14, 14)
    glPopMatrix()

    
    glColor3f(0.20, 0.36, 0.60)
    glPushMatrix()
    glTranslatef(0.0, -7.0, -2.0)
    glScalef(3.5, 0.88, 0.16)
    glutSolidCube(30)
    glPopMatrix()
    
    
    glColor3f(0.16, 0.28, 0.50)
    glPushMatrix()
    glTranslatef(-52.0, -11.0, 5.5)
    glScalef(0.16, 0.78, 0.72)
    glutSolidCube(20)
    glPopMatrix()
    
    
    glPushMatrix()
    glTranslatef(-52.0, -11.0, 13.0)
    red_pulse = 0.7 + 0.3 * math.sin(anim_time * 8.0)
    glColor3f(1.0 * red_pulse, 0.1, 0.1)
    gluSphere(gluNewQuadric(), 3.2, 8, 8)
    glPopMatrix()
    
    
    glColor3f(0.16, 0.28, 0.50)
    glPushMatrix()
    glTranslatef(52.0, -11.0, 5.5)
    glScalef(0.16, 0.78, 0.72)
    glutSolidCube(20)
    glPopMatrix()
    
    
    glPushMatrix()
    glTranslatef(52.0, -11.0, 13.0)
    green_pulse = 0.7 + 0.3 * math.sin(anim_time * 8.0 + 3.14)
    glColor3f(0.1, 1.0 * green_pulse, 0.25)
    gluSphere(gluNewQuadric(), 3.2, 8, 8)
    glPopMatrix()

    
    flame_flicker = 16.0 + 4.5 * math.sin(anim_time * 26.0)
    
    # Left Engine
    glColor3f(0.18, 0.18, 0.24)
    glPushMatrix()
    glTranslatef(-16.0, -36.0, 0.0)
    glRotatef(90.0, 1.0, 0.0, 0.0)
    gluCylinder(gluNewQuadric(), 7.5, 7.5, 18.0, 12, 6)
    
    # Outer Orange Flame
    glColor3f(1.0, 0.45, 0.05)
    glTranslatef(0.0, 0.0, 18.0)
    gluCylinder(gluNewQuadric(), 6.5, 1.5, flame_flicker, 10, 4)
    
    # Inner Thrust
    glColor3f(1.0, 0.95, 0.65)
    gluSphere(gluNewQuadric(), 5.2, 8, 8)
    glPopMatrix()
    
    # Right Engine
    glColor3f(0.18, 0.18, 0.24)
    glPushMatrix()
    glTranslatef(16.0, -36.0, 0.0)
    glRotatef(90.0, 1.0, 0.0, 0.0)
    gluCylinder(gluNewQuadric(), 7.5, 7.5, 18.0, 12, 6)
    
    # Outer Orange Flame
    glColor3f(1.0, 0.45, 0.05)
    glTranslatef(0.0, 0.0, 18.0)
    gluCylinder(gluNewQuadric(), 6.5, 1.5, flame_flicker, 10, 4)
    
    # Inner Thrust
    glColor3f(1.0, 0.95, 0.65)
    gluSphere(gluNewQuadric(), 5.2, 8, 8)
    glPopMatrix()

    
    # Left Wing Cannon
    glColor3f(0.75, 0.80, 0.88)
    glPushMatrix()
    glTranslatef(-38.0, -5.0, -3.0)
    glRotatef(-90.0, 1.0, 0.0, 0.0)
    gluCylinder(gluNewQuadric(), 3.0, 2.2, 44.0, 8, 4)
    # Green Plasma
    glColor3f(0.0, 1.0, 0.45)
    glTranslatef(0.0, 0.0, 44.0)
    gluSphere(gluNewQuadric(), 3.2, 8, 8)
    glPopMatrix()
    
    # Right Wing Cannon
    glColor3f(0.75, 0.80, 0.88)
    glPushMatrix()
    glTranslatef(38.0, -5.0, -3.0)
    glRotatef(-90.0, 1.0, 0.0, 0.0)
    gluCylinder(gluNewQuadric(), 3.0, 2.2, 44.0, 8, 4)
    # Green Plasma
    glColor3f(0.0, 1.0, 0.45)
    glTranslatef(0.0, 0.0, 44.0)
    gluSphere(gluNewQuadric(), 3.2, 8, 8)
    glPopMatrix()

    glPopMatrix()


def draw_enemy_spaceship(px, py, pz, is_boss=False, anim_time=0.0):
    
    glPushMatrix()
    glTranslatef(px, py, pz)
    glRotatef(180.0, 0.0, 0.0, 1.0)
    
    if is_boss:
        glScalef(1.45, 1.45, 1.45)
        c_body = (0.22, 0.12, 0.32)
        c_cone = (0.85, 0.72, 0.15)
        c_glass = (0.25, 0.95, 0.4)
        c_wings = (0.35, 0.22, 0.45)
    else:
        glScalef(0.92, 0.92, 0.92)
        c_body = (0.55, 0.15, 0.15)
        c_cone = (0.88, 0.22, 0.22)
        c_glass = (1.0, 0.25, 0.25)
        c_wings = (0.62, 0.22, 0.22)
    
    
    glColor3f(*c_body)
    glPushMatrix()
    glScalef(0.75, 2.3, 0.44)
    glutSolidCube(40)
    glPopMatrix()
    

    glColor3f(*c_cone)
    glPushMatrix()
    glTranslatef(0.0, 36.0, -3.0)
    glRotatef(-90.0, 1.0, 0.0, 0.0)
    gluCylinder(gluNewQuadric(), 13.5, 2.0, 42.0, 12, 6)
    glPopMatrix()


    glColor3f(*c_glass)
    glPushMatrix()
    glTranslatef(0.0, 10.0, 9.0)
    if is_boss:
        pulse_boss = 1.0 + 0.12 * math.sin(anim_time * 8.0)
        glScalef(0.65 * pulse_boss, 1.35 * pulse_boss, 0.55 * pulse_boss)
    else:
        glScalef(0.6, 1.3, 0.5)
    gluSphere(gluNewQuadric(), 13.0, 12, 12)
    glPopMatrix()


    glColor3f(*c_wings)
    glPushMatrix()
    glTranslatef(0.0, -6.0, -2.0)
    glScalef(3.6, 0.85, 0.16)
    glutSolidCube(30)
    glPopMatrix()
    
    # Enemy Rear Thrust
    glColor3f(1.0, 0.25, 0.1)
    glPushMatrix()
    glTranslatef(-14.0, -36.0, 0.0)
    gluSphere(gluNewQuadric(), 5.0, 8, 8)
    glTranslatef(28.0, 0.0, 0.0)
    gluSphere(gluNewQuadric(), 5.0, 8, 8)
    glPopMatrix()
    
    glPopMatrix()

def get_canonical_muzzle_position(px, py, pz, side_toggle):

    wing_x_offset = -27.36 if side_toggle == 0 else 27.36
    muzzle_y = py + 28.08
    muzzle_z = pz - 2.16
    return [px + wing_x_offset, muzzle_y, muzzle_z]

def fire_projectile():

    if game.state != STATE_PLAYING:
        return
    if game.fire_timer > 0.0:
        return
        
    px, py, pz = game.player_x, game.player_y, game.player_z
    
    if game.powerup_triple_timer > 0.0:
        
        left_muzzle = get_canonical_muzzle_position(px, py, pz, 0)
        right_muzzle = get_canonical_muzzle_position(px, py, pz, 1)
        center_pos = [px, py + 28.08, pz - 2.16]
        
        proj_center = Projectile(center_pos, speed=game.projectile_speed, lifetime=1.2, vx=0.0)
        proj_left = Projectile(left_muzzle, speed=game.projectile_speed, lifetime=1.2, vx=-180.0)
        proj_right = Projectile(right_muzzle, speed=game.projectile_speed, lifetime=1.2, vx=180.0)
        
        game.projectiles.extend([proj_center, proj_left, proj_right])
        game.shots_fired += 3
        game.fire_timer = game.fire_cooldown * 0.65  
    else:
        muzzle_pos = get_canonical_muzzle_position(px, py, pz, game.cannon_side)
        proj = Projectile(muzzle_pos, speed=game.projectile_speed, lifetime=1.2)
        game.projectiles.append(proj)
        game.shots_fired += 1
        game.fire_timer = game.fire_cooldown
        game.cannon_side = 1 - game.cannon_side  

def update_projectiles(dt):
    
    if game.state != STATE_PLAYING:
        return
        
    if game.fire_timer > 0.0:
        game.fire_timer = max(0.0, game.fire_timer - dt)
        
    surviving_projectiles = []
    for p in game.projectiles:
        p.update(dt)
        if p.active:
            surviving_projectiles.append(p)
        else:
            
            if not p.hit_target:
                game.missed_bullets += 1
                
    game.projectiles = surviving_projectiles


def draw_obstacles():
    
    for obs in game.obstacles:
        glPushMatrix()
        glTranslatef(obs.pos[0], obs.pos[1], obs.pos[2])
        # Outer Glowing Orange Shell
        glColor3f(1.0, 0.35, 0.05)
        gluSphere(gluNewQuadric(), obs.radius, 16, 16)
        # Inner Fiery Core
        glColor3f(1.0, 0.85, 0.2)
        gluSphere(gluNewQuadric(), obs.radius * 0.55, 10, 10)
        glPopMatrix()

def draw_coins():
    
    for c in game.coins:
        if not c.active:
            continue
        glPushMatrix()
        glTranslatef(c.pos[0], c.pos[1], c.pos[2])
        glRotatef(c.rotation, 0.0, 0.0, 1.0)
        glRotatef(75.0, 1.0, 0.0, 0.0)
        
        
        glColor3f(1.0, 0.84, 0.0)
        gluCylinder(gluNewQuadric(), 12.0, 12.0, 3.5, 14, 2)
        
        
        glColor3f(1.0, 0.95, 0.3)
        gluSphere(gluNewQuadric(), 8.5, 10, 10)
        glPopMatrix()

def draw_hearts():
    
    for h in game.hearts:
        if not h.active:
            continue
        glPushMatrix()
        glTranslatef(h.pos[0], h.pos[1], h.pos[2])
        
        pulse = 1.0 + 0.16 * math.sin(h.time_val * 6.0)
        glScalef(pulse, pulse, pulse)
        
        glColor3f(1.0, 0.15, 0.25) # Deep Crimson Red
        
        
        glPushMatrix()
        glTranslatef(-6.0, 3.5, 0.0)
        gluSphere(gluNewQuadric(), 7.0, 10, 10)
        glPopMatrix()
        
        
        glPushMatrix()
        glTranslatef(6.0, 3.5, 0.0)
        gluSphere(gluNewQuadric(), 7.0, 10, 10)
        glPopMatrix()
        
        
        glPushMatrix()
        glTranslatef(0.0, 2.0, -1.0)
        glRotatef(90.0, 1.0, 0.0, 0.0)
        gluCylinder(gluNewQuadric(), 9.5, 1.5, 15.0, 12, 4)
        glPopMatrix()
        
        glPopMatrix()

def draw_powerups():
    
    for pu in game.powerups:
        if not pu.active:
            continue
        glPushMatrix()
        glTranslatef(pu.pos[0], pu.pos[1], pu.pos[2])
        glRotatef(pu.rotation * 1.5, 0.0, 0.0, 1.0)
        glRotatef(pu.rotation, 1.0, 0.0, 0.0)
        
        
        glColor3f(0.15, 0.92, 1.0)
        gluSphere(gluNewQuadric(), 9.0, 12, 12)
        
        
        glColor3f(0.4, 0.68, 1.0)
        glScalef(0.65, 0.65, 0.65)
        glutSolidCube(28)
        glPopMatrix()

def draw_shield_aura(px, py, pz, anim_time=0.0):
    
    glPushMatrix()
    glTranslatef(px, py, pz)
    pulse = 1.0 + 0.05 * math.sin(anim_time * 8.0)
    glScalef(1.35 * pulse, 1.75 * pulse, 1.15 * pulse)
    glColor3f(0.2, 0.88, 1.0)
    gluSphere(gluNewQuadric(), 34.0, 12, 12)
    glPopMatrix()

def draw_projectiles():
    
    for p in game.projectiles:
        glPushMatrix()
        glTranslatef(p.pos[0], p.pos[1], p.pos[2])
        
        if getattr(p, 'is_enemy', False):
            glColor3f(1.0, 0.2, 0.2)
            gluSphere(gluNewQuadric(), 3.8, 8, 8)
            glColor3f(1.0, 0.8, 0.8)
            glScalef(0.65, 1.6, 0.65)
            gluSphere(gluNewQuadric(), 2.2, 6, 6)
        else:
            glColor3f(0.0, 1.0, 0.45)
            gluSphere(gluNewQuadric(), 3.8, 8, 8)
            glColor3f(0.7, 1.0, 0.9)
            glScalef(0.65, 1.6, 0.65)
            gluSphere(gluNewQuadric(), 2.2, 6, 6)
        
        glPopMatrix()

def draw_particles():
    
    if not game.particles:
        return
    glPointSize(3.0)
    glBegin(GL_POINTS)
    for part in game.particles:
        glColor3f(*part.color)
        glVertex3f(part.pos[0], part.pos[1], part.pos[2])
    glEnd()


def draw_scrolling_corridor():

    tile_len = 100.0
    y_start = -400.0
    y_end = 1200.0
    
    # CHECKERED FLOOR
    glBegin(GL_QUADS)
    y = y_start - (game.grid_offset % tile_len)
    row = int((game.grid_offset // tile_len))
    
    while y < y_end:
        
        if (row % 2) == 0:
            glColor3f(0.12, 0.15, 0.26)
        else:
            glColor3f(0.07, 0.09, 0.16)
        glVertex3f(CORRIDOR_MIN_X, y, 0.0)
        glVertex3f(-100.0, y, 0.0)
        glVertex3f(-100.0, y + tile_len, 0.0)
        glVertex3f(CORRIDOR_MIN_X, y + tile_len, 0.0)
        
        
        if (row % 2) == 0:
            glColor3f(0.09, 0.11, 0.20)
        else:
            glColor3f(0.15, 0.18, 0.30)
        glVertex3f(-100.0, y, 0.0)
        glVertex3f(100.0, y, 0.0)
        glVertex3f(100.0, y + tile_len, 0.0)
        glVertex3f(-100.0, y + tile_len, 0.0)
        
        
        if (row % 2) == 0:
            glColor3f(0.12, 0.15, 0.26)
        else:
            glColor3f(0.07, 0.09, 0.16)
        glVertex3f(100.0, y, 0.0)
        glVertex3f(CORRIDOR_MAX_X, y, 0.0)
        glVertex3f(CORRIDOR_MAX_X, y + tile_len, 0.0)
        glVertex3f(100.0, y + tile_len, 0.0)
        
        y += tile_len
        row += 1
    glEnd()
    

    glLineWidth(2.0)
    glBegin(GL_LINES)
    glColor3f(0.0, 0.85, 1.0) # Bright Electric Cyan
    
    # Left Lane Divider 
    glVertex3f(-100.0, -400.0, 1.0)
    glVertex3f(-100.0, 1200.0, 1.0)
    
    # Right Lane Divider 
    glVertex3f(100.0, -400.0, 1.0)
    glVertex3f(100.0, 1200.0, 1.0)
    
    
    glColor3f(0.2, 0.6, 1.0)
    glVertex3f(CORRIDOR_MIN_X, -400.0, 2.0)
    glVertex3f(CORRIDOR_MIN_X, 1200.0, 2.0)
    
   
    glVertex3f(CORRIDOR_MAX_X, -400.0, 2.0)
    glVertex3f(CORRIDOR_MAX_X, 1200.0, 2.0)
    glEnd()

def draw_boundary_pylons():

    for py in game.pylons:
       
        glPushMatrix()
        glColor3f(0.0, 0.85, 1.0)
        glTranslatef(CORRIDOR_MIN_X - 10.0, py, 100.0)
        glScalef(0.3, 0.3, 3.2)
        glutSolidCube(60)
        glPopMatrix()
        
    
        glPushMatrix()
        glColor3f(0.0, 0.85, 1.0)
        glTranslatef(CORRIDOR_MAX_X + 10.0, py, 100.0)
        glScalef(0.3, 0.3, 3.2)
        glutSolidCube(60)
        glPopMatrix()

def draw_space_gates():

    for gate in game.gates:
        gy = gate.y
        if gy < -350.0 or gy > 1250.0:
            continue
        glPushMatrix()
        glTranslatef(0.0, gy, 120.0)
        
        # Left Tower
        glColor3f(0.18, 0.28, 0.50)
        glPushMatrix()
        glTranslatef(CORRIDOR_MIN_X - 15.0, 0.0, 0.0)
        glScalef(0.5, 0.5, 4.0)
        glutSolidCube(60)
        glPopMatrix()
        
        # Right Tower
        glPushMatrix()
        glTranslatef(CORRIDOR_MAX_X + 15.0, 0.0, 0.0)
        glScalef(0.5, 0.5, 4.0)
        glutSolidCube(60)
        glPopMatrix()
        
        
        glColor3f(0.22, 0.36, 0.65)
        glPushMatrix()
        glTranslatef(0.0, 0.0, 110.0)
        glScalef(11.5, 0.45, 0.45)
        glutSolidCube(60)
        glPopMatrix()
        
        # Glowing Cyan
        glColor3f(0.0, 0.95, 1.0)
        glPushMatrix()
        glTranslatef(-180.0, 0.0, 110.0)
        gluSphere(gluNewQuadric(), 8.0, 8, 8)
        glTranslatef(180.0, 0.0, 0.0)
        gluSphere(gluNewQuadric(), 10.0, 8, 8)
        glTranslatef(180.0, 0.0, 0.0)
        gluSphere(gluNewQuadric(), 8.0, 8, 8)
        glPopMatrix()
        
        glPopMatrix()

def draw_starfield():
    
    glPointSize(1.5)
    glColor3f(0.55, 0.65, 0.95)
    glBegin(GL_POINTS)
    for star in game.stars_bg:
        glVertex3f(star[0], star[1], star[2])
    glEnd()
    
    glPointSize(2.5)
    glColor3f(0.85, 0.95, 1.0)
    glBegin(GL_POINTS)
    for star in game.stars_mid:
        glVertex3f(star[0], star[1], star[2])
    glEnd()
    
    glPointSize(3.5)
    glColor3f(1.0, 0.90, 0.65)
    glBegin(GL_POINTS)
    for star in game.stars_fg:
        glVertex3f(star[0], star[1], star[2])
    glEnd()


def setupCamera():

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV_Y, ASPECT_RATIO, 0.1, 2400.0)
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    px = game.player_x
    py = game.player_y
    pz = game.player_z
    
    if game.camera_mode == CAM_THIRD_PERSON:
        eye_x = px
        eye_y = py - 210.0
        eye_z = pz + 68.0
        
        target_x = px
        target_y = py + 380.0
        target_z = pz + 18.0
        gluLookAt(eye_x, eye_y, eye_z, target_x, target_y, target_z, 0.0, 0.0, 1.0)
        
    elif game.camera_mode == CAM_FIRST_PERSON:
        eye_x = px
        eye_y = py + 16.0
        eye_z = pz + 8.0
        
        target_x = px
        target_y = py + 400.0
        target_z = pz + 8.0
        gluLookAt(eye_x, eye_y, eye_z, target_x, target_y, target_z, 0.0, 0.0, 1.0)
        
    elif game.camera_mode == CAM_ORBIT:
        yaw_rad = math.radians(game.orbit_yaw)
        pitch_rad = math.radians(game.orbit_pitch)
        dist = game.orbit_distance
        
        eye_x = px + dist * math.sin(yaw_rad) * math.cos(pitch_rad)
        eye_y = py + dist * math.cos(yaw_rad) * math.cos(pitch_rad)
        eye_z = pz + dist * math.sin(pitch_rad)
        gluLookAt(eye_x, eye_y, eye_z, px, py, pz + 10.0, 0.0, 0.0, 1.0)


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """Renders 2D bitmap text overlay using orthographic projection."""
    glColor3f(1.0, 1.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
        
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_text_centered(y, text, font=GLUT_BITMAP_HELVETICA_18):
    approx_width = len(text) * 9.5
    x = CENTER_X - (approx_width / 2.0)
    draw_text(x, y, text, font)

def render_menu_screen():
    draw_text_centered(680, "========================================")
    draw_text_centered(650, "3D SPACE COMBAT SURVIVAL RUNNER")
    draw_text_centered(620, "========================================")
    draw_text_centered(560, "Press [ENTER] to Launch Mission")
    draw_text_centered(515, "[A] / [D] Maneuver Left & Right")
    draw_text_centered(480, "[W] / [S] Adjust Flight Elevation")
    draw_text_centered(445, "[Left Click] or [SPACE] Forward Cannons")
    draw_text_centered(410, "Speed Auto-increases with each wave")
    draw_text_centered(375, "[M] Auto-Collect Coins Magnet (when Cheat is OFF)")
    draw_text_centered(340, "[C] or [G] AI Co-Pilot (Auto-Aim & Auto-Dodge)")
    draw_text_centered(305, "Gold Coins (+50) | Rare Hearts (+1 Life)")
    draw_text_centered(270, "Blue Core (Triple Cannons + Energy Shield)")
    draw_text_centered(235, "[Right Click] or [V] Toggle Camera View")
    draw_text_centered(200, "[P] / [ESC] Pause | [R] Reset Session")

def render_playing_hud():
    cam_names = ["3rd-Person Chase", "1st-Person Cockpit", "Orbit"]
    lives_display = ("* " * game.lives) + ("- " * (game.max_lives - game.lives))
    
    if game.cheat_mode:
        mode_str = " | [CHEAT: AUTO-PILOT ON]"
    elif game.magnet_mode:
        mode_str = " | [MAGNET: ON]"
    else:
        mode_str = ""
    
    draw_text(15, 770, f"SCORE: {game.score:05d} | LIVES: [ {lives_display.strip()} ] | COINS: {game.coins_collected} | SPEED: {SPEED_LABELS[game.speed_mode]} | WAVE: {game.wave}{mode_str}")
    
    if game.wave_transition_timer > 0.0:
        if game.wave_transition_timer > 2.5:
            draw_text(CENTER_X - 160, CENTER_Y + 150, f"Congratulations! Wave {game.wave} complete")
        else:
            if game.wave == 2:
                draw_text(CENTER_X - 160, CENTER_Y + 150, f"Wave {game.wave + 1} starting. BEST OF LUCK")
            else:
                draw_text(CENTER_X - 80, CENTER_Y + 150, f"Wave {game.wave + 1} starting...")
                
    if game.powerup_triple_timer > 0.0 or game.shield_active:
        buff_parts = []
        if game.powerup_triple_timer > 0.0:
            buff_parts.append(f"OVERCHARGE [{game.powerup_triple_timer:.1f}s]")
        if game.shield_active:
            buff_parts.append("[SHIELD ACTIVE]")
        draw_text(15, 740, f"POWER-UP: {' | '.join(buff_parts)}")
        draw_text(15, 710, f"SHOTS: {game.shots_fired} | MISSED: {game.missed_bullets} | CAMERA: {cam_names[game.camera_mode]}")
    else:
        draw_text(15, 740, f"SHOTS: {game.shots_fired} | MISSED: {game.missed_bullets} | CAMERA: {cam_names[game.camera_mode]}")
        
    draw_text(15, 30, "[WASD] Move | [SPACE] Fire | [M] Coin Magnet | [C] Auto-Pilot | [V] Cam | [P] Pause")

def render_paused_overlay():
    draw_text_centered(450, "===== SIMULATION PAUSED =====")
    draw_text_centered(400, "Press [P] or [ESC] to Resume Flight")
    draw_text_centered(360, f"Current Speed: {SPEED_LABELS[game.speed_mode]}")
    draw_text_centered(320, "Press [R] to Restart Session")

def render_game_over_screen():
    draw_text_centered(500, "===== MISSION FAILED - GAME OVER =====")
    draw_text_centered(440, f"Final Score: {game.score:05d} | Coins: {game.coins_collected} | Missed: {game.missed_bullets}")
    draw_text_centered(380, "Press [R] to Re-Deploy")

def render_victory_screen():
    draw_text_centered(520, "===== MISSION ACCOMPLISHED - VICTORY =====")
    draw_text_centered(460, f"Final Score: {game.score:05d} | Coins: {game.coins_collected} | Missed: {game.missed_bullets}")
    draw_text_centered(400, "Press [R] to Return to Mission Command")


def keyboardListener(key, x, y):

    if game.state == STATE_MENU:
        if key in [b'\r', b'\n']:
            game.reset()
            game.state = STATE_PLAYING
        elif key in [b'c', b'C']:
            game.camera_mode = (game.camera_mode + 1) % 3
    elif game.state == STATE_PLAYING:
        move_step = 22.0 * max(0.7, game.get_speed_multiplier())
        elev_step = 16.0 * max(0.7, game.get_speed_multiplier())
        
        if key in [b'a', b'A']:
            game.player_x = clamp(game.player_x - move_step, CORRIDOR_MIN_X + 25.0, CORRIDOR_MAX_X - 25.0)
            game.player_roll = -15.0
        if key in [b'd', b'D']:
            game.player_x = clamp(game.player_x + move_step, CORRIDOR_MIN_X + 25.0, CORRIDOR_MAX_X - 25.0)
            game.player_roll = 15.0
        if key in [b'w', b'W']:
            game.player_z = clamp(game.player_z + elev_step, CORRIDOR_MIN_Z, CORRIDOR_MAX_Z)
        if key in [b's', b'S']:
            game.player_z = clamp(game.player_z - elev_step, CORRIDOR_MIN_Z, CORRIDOR_MAX_Z)
                                   
        if key in [b' ', b'f', b'F']:
            fire_projectile()
            
        
        if key in [b'c', b'C', b'g', b'G']:
            game.cheat_mode = not game.cheat_mode
            spark_color = (0.2, 0.95, 1.0) if game.cheat_mode else (1.0, 0.4, 0.2)
            game.spawn_sparks([game.player_x, game.player_y, game.player_z], count=16, color=spark_color)
            
        
        if key in [b'm', b'M']:
            game.magnet_mode = not game.magnet_mode
            spark_color = (1.0, 0.84, 0.1) if game.magnet_mode else (0.5, 0.5, 0.5)
            game.spawn_sparks([game.player_x, game.player_y, game.player_z], count=14, color=spark_color)
            
        
        if key in [b'v', b'V']:
            game.camera_mode = (game.camera_mode + 1) % 3
            
        
        if key in [b'\x1b', b'p', b'P']:
            game.state = STATE_PAUSED
        if key in [b'r', b'R']:
            game.reset()
            
    elif game.state == STATE_PAUSED:
        if key in [b'\x1b', b'p', b'P']:
            game.state = STATE_PLAYING
        elif key in [b'r', b'R']:
            game.reset()
            game.state = STATE_MENU
            
    elif game.state in [STATE_GAME_OVER, STATE_VICTORY]:
        if key in [b'r', b'R']:
            game.reset()
            game.state = STATE_MENU
            
    glutPostRedisplay()

def specialKeyListener(key, x, y):
    """Handles Arrow Keys for direct arcade positioning and orbit camera control."""
    if game.camera_mode == CAM_ORBIT:
        step = 6.0
        if key == GLUT_KEY_LEFT:
            game.orbit_yaw -= step
        elif key == GLUT_KEY_RIGHT:
            game.orbit_yaw += step
        elif key == GLUT_KEY_UP:
            game.orbit_pitch = clamp(game.orbit_pitch + step, 5.0, 85.0)
        elif key == GLUT_KEY_DOWN:
            game.orbit_pitch = clamp(game.orbit_pitch - step, 5.0, 85.0)
    else:
        move_step = 22.0 * max(0.7, game.get_speed_multiplier())
        elev_step = 16.0 * max(0.7, game.get_speed_multiplier())
        if key == GLUT_KEY_LEFT:
            game.player_x = clamp(game.player_x - move_step, CORRIDOR_MIN_X + 25.0, CORRIDOR_MAX_X - 25.0)
            game.player_roll = -15.0
        elif key == GLUT_KEY_RIGHT:
            game.player_x = clamp(game.player_x + move_step, CORRIDOR_MIN_X + 25.0, CORRIDOR_MAX_X - 25.0)
            game.player_roll = 15.0
        elif key == GLUT_KEY_UP:
            game.player_z = clamp(game.player_z + elev_step, CORRIDOR_MIN_Z, CORRIDOR_MAX_Z)
        elif key == GLUT_KEY_DOWN:
            game.player_z = clamp(game.player_z - elev_step, CORRIDOR_MIN_Z, CORRIDOR_MAX_Z)
            
    glutPostRedisplay()

def mouseListener(button, state, x, y):

    if state == GLUT_DOWN:
        if button == GLUT_LEFT_BUTTON:
            if game.state == STATE_PLAYING:
                fire_projectile()
            glutPostRedisplay()
        elif button == GLUT_RIGHT_BUTTON:
            game.camera_mode = (game.camera_mode + 1) % 3
            glutPostRedisplay()


def update_simulation(dt):
    """Updates optical stream flow, boundary pylons, projectiles, and auto-levels visual banking."""
    if game.state != STATE_PLAYING:
        return
        
    game.anim_time += dt
    
    game.grid_offset += game.scroll_speed * dt
    
    for i in range(len(game.pylons)):
        game.pylons[i] -= game.scroll_speed * dt
        if game.pylons[i] < STREAM_DESPAWN_Y:
            game.pylons[i] += 1600.0
            
    for gate in game.gates:
        gate.update(dt, game.scroll_speed)
            
    for star in game.stars_bg:
        star[1] -= game.scroll_speed * 0.45 * dt
        if star[1] < STREAM_DESPAWN_Y:
            star[1] += 1600.0
            
    for star in game.stars_mid:
        star[1] -= game.scroll_speed * 1.0 * dt
        if star[1] < STREAM_DESPAWN_Y:
            star[1] += 1600.0
            
    for star in game.stars_fg:
        star[1] -= game.scroll_speed * 1.6 * dt
        if star[1] < STREAM_DESPAWN_Y:
            star[1] += 1600.0
            
    for p in game.particles:
        p.update(dt)
    game.particles = [p for p in game.particles if p.active]
            
    if abs(game.player_roll) > 0.1:
        game.player_roll *= max(0.0, 1.0 - 8.0 * dt)
        
    game.player_x = clamp(game.player_x, CORRIDOR_MIN_X + 25.0, CORRIDOR_MAX_X - 25.0)
    game.player_z = clamp(game.player_z, CORRIDOR_MIN_Z, CORRIDOR_MAX_Z)


    update_projectiles(dt)


    if game.cheat_mode:
        px = game.player_x
        py = game.player_y
        pz = game.player_z
        

        incoming_threat = None
        min_threat_y_dist = 9999.0
        

        for p in game.projectiles:
            if getattr(p, 'is_enemy', False) and p.active:
                if p.pos[1] > py and (p.pos[1] - py) < 380.0:
                    dx = p.pos[0] - px
                    dz = p.pos[2] - pz
                    if abs(dx) < 65.0 and abs(dz) < 45.0:
                        y_dist = p.pos[1] - py
                        if y_dist < min_threat_y_dist:
                            min_threat_y_dist = y_dist
                            incoming_threat = p
                            

        if not incoming_threat:
            for obs in game.obstacles:
                if obs.active and obs.pos[1] > py and (obs.pos[1] - py) < 180.0:
                    dx = obs.pos[0] - px
                    dz = obs.pos[2] - pz
                    if abs(dx) < 55.0 and abs(dz) < 40.0:
                        y_dist = obs.pos[1] - py
                        if y_dist < min_threat_y_dist:
                            min_threat_y_dist = y_dist
                            incoming_threat = obs


        if incoming_threat:
            evade_speed = 720.0
            tx = incoming_threat.pos[0]
            if tx <= px:
                if px + 60.0 <= (CORRIDOR_MAX_X - 25.0):
                    game.player_x += evade_speed * dt
                    game.player_roll = 20.0
                else:
                    game.player_x -= evade_speed * dt
                    game.player_roll = -20.0
            else:
                if px - 60.0 >= (CORRIDOR_MIN_X + 25.0):
                    game.player_x -= evade_speed * dt
                    game.player_roll = -20.0
                else:
                    game.player_x += evade_speed * dt
                    game.player_roll = 20.0
                    
            tz = incoming_threat.pos[2]
            if tz <= pz and (pz + 30.0) <= CORRIDOR_MAX_Z:
                game.player_z += evade_speed * 0.65 * dt
            elif (pz - 30.0) >= CORRIDOR_MIN_Z:
                game.player_z -= evade_speed * 0.65 * dt
                
            if game.fire_timer <= 0.0:
                fire_projectile()
                
        else:

            target_pos = None
            
  
            if game.enemy_ship and game.enemy_ship.active:
                target_pos = game.enemy_ship.pos
  
            elif game.obstacles:
                closest_obs = None
                closest_y = 9999.0
                for obs in game.obstacles:
                    if obs.active and obs.pos[1] > py:
                        if obs.pos[1] < closest_y:
                            closest_y = obs.pos[1]
                            closest_obs = obs
                if closest_obs:
                    target_pos = closest_obs.pos

            elif game.coins or game.hearts:
                closest_item = None
                closest_y = 9999.0
                for c in game.coins:
                    if c.active and c.pos[1] > py and c.pos[1] < closest_y:
                        closest_y = c.pos[1]
                        closest_item = c
                for h in game.hearts:
                    if h.active and h.pos[1] > py and h.pos[1] < closest_y:
                        closest_y = h.pos[1]
                        closest_item = h
                if closest_item:
                    target_pos = closest_item.pos
                    
            if target_pos:
                tx, ty, tz = target_pos[0], target_pos[1], target_pos[2]
                track_speed = 520.0
                

                diff_x = tx - px
                if abs(diff_x) > 4.0:
                    step_x = math.copysign(min(abs(diff_x), track_speed * dt), diff_x)
                    game.player_x += step_x
                    game.player_roll = clamp(step_x * 4.0, -18.0, 18.0)
                    

                diff_z = tz - pz
                if abs(diff_z) > 4.0:
                    step_z = math.copysign(min(abs(diff_z), track_speed * 0.75 * dt), diff_z)
                    game.player_z += step_z
                    

                if abs(diff_x) < 42.0 and (game.enemy_ship or (game.obstacles and ty > py)):
                    if game.fire_timer <= 0.0:
                        fire_projectile()


    if not game.cheat_mode and game.magnet_mode:
        for c in game.coins:
            if not c.active: continue
            dx = game.player_x - c.pos[0]
            dy = game.player_y - c.pos[1]
            dz = game.player_z - c.pos[2]
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist < 650.0:
                pull = 780.0
                inv = 1.0 / max(0.01, dist)
                c.pos[0] += dx * inv * pull * dt
                c.pos[1] += dy * inv * pull * dt
                c.pos[2] += dz * inv * pull * dt
        for h in game.hearts:
            if not h.active: continue
            dx = game.player_x - h.pos[0]
            dy = game.player_y - h.pos[1]
            dz = game.player_z - h.pos[2]
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist < 650.0:
                pull = 780.0
                inv = 1.0 / max(0.01, dist)
                h.pos[0] += dx * inv * pull * dt
                h.pos[1] += dy * inv * pull * dt
                h.pos[2] += dz * inv * pull * dt


    if game.powerup_triple_timer > 0.0:
        game.powerup_triple_timer = max(0.0, game.powerup_triple_timer - dt)


    if game.wave == 3 and game.enemy_ships_killed >= 6:
        game.state = STATE_VICTORY
        return


    if game.wave_transition_timer > 0.0:
        game.wave_transition_timer -= dt
        if game.wave_transition_timer <= 0.0:
            game.wave += 1
            game.orbs_killed = 0
            game.enemy_ships_killed = 0
            game.enemy_delay = 0.0
            game.enemy_ship = None
            if game.wave == 2:
                game.speed_mode = SPEED_MEDIUM
            elif game.wave >= 3:
                game.speed_mode = SPEED_HIGH
    else:
        orbs_needed = 6 if game.wave >= 3 else 5
        boss_trigger = 5 if game.wave >= 3 else 3
        
        if game.orbs_killed >= orbs_needed:
            if game.enemy_ship is None:
                if game.enemy_delay > 0.0:
                    game.enemy_delay -= dt
                else:
                    is_boss = (game.enemy_ships_killed == boss_trigger)
                    game.enemy_ship = EnemyShip(is_boss=is_boss, wave=game.wave)
        else:
            game.obstacle_spawn_timer -= dt
            if game.obstacle_spawn_timer <= 0.0:
                ox = random.uniform(CORRIDOR_MIN_X, CORRIDOR_MAX_X)
                oy = STREAM_SPAWN_Y
                oz = random.uniform(CORRIDOR_MIN_Z, CORRIDOR_MAX_Z)
                game.obstacles.append(Obstacle(ox, oy, oz))
                if game.wave == 1:
                    game.obstacle_spawn_timer = random.uniform(2.0, 4.0)
                else:
                    game.obstacle_spawn_timer = random.uniform(1.2, 2.5)

    #Spawn & Power-Ups
    game.coin_spawn_timer -= dt
    if game.coin_spawn_timer <= 0.0:
        cx = random.uniform(CORRIDOR_MIN_X + 25.0, CORRIDOR_MAX_X - 25.0)
        cy = STREAM_SPAWN_Y
        cz = random.uniform(CORRIDOR_MIN_Z + 10.0, CORRIDOR_MAX_Z - 10.0)
        game.coins.append(Coin(cx, cy, cz))
        game.coin_spawn_timer = random.uniform(1.2, 2.2)

    game.heart_spawn_timer -= dt
    if game.heart_spawn_timer <= 0.0:
        hx = random.uniform(CORRIDOR_MIN_X + 30.0, CORRIDOR_MAX_X - 30.0)
        hy = STREAM_SPAWN_Y
        hz = random.uniform(CORRIDOR_MIN_Z + 15.0, CORRIDOR_MAX_Z - 15.0)
        game.hearts.append(HeartCollectible(hx, hy, hz))
        game.heart_spawn_timer = random.uniform(22.0, 32.0) # Rare spawn interval

    game.powerup_spawn_timer -= dt
    if game.powerup_spawn_timer <= 0.0:
        pux = random.uniform(CORRIDOR_MIN_X + 30.0, CORRIDOR_MAX_X - 30.0)
        puy = STREAM_SPAWN_Y
        puz = random.uniform(CORRIDOR_MIN_Z + 15.0, CORRIDOR_MAX_Z - 15.0)
        game.powerups.append(PowerUp(pux, puy, puz))
        game.powerup_spawn_timer = random.uniform(15.0, 24.0)

    for obs in game.obstacles:
        obs.update(dt, game.scroll_speed * 1.5)

    for c in game.coins:
        c.update(dt, game.scroll_speed * 1.3)

    for h in game.hearts:
        h.update(dt, game.scroll_speed * 1.15)

    for pu in game.powerups:
        pu.update(dt, game.scroll_speed * 1.2)

    for c in game.coins:
        if not c.active: continue
        dist = math.sqrt((game.player_x - c.pos[0])**2 + (game.player_y - c.pos[1])**2 + (game.player_z - c.pos[2])**2)
        if dist < (40.0 + c.radius):
            c.active = False
            game.coins_collected += 1
            game.score += 50
            game.spawn_sparks(c.pos, count=8, color=(1.0, 0.85, 0.2))

    for h in game.hearts:
        if not h.active: continue
        dist = math.sqrt((game.player_x - h.pos[0])**2 + (game.player_y - h.pos[1])**2 + (game.player_z - h.pos[2])**2)
        if dist < (40.0 + h.radius):
            h.active = False
            if game.lives < game.max_lives:
                game.lives += 1
            game.score += 25
            game.spawn_sparks(h.pos, count=10, color=(1.0, 0.2, 0.3))

    for pu in game.powerups:
        if not pu.active: continue
        dist = math.sqrt((game.player_x - pu.pos[0])**2 + (game.player_y - pu.pos[1])**2 + (game.player_z - pu.pos[2])**2)
        if dist < (40.0 + pu.radius):
            pu.active = False
            game.powerup_triple_timer = 10.0
            game.shield_active = True
            game.score += 75
            game.spawn_sparks(pu.pos, count=14, color=(0.2, 0.9, 1.0))

    if game.enemy_ship:
        game.enemy_ship.update(dt, game.player_x, game.player_z)
        
        game.enemy_ship.fire_timer -= dt
        if game.enemy_ship.fire_timer <= 0.0 and game.enemy_ship.pos[1] <= game.enemy_ship.target_y + 10.0:
            ex, ey, ez = game.enemy_ship.pos
            proj = Projectile([ex, ey - 40.0, ez], speed=game.projectile_speed * 0.7, lifetime=3.0, is_enemy=True)
            game.projectiles.append(proj)
            if game.enemy_ship.is_boss:
                if game.wave == 1:
                    game.enemy_ship.fire_timer = random.uniform(0.6, 1.5)
                elif game.wave == 2:
                    game.enemy_ship.fire_timer = random.uniform(0.3, 1.0)
                else:
                    game.enemy_ship.fire_timer = random.uniform(0.2, 0.6)
            else:
                if game.wave == 1:
                    game.enemy_ship.fire_timer = random.uniform(1.0, 2.5)
                elif game.wave == 2:
                    game.enemy_ship.fire_timer = random.uniform(0.7, 1.8)
                else:
                    game.enemy_ship.fire_timer = random.uniform(0.4, 1.2)

    for p in game.projectiles:
        if not p.active: continue
        
        if getattr(p, 'is_enemy', False):
            dist = math.sqrt((p.pos[0]-game.player_x)**2 + (p.pos[1]-game.player_y)**2 + (p.pos[2]-game.player_z)**2)
            if dist < (p.radius + 30.0):
                p.active = False
                game.spawn_sparks(p.pos, count=10, color=(1.0, 0.3, 0.2))
                if game.shield_active:
                    game.shield_active = False  
                else:
                    game.lives -= 1
                    if game.lives <= 0:
                        game.state = STATE_GAME_OVER
        else:
            hit_something = False
            for obs in game.obstacles:
                if not obs.active: continue
                dist = math.sqrt((p.pos[0]-obs.pos[0])**2 + (p.pos[1]-obs.pos[1])**2 + (p.pos[2]-obs.pos[2])**2)
                if dist < (p.radius + obs.radius + 20.0):
                    p.active = False
                    p.hit_target = True
                    obs.active = False
                    game.score += 10
                    game.orbs_killed += 1
                    hit_something = True
                    game.spawn_sparks(obs.pos, count=14, color=(1.0, 0.5, 0.1))
                    break

            
            if not hit_something and game.enemy_ship:
                es = game.enemy_ship
                dist = math.sqrt((p.pos[0]-es.pos[0])**2 + (p.pos[1]-es.pos[1])**2 + (p.pos[2]-es.pos[2])**2)
                if dist < (p.radius + es.radius + 20.0):
                    p.active = False
                    p.hit_target = True
                    es.hp -= 1
                    game.score += 20
                    game.spawn_sparks(p.pos, count=12, color=(0.2, 1.0, 0.5))
                    if es.hp <= 0:
                        game.spawn_sparks(es.pos, count=24, color=(1.0, 0.6, 0.2), speed=300.0)
                        game.enemy_ship = None
                        game.enemy_ships_killed += 1
                        
                        if es.is_boss:
                            game.score += 500
                            if game.wave < 3:
                                game.wave_transition_timer = 5.0
                        else:
                            game.enemy_delay = 3.0
                            game.score += 100
                
    for obs in game.obstacles:
        if not obs.active: continue
        dist = math.sqrt((game.player_x-obs.pos[0])**2 + (game.player_y-obs.pos[1])**2 + (game.player_z-obs.pos[2])**2)
        if dist < (40.0 + obs.radius):
            obs.active = False
            game.spawn_sparks(obs.pos, count=16, color=(1.0, 0.4, 0.1))
            if game.shield_active:
                game.shield_active = False  
            else:
                game.lives -= 1
                if game.lives <= 0:
                    game.state = STATE_GAME_OVER


    game.obstacles = [obs for obs in game.obstacles if obs.active]
    game.coins = [c for c in game.coins if c.active]
    game.hearts = [h for h in game.hearts if h.active]
    game.powerups = [pu for pu in game.powerups if pu.active]



def idle():

    now = time.time()
    dt = now - game.last_time
    game.last_time = now
    
    game.delta_time = clamp(dt, 0.001, 0.05)
    
    sim_dt = game.delta_time * game.get_speed_multiplier()
    update_simulation(sim_dt)
    
    game.frame_count += 1
    if now - game.fps_timer >= 0.5:
        game.fps = game.frame_count / (now - game.fps_timer)
        game.frame_count = 0
        game.fps_timer = now
        
    glutPostRedisplay()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
    
    setupCamera()
    
    if game.state not in [STATE_MENU, STATE_GAME_OVER, STATE_VICTORY]:
        draw_starfield()
        draw_scrolling_corridor()
        draw_boundary_pylons()
        draw_space_gates()
        
        if game.state in [STATE_PLAYING, STATE_PAUSED]:
            draw_projectiles()
            draw_obstacles()
            draw_coins()
            draw_hearts()
            draw_powerups()
            draw_particles()
            
        if getattr(game, 'enemy_ship', None):
            draw_enemy_spaceship(game.enemy_ship.pos[0], game.enemy_ship.pos[1], game.enemy_ship.pos[2], game.enemy_ship.is_boss, game.anim_time)
            
        if game.camera_mode in [CAM_THIRD_PERSON, CAM_ORBIT]:
            draw_player_spaceship(game.player_x, game.player_y, game.player_z, game.player_roll, game.anim_time)
            if game.shield_active:
                draw_shield_aura(game.player_x, game.player_y, game.player_z, game.anim_time)
        
    if game.state == STATE_MENU:
        render_menu_screen()
    elif game.state == STATE_PLAYING:
        render_playing_hud()
    elif game.state == STATE_PAUSED:
        render_playing_hud()
        render_paused_overlay()
    elif game.state == STATE_GAME_OVER:
        render_game_over_screen()
    elif game.state == STATE_VICTORY:
        render_victory_screen()
        
    glutSwapBuffers()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"3D Space Combat Survival Runner - CSE423")
    
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    
    glutMainLoop()

if __name__ == "__main__":
    main()
