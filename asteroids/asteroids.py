import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

import warnings

warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API"
)


import pygame
import numpy as np
import math
import random
import socket
import pickle
import threading
import time
import sys

pygame.init()
pygame.mixer.init()  # Initialize sound mixer
#-------os----------:

pasta = os.getcwd()

arquivo = os.path.join(pasta, "max_score.bin")

icon = pygame.image.load('imgs/icon.png')

pygame.display.set_caption('Space Shooter')

# Load sounds
try:
    pew_sound = pygame.mixer.Sound('sounds/pew.wav')
    ah_sound = pygame.mixer.Sound('sounds/ah.wav')
except:
    pew_sound = None
    ah_sound = None
    print("Warning: Could not load sound files")

asteroids_imgs = [
    pygame.image.load('imgs/asteroid0.png'),
    pygame.image.load('imgs/asteroid1.png'),
    pygame.image.load('imgs/asteroid2.png')
    ]


player_img = pygame.image.load('imgs/shooter.png')
player_img = pygame.transform.scale_by(player_img, 0.1)

gameover = pygame.image.load('imgs/gameover.png')

game_o = False

bullets = []  # List for multiple bullets

on = True

# Network settings
is_multiplayer = False
is_server = False
is_client = False
server_socket = None
client_socket = None
client_conn = None
network_thread = None
PORT = 5555
HOST = 'localhost'
connected = False
player_id = 0  # 0 for server player, 1 for client player
remote_player = None
remote_bullets = []  # Changed to list for multiple bullets
remote_score = 0
remote_life = 5
network_frame_counter = 0
NETWORK_UPDATE_INTERVAL = 1  # Update every frame for smoothness
prev_life = 1  # Track previous life for death sound
shoot_cooldown = 0  # Cooldown for shooting (frames)
SHOOT_COOLDOWN_TIME = 1  # Frames between shots (allows very rapid fire)

# ----display-----:
w, h = 650, 650
screen = pygame.display.set_mode((w, h))
pygame.display.set_icon(icon)


# //----------------Game_Settings-----------------------------:
n_of_asteroids = 15
asteroid_speed = 0.1
life = 1
max_score = 0

try:
    font = pygame.font.Font(".fonts/ARCADE.otf", 70)
except FileNotFoundError:
    font = pygame.font.Font(None, 70)
text = font.render('Hello', False, (255, 255, 255))


#----------file_handling-----------:        #aka boring stuff
if not os.path.exists(arquivo):

    with open(arquivo, "wb") as f:
        f.write((0).to_bytes(4, "big"))

# Leitura
with open(arquivo, "rb") as f:
    data = f.read(4)  # ler 4 bytes
    max_score = int.from_bytes(data, "big")
#...........................................................................................................

#-------------funcions-----:

def blit_rotate_center(s, img, top_l, angle, blit=True):
    rotated_img = pygame.transform.rotate(img, angle)
    new_rect = rotated_img.get_rect(center=img.get_rect(topleft=top_l).center)
    if blit:
        s.blit(rotated_img, new_rect.topleft)
    return new_rect.center

def reset_game():
    global player1, bullets, asteroids, score, life, game_o, remote_player, remote_bullets, remote_score, remote_life, prev_life
    if is_multiplayer:
        if player_id == 0:
            player1 = shooter(w//4, h//2)
        else:
            player1 = shooter(3*w//4, h//2)
    else:
        player1 = shooter()
    bullets = []  # Reset bullets list
    if is_server or not is_multiplayer:
        # Use seed for deterministic asteroid generation
        random.seed(42)
        asteroids = [Asteroid() for _ in range(n_of_asteroids)]
    elif is_client:
        # Client will receive asteroids from server
        asteroids = []
    score = 0
    life = 1
    game_o = False
    if is_multiplayer:
        remote_player = shooter()
        remote_bullets = []  # Reset remote bullets list
        remote_score = 0
        remote_life = 1
    prev_life = life

def start_server():
    global server_socket, client_conn, connected, is_server, is_multiplayer
    is_server = True
    is_multiplayer = True
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    # Bind to all interfaces (0.0.0.0) to accept connections from other PCs
    server_socket.bind(('0.0.0.0', PORT))
    server_socket.listen(1)
    print(f"Server started on port {PORT}. Waiting for client...")
    print(f"Connect using your local IP address (e.g., 192.168.x.x)")
    client_conn, addr = server_socket.accept()
    client_conn.setblocking(False)
    client_conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    connected = True
    print(f"Client connected from {addr}")
    return True

def start_client(host='localhost'):
    global client_socket, connected, is_client, is_multiplayer, HOST
    is_client = True
    is_multiplayer = True
    HOST = host
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    try:
        client_socket.connect((HOST, PORT))
        client_socket.setblocking(False)
        connected = True
        print(f"Connected to server at {HOST}:{PORT}")
        return True
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

def send_game_state():
    global player1, bullets, asteroids, score, life
    if not connected:
        return
    
    try:
        # Send only active bullets (not off screen)
        active_bullets = [b.to_dict() for b in bullets if not b.d_off_screen()]
        state = {
            'player': player1.to_dict(),
            'bullets': active_bullets,
            'asteroids': [a.to_dict() for a in asteroids] if is_server else None,
            'score': score,
            'life': life
        }
        data = pickle.dumps(state)
        if is_server and client_conn:
            client_conn.sendall(len(data).to_bytes(4, 'big') + data)
        elif is_client and client_socket:
            client_socket.sendall(len(data).to_bytes(4, 'big') + data)
    except (ConnectionError, OSError):
        pass  # Connection lost
    except Exception:
        pass  # Other errors

def receive_game_state():
    global remote_player, remote_bullets, asteroids, remote_score, remote_life, connected, on
    if not connected:
        return False
    
    try:
        if is_server and client_conn:
            sock = client_conn
        elif is_client and client_socket:
            sock = client_socket
        else:
            return False
        
        # Try to receive data (non-blocking)
        try:
            # Read length (non-blocking, returns immediately)
            length_bytes = sock.recv(4)
            if len(length_bytes) < 4:
                return False
            length = int.from_bytes(length_bytes, 'big')
            
            # Read message data (non-blocking)
            data = sock.recv(length)
            if len(data) < length:
                return False  # Partial message, try again next frame
            
            state = pickle.loads(data)
            
            if remote_player:
                remote_player.from_dict(state['player'])
            
            # Update remote bullets list
            remote_bullet_data = state.get('bullets', [])
            prev_remote_count = len(remote_bullets)
            
            # Create or update remote bullets
            remote_bullets = []
            for bullet_data in remote_bullet_data:
                bullet = Bullet()
                bullet.from_dict(bullet_data)
                remote_bullets.append(bullet)
            
            # Play sound when new bullets appear
            if pew_sound and len(remote_bullets) > prev_remote_count:
                pew_sound.play()
            
            # Server syncs asteroids to client
            if is_client and 'asteroids' in state:
                if len(asteroids) != len(state['asteroids']):
                    asteroids = [Asteroid() for _ in range(len(state['asteroids']))]
                for i, ast_data in enumerate(state['asteroids']):
                    asteroids[i].from_dict(ast_data)
            
            remote_score = state.get('score', 0)
            remote_life = state.get('life', 1)
            return True
        except BlockingIOError:
            return False
    except (ConnectionError, OSError):
        connected = False
        on = False  # Disconnect
        return False
    except Exception:
        return False

def show_menu():
    global is_multiplayer, is_server, is_client, HOST
    menu_active = True
    clock = pygame.time.Clock()
    
    while menu_active:
        screen.fill((0, 0, 10))
        title = font.render('Space Shooter', False, (255, 255, 255))
        single_text = font.render('1 - Single Player', False, (255, 255, 255))
        server_text = font.render('2 - Host Server', False, (255, 255, 255))
        client_text = font.render('3 - Join Game', False, (255, 255, 255))
        
        screen.blit(title, (w//2 - title.get_width()//2, 100))
        screen.blit(single_text, (w//2 - single_text.get_width()//2, 250))
        screen.blit(server_text, (w//2 - server_text.get_width()//2, 320))
        screen.blit(client_text, (w//2 - client_text.get_width()//2, 390))
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    is_multiplayer = False
                    return True
                elif event.key == pygame.K_2:
                    if start_server():
                        return True
                elif event.key == pygame.K_3:
                    # Simple input for server IP
                    input_active = True
                    ip_text = "localhost"
                    while input_active:
                        screen.fill((0, 0, 10))
                        prompt = font.render('Enter server IP:', False, (255, 255, 255))
                        ip_display = font.render(ip_text, False, (255, 255, 255))
                        screen.blit(prompt, (w//2 - prompt.get_width()//2, 250))
                        screen.blit(ip_display, (w//2 - ip_display.get_width()//2, 320))
                        pygame.display.flip()
                        
                        for ev in pygame.event.get():
                            if ev.type == pygame.QUIT:
                                return False
                            if ev.type == pygame.KEYDOWN:
                                if ev.key == pygame.K_RETURN:
                                    if start_client(ip_text):
                                        return True
                                    input_active = False
                                elif ev.key == pygame.K_BACKSPACE:
                                    ip_text = ip_text[:-1]
                                else:
                                    if ev.unicode.isprintable():
                                        ip_text += ev.unicode
                        clock.tick(60)
        
        clock.tick(60)
    return True

#-----------classes----------this took a while:

class shooter:
    def __init__(self, start_x=None, start_y=None):
        self.x = start_x if start_x is not None else w//2
        self.y = start_y if start_y is not None else h//2
        self.speed = 0
        self.x_speed = 0
        self.y_speed = 0
        self.dir = 10
        self.rad = math.radians(self.dir)
        self.acc = 0.005
        self.hitbox = pygame.Rect(self.x, self.y, round(player_img.get_width()), round(player_img.get_height()))
    
    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'speed': self.speed,
            'x_speed': self.x_speed,
            'y_speed': self.y_speed,
            'dir': self.dir
        }
    
    def from_dict(self, data):
        self.x = data['x']
        self.y = data['y']
        self.speed = data['speed']
        self.x_speed = data['x_speed']
        self.y_speed = data['y_speed']
        self.dir = data['dir']
        self.rad = math.radians(self.dir)
        self.hitbox = pygame.Rect(self.x, self.y, round(player_img.get_width()), round(player_img.get_height()))

    def draw(self, color_offset=0):
        blit_rotate_center(screen, player_img, (self.x, self.y), -self.dir)
        self.hitbox = pygame.Rect(self.x, self.y, round(player_img.get_width()), round(player_img.get_height()))
        

    def move_f(self):
        self.rad = math.radians(self.dir)
        self.x_speed = math.cos(self.rad) * self.speed
        self.y_speed = math.sin(self.rad) * self.speed
        self.x += self.x_speed
        self.y += self.y_speed

    def slow_down(self):
        if self.speed > 0:
            self.speed -= self.acc * 2

    def accelerate(self):
        if self.speed < 2:
            self.speed += self.acc

    def tp(self):
        if self.x < 0:
            self.x = w
        elif self.x > w:
            self.x = 0
        elif self.y < 0:
            self.y = h
        elif self.y > h:
            self.y = 0

    def get_tip_pos(self):
        img_w, img_h = player_img.get_size()
        dx = img_w / 2
        dy = 0 
        center = blit_rotate_center(
            screen, player_img, (self.x, self.y), -self.dir, blit=False)
        tip_x = center[0] + dx * math.cos(self.rad) - dy * math.sin(self.rad)
        tip_y = center[1] + dx * math.sin(self.rad) + dy * math.cos(self.rad)
        return tip_x, tip_y


player1 = shooter()
remote_player = None

score = 0
remote_score = 0
remote_life = 1

class Bullet:
    def __init__(self, shooter_obj=None):
        if shooter_obj:
            self.x, self.y = shooter_obj.get_tip_pos()
            self.rad = math.radians(shooter_obj.dir)
        else:
            self.x, self.y = w//2, h//2
            self.rad = 0
        self.x_speed = math.cos(self.rad) * 2
        self.y_speed = math.sin(self.rad) * 2
        self.hitbox = pygame.Rect(self.x, self.y, 5, 5)
    
    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'x_speed': self.x_speed,
            'y_speed': self.y_speed,
            'rad': self.rad
        }
    
    def from_dict(self, data):
        self.x = data['x']
        self.y = data['y']
        self.x_speed = data['x_speed']
        self.y_speed = data['y_speed']
        self.rad = data['rad']
        self.hitbox = pygame.Rect(self.x, self.y, 5, 5)
        
    def move_f(self):
        self.x += self.x_speed
        self.y += self.y_speed
        self.hitbox = pygame.Rect(self.x, self.y, 5, 5)

    def draw(self, color=(255, 255, 255)):
        bullet = pygame.Rect(self.x, self.y, 5, 5)
        pygame.draw.rect(screen, color, bullet)

    def d_off_screen(self):
        if self.x < 0 or self.x > w or self.y < 0 or self.y > h:
            return True
        return False




class Asteroid:
    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
        self.size = random.uniform(0.1, 0.5)
        self.x, self.y, self.x_speed, self.y_speed = random.randint(0, w), random.randint(0, h), random.uniform(-asteroid_speed, asteroid_speed), random.uniform(-asteroid_speed, asteroid_speed)
        self.image = pygame.transform.scale_by(random.choice(asteroids_imgs), self.size)
        self.hitbox = pygame.Rect(self.x, self.y, round(self.image.get_width()), round(self.image.get_height()))
        self.img_index = random.randint(0, len(asteroids_imgs) - 1)
    
    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'x_speed': self.x_speed,
            'y_speed': self.y_speed,
            'size': self.size,
            'img_index': self.img_index
        }
    
    def from_dict(self, data):
        self.x = data['x']
        self.y = data['y']
        self.x_speed = data['x_speed']
        self.y_speed = data['y_speed']
        self.size = data['size']
        self.img_index = data['img_index']
        self.image = pygame.transform.scale_by(asteroids_imgs[self.img_index], self.size)
        self.hitbox = pygame.Rect(self.x, self.y, round(self.image.get_width()), round(self.image.get_height()))
    def spawn(self, seed=None):
        if seed is not None:
            random.seed(seed)
        self.size = random.uniform(0.1, 0.5)
        self.img_index = random.randint(0, len(asteroids_imgs) - 1)
        self.image = pygame.transform.scale_by(asteroids_imgs[self.img_index], self.size)

        side = random.choice(["top", "bottom", "left", "right"])
            
        if side == "top":
            self.x = random.randint(0, w)
            self.y = 0
        elif side == "bottom":
            self.x = random.randint(0, w)
            self.y = h
        elif side == "left":
            self.x = 0
            self.y = random.randint(0, h)
        else:  # right
            self.x = w
            self.y = random.randint(0, h)
            
        self.x_speed = random.uniform(-asteroid_speed, asteroid_speed)
        self.y_speed = random.uniform(-asteroid_speed, asteroid_speed)


    def draw(self):
        screen.blit(self.image, (self.x, self.y))
        self.hitbox = pygame.Rect(self.x, self.y, round(self.image.get_width()), round(self.image.get_height()))
        self.x += self.x_speed
        self.y += self.y_speed
        if self.x < 0 or self.x > w:
            self.spawn()
        elif self.y < 0 or self.y > h:
            self.spawn()



asteroids = []
for i in range(n_of_asteroids):      #spawn asteroids
    asteroids.append(Asteroid())

# Initialize multiplayer - check command line arguments
if len(sys.argv) > 1:
    mode = sys.argv[1].lower()
    if mode == 'server':
        if start_server():
            player_id = 0
            reset_game()
        else:
            on = False
    elif mode == 'client':
        host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
        if start_client(host):
            player_id = 1
            reset_game()
            time.sleep(0.5)  # Wait for initial state from server
        else:
            on = False
    else:
        # Single player
        is_multiplayer = False
        reset_game()
else:
    # Show menu if no arguments
    if show_menu():
        if is_multiplayer:
            player_id = 0 if is_server else 1
            reset_game()
            if is_client:
                # Wait for initial state from server
                time.sleep(0.5)
        else:
            reset_game()
    else:
        on = False

#---main loop---:
clock = pygame.time.Clock()

while on:
    if game_o:
        #---------if you can't play a simple game this happens--------:
        screen.fill((0, 0, 10))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                on = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    life = 1
                    reset_game()
        
        screen.blit(gameover, (0, 0))
        text = font.render((f'max score: {max_score}'), False, (255, 5, 5))
        screen.blit(text, (0, -25))
        pygame.display.flip()
    else:

        #----------------draw_things-------------:
        screen.fill((0, 0, 10))
        if is_multiplayer:
            text = font.render((f'P{player_id+1} Score: {score}  Health:{life} | P{2-player_id} Score: {remote_score}  Health:{remote_life}'), False, (255, 255, 255))
        else:
            text = font.render((f'score: {score}         health:{life}'), False, (255, 255, 255))
        screen.blit(text, (0, -25))
        
        # Network communication (every N frames to reduce lag)
        if is_multiplayer:
            network_frame_counter += 1
            if network_frame_counter >= NETWORK_UPDATE_INTERVAL:
                network_frame_counter = 0
                send_game_state()
            receive_game_state()  # Always try to receive (non-blocking)
        
        #----------asteroids----------:
                                                #this part took 2h but lets pretend it didn't 
        for asteroid in asteroids:
            # Local player bullet collision
            for bullet in bullets[:]:  # Use slice to avoid modification during iteration
                if bullet.hitbox.colliderect(asteroid.hitbox):
                    asteroid.spawn()
                    score += int(asteroid.size*100)
                    bullets.remove(bullet)
            
            # Remote player bullet collision (server only)
            if is_server:
                for bullet in remote_bullets[:]:
                    if bullet.hitbox.colliderect(asteroid.hitbox):
                        asteroid.spawn()
                        remote_score += int(asteroid.size*100)
                        remote_bullets.remove(bullet)
            
            # Local player collision
            if asteroid.hitbox.colliderect(player1.hitbox):
                life -= 1
                # Play death sound when life decreases
                if ah_sound and life < prev_life:
                    ah_sound.play()
                asteroid.spawn()
            
            # Remote player collision (server only)
            if is_server and remote_player and asteroid.hitbox.colliderect(remote_player.hitbox):
                remote_life -= 1
                asteroid.spawn()
            
            asteroid.draw()

        #bullets         :cool stuf right here:
        # Update and draw local bullets
        for bullet in bullets[:]:  # Use slice to avoid modification during iteration
            if not bullet.d_off_screen():
                bullet.move_f()
                bullet.draw((255, 255, 255))
                
                # Check if bullet hits remote player
                if is_multiplayer and remote_player and bullet.hitbox.colliderect(remote_player.hitbox):
                    remote_life -= 1
                    bullets.remove(bullet)
                    # Play death sound for remote player
                    if ah_sound:
                        ah_sound.play()
            else:
                bullets.remove(bullet)
        
        # Check if remote bullets hit local player
        if is_multiplayer:
            for bullet in remote_bullets[:]:
                if bullet.hitbox.colliderect(player1.hitbox):
                    life -= 1
                    remote_bullets.remove(bullet)
                    # Play death sound when hit
                    if ah_sound and life < prev_life:
                        ah_sound.play()
        
        #event_handeling: 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                on = False
        #------key presses----:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and shoot_cooldown <= 0:
            # Create new bullet
            new_bullet = Bullet(player1)
            bullets.append(new_bullet)
            shoot_cooldown = SHOOT_COOLDOWN_TIME
            # Play shoot sound
            if pew_sound:
                pew_sound.play()
        
        # Update shoot cooldown
        if shoot_cooldown > 0:
            shoot_cooldown -= 1
        if keys[pygame.K_UP]:
            player1.accelerate()
        if not keys[pygame.K_UP]:
            player1.slow_down()
        if keys[pygame.K_LEFT]:
            player1.dir -= 0.5  # Increased turning speed
        elif keys[pygame.K_RIGHT]:
            player1.dir += 0.5  # Increased turning speed
        #-------idk what to call this---:
        player1.move_f()
        player1.tp()
        player1.draw()
        
        # Draw remote player and bullets (after local player so it's on top)
        if is_multiplayer and remote_player:
            remote_player.draw()
            for bullet in remote_bullets[:]:  # Use slice to avoid modification during iteration
                if not bullet.d_off_screen():
                    bullet.move_f()
                    bullet.draw((255, 100, 100))  # Different color for remote bullet
                else:
                    remote_bullets.remove(bullet)
        #score and lives:
        if life <= 0:
            game_o = True
        if is_server and remote_life <= 0:
            game_o = True
        if score >= max_score:
            max_score = score
        if is_multiplayer and remote_score >= max_score:
            max_score = remote_score
        
        # Update previous states for sound detection
        prev_life = life

        pygame.display.flip()
        clock.tick(60)  # 60 FPS

#save max score:


os.makedirs(pasta, exist_ok=True)
max_score = max_score.to_bytes(4, 'big')                        #more boring stuff
with open(arquivo, "wb") as f:
    f.write(max_score)

# Cleanup network connections
if is_server and server_socket:
    try:
        if client_conn:
            client_conn.close()
        server_socket.close()
    except:
        pass
elif is_client and client_socket:
    try:
        client_socket.close()
    except:
        pass

pygame.quit()

#it's currently 23:21
#now it´s midnight
