import random

def simple_calc_damage(attacker, defender, mult=1.0):
    """
    attacker, defender: dicts with keys 'attack', 'defense', 'crit_rate', 'crit_dmg', etc.
    """
    atk = attacker.get("attack", 100)
    defense = defender.get("defense", 50)
    base = atk * mult
    mitigation = defense / (defense + 1000)
    dmg = int(base * (1 - mitigation))
    # crit
    if random.random() < attacker.get("crit_rate", 0.05):
        dmg = int(dmg * attacker.get("crit_dmg", 1.5))
    return max(0, dmg)

def battle(team_chars, enemy_chars, max_turns=60):
    """
    team_chars, enemy_chars: lists of dicts representing characters (deep copies recommended)
    Returns dict with keys: player_win (bool), rounds (list of rounds each a list of strings)
    """
    # initialize combatants from dicts
    allies = [deepcopy_char_stats(c) for c in team_chars]
    enemies = [deepcopy_char_stats(c) for c in enemy_chars]

    rounds = []
    turn = 1
    while turn <= max_turns:
        round_lines = []
        # Allies act
        for a in allies:
            if a["hp"] <= 0:
                continue
            target = next((e for e in enemies if e["hp"] > 0), None)
            if not target:
                break
            dmg = simple_calc_damage(a, target, mult=1.0)
            target["hp"] -= dmg
            round_lines.append(f"{a['name']} hits {target['name']} for {dmg}.")

        # Enemies act
        for e in enemies:
            if e["hp"] <= 0:
                continue
            target = next((a for a in allies if a["hp"] > 0), None)
            if not target:
                break
            dmg = simple_calc_damage(e, target, mult=1.0)
            target["hp"] -= dmg
            round_lines.append(f"{e['name']} hits {target['name']} for {dmg}.")

        rounds.append(round_lines)

        # check end
        if not any(a["hp"] > 0 for a in allies):
            return {"player_win": False, "rounds": rounds, "title": f"Stage battle (turn {turn})"}
        if not any(e["hp"] > 0 for e in enemies):
            return {"player_win": True, "rounds": rounds, "title": f"Stage battle (turn {turn})"}

        turn += 1

    return {"player_win": False, "rounds": rounds, "title": "Timed out"}

def deepcopy_char_stats(ch):
    """
    Converts a Character instance or dict into a battle-ready dict
    """
    # Handle Character instances or already-dict
    stats = getattr(ch, "current_stats", None)
    if stats is None and isinstance(ch, dict):
        stats = ch.get("stats", ch)
    elif stats is None:
        stats = {}

    hp = int(stats.get("hp", stats.get("max_hp", 100)))
    max_hp = int(stats.get("max_hp", stats.get("hp", 100)))

    return {
        "id": getattr(ch, "id", ch.get("id", "unit") if isinstance(ch, dict) else "unit"),
        "name": getattr(ch, "name", ch.get("name", "unit") if isinstance(ch, dict) else "unit"),
        "hp": hp,
        "max_hp": max_hp,
        "attack": int(stats.get("attack", 100)),
        "defense": int(stats.get("defense", 50)),
        "crit_rate": stats.get("crit_rate", 0.05),
        "crit_dmg": stats.get("crit_dmg", 1.5),
        "speed": stats.get("speed", 100),
        "other": stats
    }
