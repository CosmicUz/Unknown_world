import socket
import threading
import time

class MultiplayerSession:
    def __init__(self, max_players=4):
        self.max_players = max_players
        self.players = [None] * max_players
        self.lock = threading.Lock()

    def add_player(self, player_info):
        with self.lock:
            print(f"[DEBUG][MultiplayerSession] add_player called with: {player_info}")
            for i in range(1, self.max_players):
                if self.players[i] is None:
                    self.players[i] = player_info
                    print(f"[SESSION] Player added to slot {i}: {player_info}")
                    return i
            print("[SESSION] No slot available for new player")
            return -1

    def remove_player(self, slot_idx):
        with self.lock:
            print(f"[DEBUG][MultiplayerSession] remove_player called for slot {slot_idx}")
            if 0 < slot_idx < self.max_players:
                print(f"[SESSION] Player removed from slot {slot_idx}")
                self.players[slot_idx] = None

    def get_state(self):
        with self.lock:
            print(f"[DEBUG][MultiplayerSession] get_state called. Current slots: {self.players}")
            return [p for p in self.players]

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"[NETWORK] Detected local IP: {ip}")
        return ip
    except Exception as e:
        print(f"[NETWORK] Could not determine local IP: {e}")
        return "127.0.0.1"

class HostServer:
    def __init__(self, port=7777, max_players=4):
        self.session = MultiplayerSession(max_players)
        self.port = port
        self.sock = None
        self.is_running = False
        self.thread = None
        self.connections = []

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", self.port))
        self.sock.listen(self.session.max_players - 1)
        self.is_running = True
        print(f"[NETWORK] Host starting on port {self.port}...")
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        print(f"[NETWORK] Host started. Waiting for clients...")

    def _accept_loop(self):
        while self.is_running:
            try:
                print("[NETWORK] Accepting clients...")
                conn, addr = self.sock.accept()
                print(f"[NETWORK] Client connected from {addr}")
                self.connections.append(conn)
                threading.Thread(target=self._client_handler, args=(conn, addr), daemon=True).start()
            except Exception as e:
                print(f"[NETWORK] Accept error: {e}")
            time.sleep(0.2)

    def _client_handler(self, conn, addr):
        try:
            print(f"[NETWORK] Handling new client {addr}")
            name = conn.recv(64).decode("utf-8")
            print(f"[NETWORK] Received player name: {name}")
            slot_idx = self.session.add_player({"name": name, "ip": addr[0]})
            print(f"[DEBUG][HostServer] add_player returned slot_idx={slot_idx}")
            if slot_idx == -1:
                conn.sendall(b"FULL")
                print(f"[NETWORK] Session full, client {addr} rejected.")
                conn.close()
                return
            else:
                print(f"[NETWORK] Client {name} accepted into slot {slot_idx}")
                conn.sendall(f"SLOT:{slot_idx}".encode("utf-8"))
                self.broadcast_state()
            while self.is_running:
                try:
                    data = conn.recv(128)
                except Exception as e:
                    print(f"[NETWORK] Error reading from client {addr}: {e}")
                    break
                if not data:
                    print(f"[NETWORK] No data from client {addr}, disconnecting.")
                    break
                msg = data.decode("utf-8")
                print(f"[NETWORK] Received from {addr}: {msg}")
                time.sleep(0.1)
            self.session.remove_player(slot_idx)
            self.broadcast_state()
            conn.close()
            print(f"[NETWORK] Client {addr} disconnected")
        except Exception as e:
            print(f"[NETWORK] Client handler error: {e}")

    def broadcast_state(self):
        state = self.session.get_state()
        state_str = str(state)
        print(f"[NETWORK] Broadcasting state: {state_str}")
        for conn in self.connections:
            try:
                conn.sendall(f"STATE:{state_str}".encode("utf-8"))
                time.sleep(0.05)
            except Exception:
                print("[NETWORK] Error broadcasting to a client.")

    def stop(self):
        print("[NETWORK] Stopping host server...")
        self.is_running = False
        if self.sock:
            self.sock.close()
        for conn in self.connections:
            try:
                conn.close()
            except:
                pass
        print("[NETWORK] Host stopped.")

class Client:
    def __init__(self, host_ip, port=7777, name="P2"):
        self.host_ip = host_ip
        self.port = port
        self.name = name
        self.sock = None
        self.slot_idx = None
        self.thread = None
        self.is_connected = False
        self.last_slots = None

    def connect(self):
        print(f"[NETWORK] Connecting to host {self.host_ip}:{self.port} as {self.name}")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.settimeout(4)
            self.sock.connect((self.host_ip, self.port))
            print("[NETWORK] TCP connect() successful")
            self.sock.sendall(self.name.encode("utf-8"))
            print(f"[NETWORK] Player name '{self.name}' sent to host")
            reply = self.sock.recv(64).decode("utf-8")
            print(f"[NETWORK] Host replied: {reply}")
            if reply.startswith("SLOT:"):
                self.slot_idx = int(reply.split(":")[1])
                self.is_connected = True
                print(f"[NETWORK] Connected to host as slot {self.slot_idx}")
                self.thread = threading.Thread(target=self._listen_loop, daemon=True)
                self.thread.start()
            else:
                print("[NETWORK] Host is full or rejected connection.")
        except Exception as e:
            print(f"[NETWORK] Connection error: {e}")
            self.is_connected = False
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
        time.sleep(0.5)

    def _listen_loop(self):
        try:
            print("[NETWORK] Starting listen loop for client...")
            while self.is_connected:
                try:
                    data = self.sock.recv(1024)
                except Exception as e:
                    print(f"[NETWORK] Listen loop receive error: {e}")
                    break
                if not data:
                    print("[NETWORK] Server disconnected.")
                    break
                msg = data.decode("utf-8")
                print(f"[NETWORK] Received from server: {msg}")
                if msg.startswith("STATE:"):
                    state = eval(msg[6:])  # List of slot dicts
                    print(f"[NETWORK] Session slots (client side): {state}")
                    self.last_slots = state  # Client can update its session here!
                time.sleep(0.1)
        except Exception as e:
            print(f"[NETWORK] Listen error: {e}")
        finally:
            self.is_connected = False
            if self.sock:
                self.sock.close()
            print("[NETWORK] Disconnected from host.")

    def disconnect(self):
        print("[NETWORK] Client disconnecting...")
        self.is_connected = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        print("[NETWORK] Client disconnected.")
