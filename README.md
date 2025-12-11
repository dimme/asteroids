# Space Shooter Game

A multiplayer space shooter game built with Pygame. Battle asteroids and compete with friends in local or network multiplayer mode!

## Features

- Single player mode
- Multiplayer mode (server/client architecture)
- Real-time synchronization of players, bullets, and asteroids
- Sound effects for shooting and taking damage
- Persistent high score tracking

## Requirements

- Python 3.x
- Pygame library (`pip install pygame`)
- NumPy (`pip install numpy`)

## Controls

- **Arrow Up**: Accelerate
- **Arrow Left/Right**: Rotate ship
- **Space**: Shoot (hold for rapid fire)
- **R**: Restart (when game over)

## Installation

1. Clone or download this repository
2. Navigate to the `asteroids` directory
3. Install dependencies:
   ```bash
   pip install pygame numpy
   ```

## How to Play

### Single Player Mode

Simply run the game and press `1` at the menu:
```bash
cd asteroids
python3 asteroids.py
```

Or directly:
```bash
cd asteroids
python3 asteroids.py single
```

### Multiplayer Mode

The game supports multiplayer via network sockets. One player hosts the server, and another connects as a client.

#### Option 1: Same PC (Local Network)

**Terminal 1 - Start Server:**
```bash
cd asteroids
python3 asteroids.py server
```

**Terminal 2 - Start Client:**
```bash
cd asteroids
python3 asteroids.py client localhost
```

Or use the menu:
1. Run the game: `python3 asteroids.py`
2. First instance: Press `2` to host server
3. Second instance: Press `3` to join, then enter `localhost` as the server IP

#### Option 2: Different PCs (Network Play)

**On the Server PC:**

1. Find your local IP address:
   - **Linux/Mac**: Run `ip addr show` or `ifconfig` and look for your network interface IP (usually starts with 192.168.x.x or 10.x.x.x)
   - **Windows**: Run `ipconfig` and look for "IPv4 Address"

2. Start the server:
   ```bash
   cd asteroids
   python3 asteroids.py server
   ```
   
   The server will display: `Server started on localhost:5555. Waiting for client...`

3. **Important**: Make sure your firewall allows incoming connections on port 5555

**On the Client PC:**

1. Start the client with the server's IP address:
   ```bash
   cd asteroids
   python3 asteroids.py client <SERVER_IP_ADDRESS>
   ```
   
   For example, if the server IP is `192.168.1.100`:
   ```bash
   python3 asteroids.py client 192.168.1.100
   ```

2. The client will connect and you'll see: `Connected to server at <IP>:5555`

**Or use the menu:**
1. Run the game: `python3 asteroids.py`
2. Server: Press `2` to host
3. Client: Press `3` to join, then enter the server's IP address

### Network Configuration

- **Default Port**: 5555
- **Protocol**: TCP
- **Connection**: One server, one client (2 players total)

### Troubleshooting

**Connection Refused:**
- Make sure the server is running before the client tries to connect
- Check that both PCs are on the same network
- Verify the server IP address is correct
- Ensure firewall allows port 5555

**Can't See Other Player:**
- Wait a moment for the connection to establish
- Check that both players are in multiplayer mode
- Restart both server and client if issues persist

**High Latency:**
- Ensure both PCs are on a stable network connection
- Close other bandwidth-intensive applications
- For best results, use a wired connection instead of WiFi

## Game Modes

### Single Player
- Classic asteroid shooter
- Compete for high scores
- High score is saved locally

### Multiplayer
- Two players share the same game world
- Server player (P1) spawns on the left
- Client player (P2) spawns on the right
- Both players can see each other's bullets and movements
- Shared asteroid field
- Independent scores and lives

## Technical Details

- High scores are stored in `max_score.bin` (binary format)
- Game runs at 60 FPS
- Network updates every frame for smooth gameplay
- Server is authoritative for asteroids
- Both players send their positions and bullets

## License

Free to use and edit. Have fun!
