class Session:
    def __init__(self, max_players=4):
        self.max_players = max_players
        self.slots = [None] * max_players

    def add_host(self, name, ip="LOCAL"):
        self.slots[0] = {"name": name, "ip": ip, "role": "host"}
        return 0

    def add_client(self, name, ip="LOCAL"):
        for i in range(1, self.max_players):
            if self.slots[i] is None:
                self.slots[i] = {"name": name, "ip": ip, "role": "client"}
                return i
        return -1

    def remove_client(self, idx, compress=True):
        if idx <= 0 or idx >= self.max_players:
            return
        self.slots[idx] = None
        if compress:
            for i in range(idx + 1, self.max_players):
                if self.slots[i] is not None:
                    self.slots[i - 1] = self.slots[i]
                    self.slots[i] = None

    def remove_host(self):
        self.slots[0] = None

    def is_full(self):
        return all(self.slots)

    def get_state(self):
        return list(self.slots)

    def num_clients(self):
        return sum(1 for i in range(1, self.max_players) if self.slots[i] is not None)

    def num_players(self):
        return sum(1 for slot in self.slots if slot is not None)

    def update_from_network(self, net_slots):
        if not isinstance(net_slots, list):
            print("[Session] WARNING: Bad net_slots format:", net_slots)
            return

        if len(net_slots) != self.max_players:
            print("[Session] WARNING: Slot count mismatch.")
            return

        self.slots = list(net_slots)