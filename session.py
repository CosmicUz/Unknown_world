class Session:
    def __init__(self, max_players=4):
        self.max_players = max_players
        self.slots = [{"id": 1, "role": "host", "name": "Host (P1)"}, None, None, None]

    def add_client(self, name):
        print(f"[DEBUG][Session] add_client called: {name}")
        for i in range(1, self.max_players):
            if self.slots[i] is None:
                self.slots[i] = {"id": i+1, "role": "client", "name": name}
                print(f"[DEBUG][Session] Client added to slot {i}")
                return i
        print("[DEBUG][Session] No slot available for new client")
        return -1

    def remove_client(self, idx):
        print(f"[DEBUG][Session] remove_client called for slot {idx}")
        if 1 <= idx < self.max_players:
            self.slots[idx] = None

    def is_full(self):
        return all(self.slots)

    def get_state(self):
        print(f"[DEBUG][Session] get_state called. Slots: {self.slots}")
        return [slot for slot in self.slots]

    def num_clients(self):
        return sum(1 for slot in self.slots[1:] if slot is not None)

    def update_from_network(self, slot_names):
        print(f"[DEBUG][Session] update_from_network called: {slot_names}")
        for i in range(self.max_players):
            if slot_names[i]:
                if isinstance(slot_names[i], dict):
                    self.slots[i] = slot_names[i]
                else:
                    role = "host" if i == 0 else "client"
                    self.slots[i] = {"id": i+1, "role": role, "name": slot_names[i]}
            else:
                self.slots[i] = None