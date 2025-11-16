import socket
import threading
import struct
import json
import random
import time
import traceback


def send_message(sock: socket.socket, obj: dict):
    try:
        data = json.dumps(obj).encode("utf-8")
        header = struct.pack("!I", len(data))
        sock.sendall(header + data)
    except Exception as e:
        raise e


def recv_all(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = b""
        try:
            chunk = sock.recv(n - len(buf))
        except:
            return b""
        if not chunk:
            return b""
        buf.extend(chunk)
    return bytes(buf)


def recv_message(sock: socket.socket):
    header = recv_all(sock, 4)
    if not header:
        return None
    size = struct.unpack("!I", header)[0]
    if size <= 0:
        return None
    payload = recv_all(sock, size)
    if not payload:
        return None
    try:
        return json.loads(payload.decode("utf-8"))
    except:
        return None


def find_open_port(start=7777, end=7787):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError as e:
                print(e)
    return None


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


class MultiplayerSession:
    def __init__(self, max_players=4):
        self.max_players = max_players
        self.players = [None] * max_players  # slot 0..max_players-1
        self.lock = threading.Lock()

    def add_player(self, info):
        with self.lock:
            for i in range(self.max_players):
                if self.players[i] is None:
                    self.players[i] = info
                    return i
            return -1

    def remove_player(self, idx):
        with self.lock:
            if 0 <= idx < self.max_players:
                self.players[idx] = None

    def get_state(self):
        with self.lock:
            return list(self.players)



class HostServer:
    def __init__(self, port=None, max_players=4, bind_ip=""):
        self.session = MultiplayerSession(max_players)
        self.port = port if port else find_open_port()
        if port:
            self.port = port
        else:
            self.port = find_open_port()
        if not self.port:
            raise RuntimeError("Barcha portlar band (7777-7787)! Server ochilmaydi.")
        self.bind_ip = bind_ip
        self.sock = None
        self.is_running = False
        self.connections = {}
        self.conn_lock = threading.Lock()
        self.accept_thread = None
        self.client_threads = []

    def start(self):
        try:
            print(f"[HOST] Starting on {self.bind_ip or '0.0.0.0'}:{self.port}")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.bind_ip, self.port))
            self.sock.listen(32)
            self.sock.settimeout(1.0)
            self.is_running = True
            print(f"[HOST] is_running: {self.is_running}, sock: {self.sock}")
            self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.accept_thread.start()
            print(f"[HOST] Listening. Share this with players: {get_local_ip()}:{self.port}")
        except Exception as e:
            traceback.print_exc()
            print(f"[HOST] Failed to start: {e}")
            self.is_running = False

    def _accept_loop(self):
        while self.is_running:
            try:
                conn, addr = self.sock.accept()
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"[HOST] Accept error: {e}")
                continue

            conn.settimeout(10)
            t = threading.Thread(target=self._client_handler, args=(conn, addr), daemon=True)
            t.start()
            self.client_threads.append(t)

    def _client_handler(self, conn, addr):
        slot = None
        try:
            join = recv_message(conn)
            if not join or join.get("type") != "JOIN":
                conn.close()
                return

            name = join.get("name", "Player")

            slot = self.session.add_player({"name": name, "ip": addr[0]})
            if slot == -1:
                send_message(conn, {"type": "REJECT", "reason": "FULL"})
                conn.close()
                return

            with self.conn_lock:
                self.connections[slot] = (conn, addr)

            send_message(conn, {"type": "ACCEPT", "slot": slot})
            self.broadcast_state()

            while self.is_running:
                msg = recv_message(conn)
                if msg is None:
                    break

                if msg.get("type") == "DISCONNECT":
                    break


        except Exception as e:
            print(f"[HOST] Client error: {e}")

        finally:
            if slot is not None:
                self.session.remove_player(slot)
                with self.conn_lock:
                    self.connections.pop(slot, None)
                self.broadcast_state()
            try:
                conn.close()
            except:
                pass

    def broadcast_state(self):
        msg = {"type": "STATE", "payload": self.session.get_state()}
        bad = []
        with self.conn_lock:
            for slot, (conn, addr) in self.connections.items():
                try:
                    send_message(conn, msg)
                except:
                    bad.append(slot)
            for s in bad:
                self.connections.pop(s, None)
                self.session.remove_player(s)

    def stop(self):
        print("[HOST] Stopping server...")
        self.is_running = False

        try:
            self.sock.close()
        except:
            pass

        with self.conn_lock:
            for slot, (conn, addr) in self.connections.items():
                try:
                    send_message(conn, {"type": "SERVER_SHUTDOWN"})
                except:
                    pass
                try:
                    conn.close()
                except:
                    pass
            self.connections.clear()

        time.sleep(0.2)
        print("[HOST] Server stopped.")


class Client:
    def __init__(self, host_ip, port, name="Player"):
        self.host_ip = host_ip
        self.port = port
        self.name = name
        self.sock = None
        self.slot = None
        self.is_connected = False
        self.listen_thread = None
        self.last_state = None

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.host_ip, self.port))

            send_message(self.sock, {"type": "JOIN", "name": self.name})

            reply = recv_message(self.sock)
            if not reply:
                print("[CLIENT] No reply from server.")
                return False

            if reply.get("type") != "ACCEPT":
                print("[CLIENT] Rejected:", reply.get("reason"))
                return False

            self.slot = reply["slot"]
            self.is_connected = True

            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()

            print(f"[CLIENT] Connected as slot {self.slot}")
            return True

        except Exception as e:
            print(f"[CLIENT] Connection error: {e}")
            return False

    def _listen_loop(self):
        while self.is_connected:
            msg = recv_message(self.sock)
            if msg is None:
                break

            t = msg.get("type")

            if t == "STATE":
                self.last_state = msg.get("payload")
                print("[CLIENT] State:", self.last_state)

            elif t == "SERVER_SHUTDOWN":
                print("[CLIENT] Server shutting down")
                break

        self.disconnect()

    def send_action(self, data: dict):
        if not self.is_connected:
            return
        try:
            send_message(self.sock, data)
        except:
            self.disconnect()

    def disconnect(self):
        if not self.is_connected:
            return
        self.is_connected = False

        try:
            send_message(self.sock, {"type": "DISCONNECT"})
        except:
            pass
        try:
            self.sock.close()
        except:
            pass

        print("[CLIENT] Disconnected")
