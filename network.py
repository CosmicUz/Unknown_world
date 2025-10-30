import socket
import threading
import time
import json
import os
import subprocess
import random


def disable_firewall_temporarily():
    try:
        print("[FIREWALL] ⚠️ Temporarily disabling Windows Firewall...")
        os.system("netsh advfirewall set allprofiles state off")
        print("[FIREWALL] ✅ Firewall disabled temporarily.")
    except Exception as e:
        print(f"[FIREWALL] ❌ Failed to disable firewall: {e}")


def open_firewall_port(port: int):
    try:
        rule_name = f"PythonGame_{port}"
        check_rule = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"],
            capture_output=True, text=True
        )
        if "No rules match" not in check_rule.stdout:
            print(f"[FIREWALL] ✅ Rule already exists for port {port}")
            return

        os.system(
            f'netsh advfirewall firewall add rule name="{rule_name}" '
            f'dir=in action=allow protocol=TCP localport={port}'
        )
        print(f"[FIREWALL] ✅ Port {port} opened in Windows Firewall")
    except Exception as e:
        print(f"[FIREWALL] ⚠️ Failed to open port {port}: {e}")


def check_port_active(port: int):
    try:
        res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, encoding="utf-8")
        if f":{port}" in res.stdout:
            print(f"[NETWORK] ✅ Port {port} is active (LISTENING).")
            return True
        print(f"[NETWORK] ⚠️ Port {port} not found in netstat.")
        return False
    except Exception as e:
        print(f"[NETWORK] ⚠️ Could not check port {port}: {e}")
        return False


def find_open_port(start=7777, end=7787):
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                print(f"[NETWORK] ✅ Available port found: {port}")
                return port
        except OSError:
            continue
    raise RuntimeError("[NETWORK] ❌ No available ports in range 7777–7787")


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"[NETWORK] Local IP: {ip}")
        return ip
    except Exception:
        return "127.0.0.1"


class MultiplayerSession:
    def __init__(self, max_players=4):
        self.max_players = max_players
        self.players = [None] * max_players
        self.lock = threading.Lock()

    def add_player(self, player_info):
        with self.lock:
            print(f"[SESSION] add_player: {player_info}")
            for i in range(1, self.max_players):
                if self.players[i] is None:
                    self.players[i] = player_info
                    print(f"[SESSION] Player added to slot {i}: {player_info}")
                    return i
            print("[SESSION] No slot available.")
            return -1

    def remove_player(self, slot_idx):
        with self.lock:
            if 0 < slot_idx < self.max_players and self.players[slot_idx]:
                print(f"[SESSION] Removing player from slot {slot_idx}")
                self.players[slot_idx] = None

    def get_state(self):
        with self.lock:
            return [p for p in self.players]


class HostServer:
    def __init__(self, port=None, max_players=4):
        self.session = MultiplayerSession(max_players)
        self.port = port or find_open_port()
        self.sock = None
        self.is_running = False
        self.connections = {}
        self.thread = None

    def start(self):
        try:
            print(f"[HOST] 🟢 Starting server on port {self.port}...")

            try:
                open_firewall_port(self.port)
            except Exception as e:
                print(f"[HOST] ⚠️ Firewall rule open failed: {e}")

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                self.sock.bind(("", self.port))
                print(f"[HOST] ✅ Bound successfully on port {self.port}")
            except Exception as e:
                print(f"[HOST] ❌ Bind failed: {e}")
                self.port = random.randint(7800, 7900)
                print(f"[HOST] 🔁 Retrying on port {self.port}")
                self.sock.bind(("", self.port))

            self.sock.listen(self.session.max_players - 1)
            self.is_running = True

            local_ip = get_local_ip()
            print(f"[HOST] ✅ Server started on {local_ip}:{self.port}")
            print("[HOST] 🔊 Listening for incoming clients...")

            self.thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.thread.start()

        except Exception as e:
            print(f"[HOST] ❌ Failed to start server: {e}")

    def _accept_loop(self):
        print("[HOST] 🔁 Listening for clients...")
        while self.is_running:
            try:
                conn, addr = self.sock.accept()
                print(f"[HOST] New client: {addr}")
                threading.Thread(target=self._client_handler, args=(conn, addr), daemon=True).start()
            except Exception as e:
                print(f"[HOST] Accept error: {e}")
            time.sleep(0.1)

    def _client_handler(self, conn, addr):
        try:
            name = conn.recv(64).decode("utf-8")
            print(f"[HOST] Received name from {addr}: {name}")
            slot_idx = self.session.add_player({"name": name, "ip": addr[0]})

            if slot_idx == -1:
                conn.sendall(b"FULL")
                conn.close()
                return

            self.connections[slot_idx] = conn
            conn.sendall(f"SLOT:{slot_idx}".encode())
            self.broadcast_state()

            while self.is_running:
                try:
                    data = conn.recv(512)
                    if not data:
                        print(f"[HOST] {addr} disconnected.")
                        break
                    if data.decode() == "DISCONNECT":
                        break
                except Exception as e:
                    print(f"[HOST] Client error ({addr}): {e}")
                    break

            self.session.remove_player(slot_idx)
            self.connections.pop(slot_idx, None)
            conn.close()
            self.broadcast_state()
            print(f"[HOST] Client {addr} handler closed.")
        except Exception as e:
            print(f"[HOST] Handler exception: {e}")

    def broadcast_state(self):
        state = self.session.get_state()
        data = json.dumps({"type": "STATE", "payload": state})
        for slot_idx, conn in list(self.connections.items()):
            try:
                conn.sendall(data.encode())
            except Exception:
                print(f"[HOST] Lost connection to slot {slot_idx}, removing.")
                self.session.remove_player(slot_idx)
                del self.connections[slot_idx]

    def stop(self):
        self.is_running = False
        print("[HOST] Stopping server...")
        for conn in list(self.connections.values()):
            try:
                conn.close()
            except:
                pass
        if self.sock:
            self.sock.close()
        print("[HOST] Server stopped.")


class Client:
    def __init__(self, host_ip, port=7777, name="Player"):
        self.host_ip = host_ip
        self.port = port
        self.name = name
        self.sock = None
        self.slot_idx = None
        self.is_connected = False
        self.last_slots = None
        self.listen_thread = None

    def connect(self):
        try:
            print(f"[CLIENT] Connecting to {self.host_ip}:{self.port} as {self.name}")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.host_ip, self.port))
            self.sock.sendall(self.name.encode("utf-8"))
            reply = self.sock.recv(64).decode("utf-8")
            print(f"[CLIENT] Host reply: {reply}")

            if reply.startswith("SLOT:"):
                self.slot_idx = int(reply.split(":")[1])
                self.is_connected = True
                self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
                self.listen_thread.start()
                print(f"[CLIENT] ✅ Connected successfully as slot {self.slot_idx}")
            else:
                print("[CLIENT] ❌ Connection rejected or server full.")
                self.sock.close()
        except Exception as e:
            print(f"[CLIENT] ❌ Connection error: {e}")
            self.is_connected = False
            if self.sock:
                self.sock.close()

    def _listen_loop(self):
        print("[CLIENT] Listening for server messages...")
        while self.is_connected:
            try:
                data = self.sock.recv(2048)
                if not data:
                    print("[CLIENT] Server disconnected.")
                    break
                packet = json.loads(data.decode("utf-8"))
                if packet.get("type") == "STATE":
                    self.last_slots = packet["payload"]
                    print(f"[CLIENT] Updated session slots: {self.last_slots}")
            except Exception as e:
                print(f"[CLIENT] Listen error: {e}")
                break
        self.disconnect()

    def disconnect(self):
        print("[CLIENT] Disconnecting...")
        self.is_connected = False
        try:
            if self.sock:
                self.sock.sendall(b"DISCONNECT")
                self.sock.close()
        except:
            pass
        print("[CLIENT] Disconnected.")
