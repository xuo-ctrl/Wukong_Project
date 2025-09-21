import random
from character import Character

def generate_enemy_team(stage, enemy_data):
    """
    Returns a list of 5 Character objects scaled by stage.
    enemy_data: list of dicts (as loaded from JSON)
    """
    team = []
    for _ in range(5):
        template = random.choice(enemy_data)
        scale = 1.05 ** stage
        stats = {
            "hp": int(template["stats"]["hp"] * scale),
            "attack": int(template["stats"]["attack"] * scale),
            "defense": int(template["stats"]["defense"] * scale),
            "speed": template["stats"]["speed"],
            "crit_rate": template["stats"].get("crit_rate", 0.05),
            "crit_dmg": template["stats"].get("crit_dmg", 1.5),
            "dodge": template["stats"].get("dodge", 0.02),
            "accuracy": template["stats"].get("accuracy", 1.0),
            "armor_pierce": template["stats"].get("armor_pierce", 0.0),
            "energy": template["stats"].get("energy", 20)
        }
        # Always create Character instance
        enemy = Character(
            id_name=template.get("id", template["name"]),
            rarity=template.get("rarity", "rare"),
            cls=template.get("class", "Warrior"),
            base_stats=stats,
            skills=template.get("skills", []),
        )
        team.append(enemy)
    return team


def get_stage_rewards(stage):
    return {
        "Coins": 100*stage,
        "Gems": stage//5,
        "Gear": 1 if stage%3==0 else 0,
        "XP": 50*stage,
        "Essence": 10*(stage//2)
    }
