# character.py
import math, random

# Rarity multipliers for base stats
RARITY_MULT = {
    "rare": 1.0,
    "epic": 1.25,
    "legendary": 1.5,
    "mythic": 1.7,
    "UR": 1.85,
    "Ascended": 2.0
}

# Ability counts per rarity (actives, passives)
ABILITY_COUNTS = {
    "rare": (1, 0),
    "epic": (2, 0),
    "legendary": (2, 1),
    "mythic": (3, 1),
    "UR": (3, 2),
    "Ascended": (4, 3)  # Wukong special handled separately
}

class Character:
    def __init__(self, id_name, rarity, cls, base_stats, skills,
                 level=1, stars=1, awakened=False, display_name=None):
        """
        skills: list of dicts with keys: name, type ('active'|'passive'), desc, effect, energy_cost
        base_stats: dict of hp, attack, defense, crit_rate, crit_dmg, speed, dodge, accuracy, armor_pierce, energy
        """
        self.id = id_name
        self.name = display_name if display_name else id_name
        self.rarity = rarity
        self.cls = cls
        self.level = level
        self.stars = stars
        self.awakened = awakened
        self.base_stats = base_stats.copy()
        self.skills = skills[:]
        # enforce counts immediately
        self.enforce_ability_counts()
        self.recalc()

    def enforce_ability_counts(self):
        """Trim or pad skills to match rarity. Wukong special case."""
        actives = [s for s in self.skills if s.get("type")=="active"]
        passives = [s for s in self.skills if s.get("type")=="passive"]

        if self.id == "wukong":
            want_a, want_p = 5, 4
        else:
            want_a, want_p = ABILITY_COUNTS.get(self.rarity, (1,0))

        # Trim extras
        actives = actives[:want_a]
        passives = passives[:want_p]

        self.skills = actives + passives

    def recalc(self):
        """Scale stats by level, rarity, stars, and awakened bonus."""
        star_mult = 1 + 0.15 * (self.stars - 1)
        rarity_mult = RARITY_MULT.get(self.rarity, 1.0)
        lv = self.level
        self.current_stats = {}

        for k, v in self.base_stats.items():
            if k in ("crit_rate","crit_dmg","dodge","accuracy"):
                self.current_stats[k] = v * (1 + 0.01*(lv-1)) * star_mult * rarity_mult
            else:
                self.current_stats[k] = v * ((1.03)**(lv-1)) * star_mult * rarity_mult

        self.current_stats["max_hp"] = self.current_stats.get("hp", 100)
        self.current_stats["hp"] = self.current_stats["max_hp"]
        self.current_stats["energy"] = self.current_stats.get("energy", 0)

        # Awakening bonuses
        if self.awakened:
            boost_mult = 1.30
            for stat in ("hp","attack","defense","speed"):
                if stat in self.current_stats:
                    self.current_stats[stat] *= boost_mult

            # Wukong special awakened effect
            if self.id == "wukong":
                # Wukong gets a special OP passive each turn (handled in battle loop)
                self.current_stats["wukong_special"] = True

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rarity": self.rarity,
            "class": self.cls,
            "level": self.level,
            "stars": self.stars,
            "awakened": self.awakened,
            "base_stats": self.base_stats,
            "skills": self.skills
        }

    @staticmethod
    def from_dict(d):
        return Character(
            d["id"],
            d.get("rarity","rare"),
            d.get("class","Warrior"),
            d.get("base_stats",{}),
            d.get("skills",[]),
            level=d.get("level",1),
            stars=d.get("stars",1),
            awakened=d.get("awakened",False),
            display_name=d.get("name", d.get("id"))
        )
