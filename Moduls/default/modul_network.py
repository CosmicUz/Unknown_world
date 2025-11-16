def sync_state_to_clients(game, host_server):
    state = get_game_state_payload(game)
    msg = {"type": "GAME_STATE", "payload": state}
    with host_server.conn_lock:
        for slot, (conn, addr) in host_server.connections.items():
            try:
                host_server.session.players[slot]['last_sync'] = game.game_time if 'last_sync' in host_server.session.players[slot] else 0
                host_server.session.players[slot]['last_sync'] = game.game_time
                from network import send_message
                send_message(conn, msg)
            except Exception as e:
                print(f"[modul_network] Sync error: {e}")


def receive_state_from_host(game, client):
    state = client.last_state
    if state and isinstance(state, dict) and "players" in state:
        apply_state_to_game(game, state)


def get_game_state_payload(game):
    return {
        "players": [
            {
                "id": p.id,
                "position": [float(p.position.x), float(p.position.y)],
                "health": int(getattr(p, "health", 0)),
                "shield": int(getattr(p, "shield", 0)),
                "state": p.state.name if hasattr(p, "state") else "",
                "level": int(getattr(p, "level", 1)),
                "zombie_kills": int(getattr(p, "zombie_kills", 0)),
                "weapon_type": getattr(p, "weapon_type", "").name if hasattr(p, "weapon_type") else "PISTOL",
                "drone": getattr(p, "drone", None).level if (hasattr(p, "drone") and p.drone) else None,
            }
            for p in getattr(game, "players", [])
        ],
        "zombies": [
            {
                "position": [float(z.position.x), float(z.position.y)],
                "health": int(getattr(z, "health", 0)),
                "type": getattr(z, "type", "").value if hasattr(z, "type") else "Walker",
                "active": bool(getattr(z, "active", True)),
                "strength": int(getattr(z, "strength", 1)),
            }
            for z in getattr(game, "zombies", [])
        ],
        "bullets": [
            {
                "position": [float(b.position.x), float(b.position.y)],
                "active": bool(getattr(b, "active", True)),
                "player_id": int(getattr(b, "player_id", 0)),
                "damage": int(getattr(b, "damage", 0)),
            }
            for b in getattr(game, "bullets", [])
        ],
        "meta": {
            "game_time": int(getattr(game, "game_time", 0)),
            "current_day": int(getattr(game, "current_day", 1)),
            "is_night": bool(getattr(game, "is_night", False)),
            "zombie_strength": int(getattr(game, "zombie_strength", 1)),
            "zombies_killed": int(getattr(game, "zombies_killed", 0)),
        }
    }


def apply_state_to_game(game, state):
    if "players" in state:
        for pdata in state["players"]:
            player = next((p for p in game.players if p.id == pdata["id"]), None)
            if player:
                px, py = pdata.get("position", [player.position.x, player.position.y])
                player.position.x = float(px)
                player.position.y = float(py)
                player.health = int(pdata.get("health", player.health))
                player.shield = int(pdata.get("shield", player.shield))
                if hasattr(player, "state"):
                    try: player.state = getattr(type(player.state), pdata.get("state", "ALIVE"))
                    except: pass
                player.level = int(pdata.get("level", player.level))
                player.zombie_kills = int(pdata.get("zombie_kills", player.zombie_kills))
                if hasattr(player, "weapon_type"):
                    try: player.weapon_type = getattr(type(player.weapon_type), pdata.get("weapon_type", "PISTOL"))
                    except: pass
                if player.drone and isinstance(pdata.get("drone", None), int):
                    player.drone.level = pdata["drone"]

    if "zombies" in state:
        for zdata in state["zombies"]:
            zpos = zdata.get("position", None)
            zombie = next((z for z in game.zombies if [z.position.x, z.position.y] == zpos), None)
            if zombie:
                zombie.health = int(zdata.get("health", zombie.health))
                zombie.active = bool(zdata.get("active", zombie.active))
                zombie.strength = int(zdata.get("strength", zombie.strength))
                if hasattr(zombie, "type"):
                    try: zombie.type = getattr(type(zombie.type), zdata.get("type", zombie.type.value))
                    except: pass

    if "bullets" in state:
        for bdata in state["bullets"]:
            bpos = bdata.get("position", None)
            bullet = next((b for b in game.bullets if [b.position.x, b.position.y] == bpos), None)
            if bullet:
                bullet.active = bool(bdata.get("active", bullet.active))
                bullet.damage = int(bdata.get("damage", bullet.damage))

    if "meta" in state:
        meta = state["meta"]
        game.game_time = int(meta.get("game_time", game.game_time))
        game.current_day = int(meta.get("current_day", game.current_day))
        game.is_night = bool(meta.get("is_night", game.is_night))
        game.zombie_strength = int(meta.get("zombie_strength", game.zombie_strength))
        game.zombies_killed = int(meta.get("zombies_killed", game.zombies_killed))
