# sun_wukong_idle.py
'''
import pygame, sys, os, json, random, math, datetime, threading, time
from copy import deepcopy

pygame.init()
WIDTH, HEIGHT = 1280, 760
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sun Wukong Idle RPG - Engine")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 18)
BIG = pygame.font.SysFont("consolas", 28)

SAVE_FILE = "savegame.json"

# -----------------------
# Utilities
# -----------------------
def fmt(n):
    if isinstance(n, float):
        return f"{n:,.1f}"
    return f"{n:,}"

def clamp(x, a, b): return max(a, min(b, x))

def chance(p): return random.random() < p

# -----------------------
# Stats model
# -----------------------
STAT_KEYS = [
    "hp", "max_hp", "attack", "defense", "crit_rate", "crit_dmg",
    "speed", "dodge", "accuracy", "armor_pierce", "energy"
]

# -----------------------
# Currencies
# -----------------------
currencies = {
    "gold": 100000,
    "gems": 2000,
    "shards": 200,
    "tokens": 50,
    "awaken_stones": 5
}

# -----------------------
# Class / Awakening mapping
# -----------------------
CLASSES = {
    "Tank": "Paladin",
    "Archer": "Sharpshooter",
    "Fighter": "Berserker",
    "Mage": "Wizard",
    "Assassin": "Shadowblade",
    "Healer": "Cleric",
    "Summoner": "Necromancer",
    "Ranger": "Pathfinder",
    "Warrior": "Champion",
    "Elementalist": "Archmage"
}

# -----------------------
# Skill engine
# -----------------------
class Skill:
    # skill_type: "active" or "passive"
    # effect: dict describing what the skill does (see usages)
    # energy_cost: how much energy required (active)
    def __init__(self, name, skill_type, description, effect, energy_cost=0, cooldown=0):
        self.name = name
        self.skill_type = skill_type
        self.description = description
        self.effect = effect
        self.energy_cost = energy_cost
        self.cooldown = cooldown
        self._cd = 0

    def ready(self):
        return self._cd == 0

    def trigger_cooldown(self):
        self._cd = self.cooldown

    def tick(self):
        if self._cd > 0:
            self._cd = max(0, self._cd - 1)

# -----------------------
# Character template
# -----------------------
class Character:
    def __init__(self, id_name, display_name, cls, level, stars, base_stats, skills, awakened=False):
        self.id = id_name
        self.name = display_name
        self.cls = cls
        self.level = level
        self.stars = stars
        self.awakened = awakened
        # base_stats is dict: hp, attack, defense, crit_rate (0-1), crit_dmg (multiplier like 1.5), speed, dodge, accuracy, armor_pierce, energy
        self.base_stats = base_stats.copy()
        self.current_stats = base_stats.copy()
        self.current_stats["max_hp"] = base_stats["hp"]
        self.current_stats["hp"] = base_stats["hp"]
        self.current_stats["energy"] = base_stats.get("energy", 0)
        self.skills = skills[:]  # list of Skill objects
        self.passives = [s for s in self.skills if s.skill_type == "passive"]
        self.actives = [s for s in self.skills if s.skill_type == "active"]
        self.alive = True
        self.buffs = {}  # name -> {stat: val, turns: n}
        self.debuffs = {}
        self.ultimate_ready = False

    def recalc_from_level_and_stars(self):
        # simple progression: stats scale with level and stars
        lv = self.level
        star_mult = 1 + 0.15 * (self.stars - 1)  # each star +15%
        for k,v in self.base_stats.items():
            # stats scaled: base * (1.03^(level-1)) * star_mult
            if k in ("crit_rate","crit_dmg","dodge","accuracy"):
                self.current_stats[k] = v * (1 + 0.01*(lv-1)) * star_mult
            else:
                self.current_stats[k] = v * ((1.03)**(lv-1)) * star_mult
        self.current_stats["max_hp"] = self.current_stats["hp"]
        self.current_stats["hp"] = min(self.current_stats.get("hp", self.current_stats["max_hp"]), self.current_stats["max_hp"])
        # energy regen / start energy is unchanged for simplicity

    def apply_buffs_debuffs(self):
        # apply buff modifications: for temporary simulation only, persistent buffs handled elsewhere
        pass

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "cls": self.cls,
            "level": self.level,
            "stars": self.stars,
            "awakened": self.awakened,
            "base_stats": self.base_stats,
            "skills": [ {"name":s.name,"type":s.skill_type,"desc":s.description,"effect":s.effect,"energy_cost":s.energy_cost,"cooldown":s.cooldown} for s in self.skills ]
        }

    @staticmethod
    def from_dict(d):
        skills = []
        for sd in d.get("skills", []):
            skills.append(Skill(sd["name"], sd["type"], sd.get("desc",""), sd["effect"], sd.get("energy_cost",0), sd.get("cooldown",0)))
        ch = Character(d["id"], d["name"], d["cls"], d["level"], d["stars"], d["base_stats"], skills, d.get("awakened", False))
        ch.recalc_from_level_and_stars()
        return ch

# -----------------------
# Game database: Characters (Sun Wukong universe + unique designs)
# -----------------------
# Helper to create skill effects (standardized)
def dmg_effect(multiplier=1.0, is_aoe=False, target="enemy", pierce=0.0, add_flat=0):
    # multiplier multiplies caster attack
    return {"action":"damage", "mult":multiplier, "aoe":is_aoe, "target":target, "pierce":pierce, "add":add_flat}

def heal_effect(multiplier=1.0, aoe=False):
    return {"action":"heal", "mult":multiplier, "aoe":aoe}

def buff_effect(stat, amount, turns, target="ally", is_percent=True):
    return {"action":"buff","stat":stat,"amount":amount,"turns":turns,"target":target,"is_percent":is_percent}

def debuff_effect(stat, amount, turns, target="enemy", is_percent=True):
    return {"action":"debuff","stat":stat,"amount":amount,"turns":turns,"target":target,"is_percent":is_percent}

def energy_effect(amount):
    return {"action":"energy","amount":amount}

# Create characters
CHAR_DB = {}

def add_char_to_db(ch):
    CHAR_DB[ch.id] = ch

# Sun Wukong — EXTREMELY STRONG / HAX
wukong_skills = [
    Skill("Monkey Strike", "active", "Fast heavy strike: deals 1.8x attack to one target.", dmg_effect(1.8), energy_cost=15, cooldown=0),
    Skill("Nimbus Dash", "active", "Dashes and grants speed buff to self and fighters.", buff_effect("speed", 0.30, 2), energy_cost=10, cooldown=3),
    Skill("Cloud Split", "active", "AOE massive damage to all enemies scaled by (attack * 2.5).", dmg_effect(2.5, is_aoe=True), energy_cost=30, cooldown=4),
    Skill("Trickster Passive", "passive", "30% chance to ignore target defense and double crit damage.", {"action":"passive","chance":0.30,"ignore_def":True,"crit_dmg_mult":2.0}, energy_cost=0),
    Skill("Ruyi Ultimate", "active", "Ultimate: obliterate enemy team — deals 6x attack to one enemy, reduces their energy to 0 and stuns for 2 turns.", {"action":"ultimate","mult":6.0,"stun":2,"energy_drain":True}, energy_cost=100, cooldown=6)
]
wukong_base = {
    "hp": 12000.0,
    "attack": 2200.0,
    "defense": 700.0,
    "crit_rate": 0.35,
    "crit_dmg": 1.75,
    "speed": 140.0,
    "dodge": 0.12,
    "accuracy": 0.95,
    "armor_pierce": 0.25,
    "energy": 50.0
}
wukong = Character("wukong", "Sun Wukong", "Fighter", level=1, stars=5, base_stats=wukong_base, skills=wukong_skills, awakened=True)
# Wukong has exponential level scaling method defined later; we'll special-case his leveling

add_char_to_db(wukong)

# Support characters with synergy
# Jade Maiden - Mage support
jade_skills = [
    Skill("Arcane Bolt","active","Single target magic damage + 10% more damage to Fighters.", {"action":"damage","mult":1.4,"extra_vs":"Fighter"}, energy_cost=20, cooldown=0),
    Skill("Mana Weave","active","Restore energy to all allies.", energy_effect(25), energy_cost=0, cooldown=4),
    Skill("Sage Passive","passive","All mages grant +8% magic attack to allies.", {"action":"passive","ally_attack_pct":0.08}, energy_cost=0),
    Skill("Elemental Fury","active","AOE moderate dmg.", dmg_effect(1.2, is_aoe=True), energy_cost=30, cooldown=3),
    Skill("Storm Ultimate","active","Massive AOE", dmg_effect(3.5, is_aoe=True), energy_cost=100, cooldown=6)
]
jade_base = {
    "hp": 7000.0, "attack": 1800.0, "defense": 350.0, "crit_rate":0.12, "crit_dmg":1.5,
    "speed": 100.0, "dodge":0.06, "accuracy":0.98, "armor_pierce":0.05, "energy":40.0
}
jade = Character("jade", "Jade Maiden", "Mage", 1, 5, jade_base, jade_skills, awakened=False)
add_char_to_db(jade)

# Iron Monk - Tank & synergy with Wukong (draw fire)
monk_skills = [
    Skill("Shield Bash","active","Smash single target, small stun.", dmg_effect(0.9), energy_cost=15, cooldown=1),
    Skill("Taunt","active","Taunt enemies to target this unit for 2 turns.", {"action":"taunt","turns":2}, energy_cost=20, cooldown=3),
    Skill("Stone Skin","passive","Increase defense for all allies by 10%.", {"action":"passive","ally_def_pct":0.10}),
    Skill("Guard Ultimate","active","Massive defense buff to team.", buff_effect("defense", 0.50, 3, target="ally", is_percent=True), energy_cost=100, cooldown=6)
]
monk_base = {"hp":18000.0,"attack":900.0,"defense":1500.0,"crit_rate":0.05,"crit_dmg":1.4,"speed":70.0,"dodge":0.04,"accuracy":0.92,"armor_pierce":0.02,"energy":30.0}
monk = Character("monk","Iron Monk","Tank",1,5,monk_base,monk_skills)
add_char_to_db(monk)

# Silver Archer - DPS ranged who buffs crit
archer_skills = [
    Skill("Piercing Arrow","active","High single-target dmg, armor pierce.", dmg_effect(2.0, pierce=0.4), energy_cost=25),
    Skill("Focus Shot","active","Increase own crit rate for 3 turns.", buff_effect("crit_rate", 0.25, 3, target="self"), energy_cost=10, cooldown=2),
    Skill("Sharpshooter Passive","passive","When ally is Fighter, increase their crit dmg slightly.", {"action":"passive","bonus_crit_dmg_vs_fighter":0.15}),
    Skill("Rain of Arrows","active","AOE moderate damage", dmg_effect(1.1, is_aoe=True), energy_cost=40, cooldown=4),
    Skill("Vision Ultimate","active","Guaranteed crit next hit for whole team for 2 turns", buff_effect("crit_rate", 0.50, 2, target="ally"), energy_cost=100, cooldown=6)
]
archer_base = {"hp":8000,"attack":1600,"defense":400,"crit_rate":0.20,"crit_dmg":1.6,"speed":120,"dodge":0.08,"accuracy":0.96,"armor_pierce":0.10,"energy":45}
archer = Character("archer","Silver Archer","Archer",1,5,archer_base,archer_skills)
add_char_to_db(archer)

# Monkey King's Rival - Assassin who manipulates dodge and debuffs
rival_skills = [
    Skill("Shadow Slash","active","High single-target crit-prone dmg", dmg_effect(2.2), energy_cost=20),
    Skill("Evasion Hex","active","Reduce target dodge drastically for 3 turns", debuff_effect("dodge", 0.30, 3), energy_cost=20, cooldown=3),
    Skill("Ambush Passive","passive","First attack of battle deals +40% damage", {"action":"passive","first_strike_bonus":0.40}),
    Skill("Night Ultimate","active","Steal energy from all enemies and deal damage", {"action":"ultimate","steal_energy":30,"mult":2.0}, energy_cost=100, cooldown=6)
]
rival_base = {"hp":8500,"attack":2000,"defense":300,"crit_rate":0.40,"crit_dmg":1.8,"speed":160,"dodge":0.18,"accuracy":0.93,"armor_pierce":0.18,"energy":45}
rival = Character("rival","Rivalsong","Assassin",1,5,rival_base,rival_skills)
add_char_to_db(rival)

# Support Priest - heals and cleanse
priest_skills = [
    Skill("Light Heal","active","Heals one ally", heal_effect(1.2), energy_cost=20),
    Skill("Group Mend","active","Heals all allies moderately", heal_effect(0.8, aoe=True), energy_cost=40, cooldown=3),
    Skill("Guardian Passive","passive","All allies gain small regen each turn", {"action":"passive","regen":0.02})
]
priest_base = {"hp":9000,"attack":900,"defense":550,"crit_rate":0.06,"crit_dmg":1.45,"speed":90,"dodge":0.05,"accuracy":0.97,"armor_pierce":0.03,"energy":50}
priest = Character("priest","Lotus Priest","Healer",1,5,priest_base,priest_skills)
add_char_to_db(priest)

# Fill default starting roster (player will own these by default)
DEFAULT_ROSTER = ["wukong","jade","monk","archer","rival","priest"]

# -----------------------
# Player profile & roster
# -----------------------
player = {
    "name": "Player",
    "roster": [],  # list of Character instances owned
    "team_slots": [None]*5, # chosen team for battles
    "login_dates": [],
    "last_save": None
}

# -----------------------
# Campaigns / Events
# -----------------------
class Campaign:
    def __init__(self, name, base_hp, base_attack, base_reward_gold, difficulty=1.0):
        self.name = name
        self.level = 1
        self.base_hp = base_hp
        self.base_attack = base_attack
        self.base_reward_gold = base_reward_gold
        self.difficulty = difficulty

    def generate_enemy_team(self):
        # generate up to 5 enemy characters scaled by campaign level
        team = []
        lvl_mult = 1.05 ** (self.level - 1)
        for i in range(5):
            # create simple enemy with scaling stats
            base = {
                "hp": self.base_hp * lvl_mult * random.uniform(0.8,1.2),
                "attack": self.base_attack * lvl_mult * random.uniform(0.9,1.3),
                "defense": 300 * lvl_mult,
                "crit_rate": 0.08,
                "crit_dmg": 1.5,
                "speed": 90 + i*5,
                "dodge": 0.04,
                "accuracy": 0.9,
                "armor_pierce": 0.05,
                "energy": 40
            }
            # simple enemy skills: one basic attack + occasional AoE
            skl = [ Skill("Claw","active","Enemy basic", dmg_effect(1.0), energy_cost=0) ]
            e = Character(f"enemy_{self.name}_{self.level}_{i}","Bandit","Warrior",1,1,base,skl)
            team.append(e)
        return team

    def reward(self):
        return int(self.base_reward_gold * (1.15**(self.level-1)))

campaigns = [
    Campaign("Mountain Pass", 1000, 200, 1000),
    Campaign("Sky Temple", 6000, 800, 6000),
    Campaign("Dragon's Lair", 30000, 2500, 30000)
]

# Weekly events (rotate)
WEEKLY_EVENTS = [
    {"name":"Double Gold Week","mult_gold":2,"description":"All campaign gold rewards x2"},
    {"name":"Boss Raid Week","mult_gold":1.5,"description":"Special boss spawn: bigger rewards"},
    {"name":"Energy Week","energy_gain_mult":1.5,"description":"Energy gains increased"},
]
current_week_index = 0
week_start = datetime.date.today()

def start_new_week_if_needed():
    global current_week_index, week_start
    today = datetime.date.today()
    if (today - week_start).days >= 7:
        current_week_index = (current_week_index + 1) % len(WEEKLY_EVENTS)
        week_start = today

# -----------------------
# Save/Load
# -----------------------
def save_game():
    data = {
        "currencies": currencies,
        "player": {
            "name": player["name"],
            "roster": [c.to_dict() for c in player["roster"]],
            "team": [c.id if c else None for c in player["team_slots"]],
            "login_dates": [d.isoformat() for d in player["login_dates"]],
        },
        "campaigns": [{"name":c.name,"level":c.level} for c in campaigns],
        "week_index": current_week_index,
        "week_start": week_start.isoformat()
    }
    with open(SAVE_FILE,"w") as f:
        json.dump(data,f,indent=2)
    player["last_save"] = datetime.datetime.now().isoformat()
    print("[SAVE] Game saved.")

def load_game():
    if not os.path.exists(SAVE_FILE):
        # give starter roster
        for sid in DEFAULT_ROSTER:
            ch = deepcopy(CHAR_DB[sid])
            ch.recalc_from_level_and_stars()
            player["roster"].append(ch)
        # auto put first 5 as team (if wukong exists)
        for i in range(min(5,len(player["roster"]))):
            player["team_slots"][i] = player["roster"][i]
        print("[LOAD] New starter roster created.")
        return
    with open(SAVE_FILE,"r") as f:
        data = json.load(f)
    currencies.update(data.get("currencies",{}))
    p = data.get("player",{})
    player["name"] = p.get("name","Player")
    player["roster"] = [ Character.from_dict(d) for d in p.get("roster",[]) ]
    # set team slots by id mapping
    roster_map = {c.id:c for c in player["roster"]}
    for i,tid in enumerate(p.get("team",[])):
        player["team_slots"][i] = roster_map.get(tid, None)
    player["login_dates"] = [ datetime.date.fromisoformat(s) for s in p.get("login_dates",[]) ]
    # campaigns
    for cd in data.get("campaigns",[]):
        for c in campaigns:
            if c.name == cd["name"]:
                c.level = cd.get("level", c.level)
    global current_week_index, week_start
    current_week_index = data.get("week_index", 0)
    week_start = datetime.date.fromisoformat(data.get("week_start", week_start.isoformat()))
    print("[LOAD] Game loaded from save.")

# -----------------------
# Codes (3 specific codes including exact resource pack for Wukong team)
# -----------------------
def code_wukong():
    # grant Sun Wukong, and exact resources for an "insane synergy team" (numbers chosen precisely)
    # Give Wukong (maxed-ish) + team Jade, Monk, Archer, Priest
    # Exact resources: gold 1_000_000, gems 10_000, shards 5_000, tokens 1_000, awaken_stones 50
    global player
    # add characters if not present
    wanted = ["wukong","jade","monk","archer","priest"]
    for wid in wanted:
        if not any(c.id == wid for c in player["roster"]):
            ch = deepcopy(CHAR_DB[wid])
            # buff them to be powerful: level 50, stars 5
            ch.level = 50
            ch.stars = 5
            ch.recalc_from_level_and_stars()
            player["roster"].append(ch)
    # set team slots to these
    roster_map = {c.id:c for c in player["roster"]}
    teamids = ["wukong","monk","jade","archer","priest"]
    for i,tid in enumerate(teamids):
        player["team_slots"][i] = roster_map.get(tid)
    # give resources exact amounts
    currencies["gold"] += 1_000_000
    currencies["gems"] += 10_000
    currencies["shards"] += 5_000
    currencies["tokens"] += 1_000
    currencies["awaken_stones"] += 50
    print("[CODE] WUKONG redeemed: Sun Wukong + team added, resources granted.")

def code_godmode():
    currencies["gold"] += 10_000_000
    currencies["gems"] += 100_000
    currencies["shards"] += 50_000
    currencies["tokens"] += 10_000
    currencies["awaken_stones"] += 500
    print("[CODE] GODMODE redeemed: massive resources.")

def code_gold100k():
    currencies["gold"] += 100_000
    print("[CODE] GOLD100K redeemed: +100k gold.")

CODES = {
    "WUKONG": code_wukong,
    "GODMODE": code_godmode,
    "GOLD100K": code_gold100k
}

# -----------------------
# Battle system (5v5, turn based)
# -----------------------
class Combatant:
    def __init__(self, char:Character, owner="player"):
        # copy stats for battle instance
        self.template = char
        self.owner = owner
        self.id = char.id
        self.name = char.name
        self.cls = char.cls
        self.level = char.level
        self.stars = char.stars
        self.awakened = char.awakened
        self.stats = char.current_stats.copy()
        self.stats["hp"] = self.stats.get("hp", self.stats.get("max_hp",1000))
        self.stats["max_hp"] = self.stats.get("max_hp", self.stats["hp"])
        self.energy = self.stats.get("energy", 0)
        self.skills = deepcopy(char.skills)
        self.passives = [s for s in self.skills if s.skill_type=="passive"]
        self.actives = [s for s in self.skills if s.skill_type=="active"]
        self.alive = True
        self.buffs = {}  # name: {stat,val,turns}
        self.debuffs = {}
        self.stunned = 0
        self.taunted = 0
        self.first_strike_used = False

    def is_alive(self):
        return self.alive and self.stats["hp"] > 0

    def mod_stat(self, stat, amount, is_percent=False):
        # direct mod: if percent, multiply; else add
        if is_percent:
            self.stats[stat] *= (1+amount)
        else:
            self.stats[stat] += amount

    def take_damage(self, dmg):
        self.stats["hp"] -= dmg
        if self.stats["hp"] <= 0:
            self.stats["hp"] = 0
            self.alive = False

    def heal(self, amount):
        self.stats["hp"] = min(self.stats["hp"] + amount, self.stats["max_hp"])
        if self.stats["hp"] > 0:
            self.alive = True

    def tick(self):
        # reduce durations, skill cooldowns
        for s in self.skills:
            s.tick()
        if self.stunned > 0:
            self.stunned -= 1
        if self.taunted > 0:
            self.taunted -= 1
        # buffs/debuff turns
        for name in list(self.buffs.keys()):
            self.buffs[name]["turns"] -= 1
            if self.buffs[name]["turns"] <= 0:
                del self.buffs[name]
        for name in list(self.debuffs.keys()):
            self.debuffs[name]["turns"] -= 1
            if self.debuffs[name]["turns"] <= 0:
                del self.debuffs[name]

    def effective_stat(self, stat):
        # start with base
        val = self.stats.get(stat, 0)
        # apply buffs/debuffs
        for b in self.buffs.values():
            if b["stat"] == stat:
                if b["is_percent"]:
                    val *= (1 + b["amount"])
                else:
                    val += b["amount"]
        for d in self.debuffs.values():
            if d["stat"] == stat:
                if d["is_percent"]:
                    val *= (1 - d["amount"])
                else:
                    val -= d["amount"]
        return val

# Resolving actions based on skill effect dicts
def resolve_skill(user:Combatant, target:Combatant, skill:Skill, allies, enemies):
    eff = skill.effect
    log = []
    # Basic hit check: accuracy vs dodge
    def hit_check(u,t):
        acc = u.effective_stat("accuracy")
        dodge = t.effective_stat("dodge")
        # chance to hit = acc - dodge (clamped)
        prob = clamp(acc - dodge, 0.05, 0.99)
        return chance(prob)

    # damage formula: (user attack * mult) * (1 - target_def/(target_def + 1000)) * (1 - pierce)
    def calc_damage(u,t,mult,pierce,flat_add=0,extra_mult=1.0):
        atk = u.effective_stat("attack")
        defn = t.effective_stat("defense")
        pierce_total = u.effective_stat("armor_pierce") + pierce
        pierce_total = clamp(pierce_total,0,0.95)
        mitig = defn/(defn+1000)
        effective_mitig = mitig*(1-pierce_total)
        base = atk * mult * extra_mult + flat_add
        dmg = base * (1 - effective_mitig)
        # crit?
        crit_chance = u.effective_stat("crit_rate")
        is_crit = chance(crit_chance)
        if is_crit:
            dmg *= u.effective_stat("crit_dmg")
        # passive effects (wukong ignore def etc)
        for p in u.passives:
            pe = p.effect
            if isinstance(pe, dict) and pe.get("action")=="passive":
                if pe.get("ignore_def") and chance(pe.get("chance",0)):
                    # ignore defense
                    dmg = atk * mult * (1 + (pe.get("crit_dmg_mult",0)-1))  # approximate
                if pe.get("first_strike_bonus") and not u.first_strike_used:
                    dmg *= (1+pe["first_strike_bonus"])
        # clamp
        dmg = max(0, dmg)
        return int(dmg), is_crit

    if eff["action"] == "damage":
        if eff.get("aoe", False):
            for e in enemies:
                if not e.is_alive(): continue
                if not hit_check(user,e):
                    log.append(f"{user.name}'s {skill.name} missed {e.name}!")
                    continue
                dmg,crit = calc_damage(user,e, eff.get("mult",1.0), eff.get("pierce",0.0), eff.get("add",0))
                e.take_damage(dmg)
                log.append(f"{user.name} used {skill.name} on {e.name} for {dmg}{' (CRIT)' if crit else ''}.")
                # energy drain? not here
        else:
            if not target or not target.is_alive():
                # pick random alive
                targ = next((e for e in enemies if e.is_alive()), None)
            else:
                targ = target
            if targ is None:
                return log
            if not hit_check(user,targ):
                log.append(f"{user.name}'s {skill.name} missed {targ.name}!")
                return log
            extra_mult = 1.0
            # special 'extra_vs' flag
            if eff.get("extra_vs") and targ.cls == eff["extra_vs"]:
                extra_mult = 1.20
            dmg,crit = calc_damage(user,targ, eff.get("mult",1.0), eff.get("pierce",0.0), eff.get("add",0), extra_mult)
            targ.take_damage(dmg)
            log.append(f"{user.name} used {skill.name} on {targ.name} for {dmg}{' (CRIT)' if crit else ''}.")
    elif eff["action"] == "heal":
        if eff.get("aoe", False):
            for a in allies:
                if not a.is_alive(): continue
                heal_amount = int(user.effective_stat("attack") * eff.get("mult",1.0))
                a.heal(heal_amount)
                log.append(f"{user.name} healed {a.name} for {heal_amount}.")
        else:
            targ = target if (target and target.is_alive()) else user
            heal_amount = int(user.effective_stat("attack") * eff.get("mult",1.0))
            targ.heal(heal_amount)
            log.append(f"{user.name} healed {targ.name} for {heal_amount}.")
    elif eff["action"] == "buff":
        # target: ally / self / all allies
        ttype = eff.get("target","ally")
        stat = eff.get("stat")
        amount = eff.get("amount")
        turns = eff.get("turns",1)
        is_pct = eff.get("is_percent",True)
        if ttype == "self":
            user.buffs[skill.name] = {"stat":stat,"amount":amount,"turns":turns,"is_percent":is_pct}
            log.append(f"{user.name} gains {stat} {'+' if is_pct else ''}{amount}{'%' if is_pct else ''} for {turns} turns.")
        elif ttype in ("ally","ally_single","ally_all","ally_team"):
            for a in allies:
                if not a.is_alive(): continue
                a.buffs[skill.name] = {"stat":stat,"amount":amount,"turns":turns,"is_percent":is_pct}
            log.append(f"{user.name} buffed allies: {stat} +{amount}{'%' if is_pct else ''} for {turns} turns.")
        elif ttype == "ally_target":
            if target and target.is_alive():
                target.buffs[skill.name] = {"stat":stat,"amount":amount,"turns":turns,"is_percent":is_pct}
                log.append(f"{user.name} buffed {target.name}: {stat} +{amount}{'%' if is_pct else ''} for {turns} turns.")
    elif eff["action"] == "debuff":
        stat = eff.get("stat"); amount = eff.get("amount"); turns = eff.get("turns",1); is_pct = eff.get("is_percent",True)
        # apply to target(s)
        if eff.get("target","enemy") == "enemy":
            for e in enemies:
                if not e.is_alive(): continue
                e.debuffs[skill.name] = {"stat":stat,"amount":amount,"turns":turns,"is_percent":is_pct}
            log.append(f"{user.name} applied debuff {stat} -{amount}{'%' if is_pct else ''} to enemies for {turns} turns.")
    elif eff["action"] == "energy":
        amt = eff.get("amount",0)
        # grant energy to allies or self?
        for a in allies:
            if not a.is_alive(): continue
            a.energy = min(100, a.energy + amt)
        log.append(f"{user.name} granted {amt} energy to allies.")
    elif eff["action"] == "taunt":
        turns = eff.get("turns",1)
        user.taunted = turns
        log.append(f"{user.name} taunts enemies for {turns} turns.")
    elif eff["action"] == "ultimate":
        # custom ultimate handler
        if eff.get("energy_drain"):
            if target and target.is_alive():
                target.energy = 0
                log.append(f"{user.name} drains {target.name}'s energy to 0.")
        if eff.get("stun"):
            if target and target.is_alive():
                target.stunned = eff.get("stun")
                log.append(f"{target.name} stunned for {eff.get('stun')} turns.")
        # damage
        if eff.get("mult"):
            if eff.get("aoe", False):
                for e in enemies:
                    if not e.is_alive(): continue
                    dmg,crit = calc_damage(user,e, eff.get("mult",1.0), 0.0)
                    e.take_damage(dmg)
                    log.append(f"{user.name} ultimate hit {e.name} for {dmg}.")
            else:
                if target and target.is_alive():
                    dmg,crit = calc_damage(user,target, eff.get("mult",1.0), 0.0)
                    target.take_damage(dmg)
                    log.append(f"{user.name} ultimate hit {target.name} for {dmg}.")
        if eff.get("steal_energy"):
            steal = eff.get("steal_energy",0)
            for e in enemies:
                if not e.is_alive(): continue
                stolen = min(e.energy, steal)
                e.energy -= stolen
                user.energy = min(100, user.energy + stolen)
            log.append(f"{user.name} stole energy.")
    return log

# AI: simple: use highest-damage ready active, else basic attack
def ai_choose_skill(user:Combatant, allies, enemies):
    # prefer ult if energy>=cost
    best = None
    for s in user.actives:
        if s.energy_cost > 0 and user.energy < s.energy_cost:
            continue
        if s.effect.get("action") == "ultimate" and user.energy >= s.energy_cost:
            return s
        # choose highest mult damage available and ready
        if s.effect.get("action")=="damage" and s.ready():
            if best is None or s.effect.get("mult",1.0) > best.effect.get("mult",1.0):
                best = s
    # fallback to first active ready
    if best and best.ready():
        return best
    for s in user.actives:
        if s.ready() and (s.energy_cost == 0 or user.energy >= s.energy_cost):
            return s
    # else do basic attack simulated by a dummy skill
    return Skill("Basic Attack","active","auto", {"action":"damage","mult":1.0})

# Battle runner - synchronous per click / auto resolve
def run_battle(player_team, enemy_team, verbose=True):
    # player_team, enemy_team: lists of Character -> convert to Combatant
    allies = [Combatant(c,"player") for c in player_team if c]
    enemies = [Combatant(c,"enemy") for c in enemy_team if c]
    combatants = allies + enemies
    log = []
    # initial recalc buffs etc.
    turn = 1
    # Determine first-strike passives
    for c in allies+enemies:
        c.first_strike_used = False

    # loop until one side dead or max turns
    max_turns = 80
    while turn <= max_turns:
        # end condition
        if not any(c.is_alive() for c in allies):
            log.append("Enemies win!")
            break
        if not any(e.is_alive() for e in enemies):
            log.append("Players win!")
            break

        # determine order by speed desc each turn among alive
        acting = [c for c in allies+enemies if c.is_alive()]
        acting.sort(key=lambda x: x.effective_stat("speed"), reverse=True)

        for actor in acting:
            if not actor.is_alive(): continue
            actor.tick()
            # choose target group
            if actor.owner == "player":
                friend_group = allies
                enemy_group = enemies
            else:
                friend_group = enemies
                enemy_group = allies
            # check stun
            if actor.stunned > 0:
                log.append(f"{actor.name} is stunned, skips turn.")
                continue
            # increment small energy per turn
            actor.energy = min(100, actor.energy + 10)
            # choose skill
            if actor.owner == "player":
                # simplistic: player uses first available active or basic attack
                skill = None
                for s in actor.actives:
                    if s.ready() and (s.energy_cost == 0 or actor.energy >= s.energy_cost):
                        skill = s; break
                if skill is None:
                    skill = Skill("Basic Attack","active","auto", {"action":"damage","mult":1.0})
            else:
                skill = ai_choose_skill(actor, friend_group, enemy_group)
            # pick target: random alive enemy (or obey taunt)
            target = None
            if any(e.taunted>0 for e in enemy_group):
                # pick taunting enemy
                t = next((e for e in enemy_group if e.taunted>0 and e.is_alive()), None)
                target = t
            else:
                target = next((e for e in enemy_group if e.is_alive()), None)
            # consume energy
            if hasattr(skill, "energy_cost") and skill.energy_cost > 0:
                if actor.energy >= skill.energy_cost:
                    actor.energy -= skill.energy_cost
                else:
                    # cannot use, use basic
                    skill = Skill("Basic Attack","active","auto", {"action":"damage","mult":1.0})
            # resolve skill
            step_log = resolve_skill(actor, target, skill, friend_group, enemy_group)
            for L in step_log: log.append(L)
            # if skill is ultimate, reset its cooldowns etc.
            # mark first strike used
            actor.first_strike_used = True
            # check death end fast
            if not any(e.is_alive() for e in enemy_group) or not any(a.is_alive() for a in friend_group):
                break
        turn += 1
    # collect rewards if players won
    player_win = any(e.is_alive() == False for e in enemies) and any(a.is_alive() for a in allies)
    return {"log":log, "player_win":player_win, "turns":turn-1, "allies":allies, "enemies":enemies}

# -----------------------
# UI helpers
# -----------------------
input_text = ""
battle_log = []
log_scroll = 0

def draw_text_block(lines, x, y, w, h, title=None):
    pygame.draw.rect(screen, (30,30,30), (x,y,w,h))
    if title:
        screen.blit(BIG.render(title, True, (220,220,220)), (x+6,y+6))
    oy = y + (36 if title else 6)
    for i,line in enumerate(lines):
        if oy + i*20 > y + h - 20: break
        screen.blit(FONT.render(line, True, (240,240,240)), (x+6, oy + i*20))

# -----------------------
# UI Buttons for campaigns and actions
# -----------------------
def button(rect, text, fg=(255,255,255), bg=(80,80,80)):
    pygame.draw.rect(screen, bg, rect)
    screen.blit(FONT.render(text, True, fg), (rect[0]+6, rect[1]+6))
    return rect

# -----------------------
# Main loop
# -----------------------
load_game()
start_new_week_if_needed()
# ensure roster at least starter
if len(player["roster"]) == 0:
    for sid in DEFAULT_ROSTER:
        ch = deepcopy(CHAR_DB[sid])
        ch.recalc_from_level_and_stars()
        player["roster"].append(ch)
# ensure team
for i in range(5):
    if player["team_slots"][i] is None and i < len(player["roster"]):
        player["team_slots"][i] = player["roster"][i]

running = True
selected_campaign_index = 0
battle_running = False
last_battle_result = None

# We'll allow starting a synchronous battle when pressing button; it will produce logs
while running:
    clock.tick(30)
    start_new_week_if_needed()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_game()
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                code = input_text.strip().upper()
                if code in CODES:
                    CODES[code]()
                else:
                    print("[CODE] Invalid or already used.")
                input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            else:
                input_text += event.unicode
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx,my = event.pos
            # Campaign buttons
            for i,c in enumerate(campaigns):
                bx,by,bw,bh = 20, 120 + i*60, 300, 48
                if bx <= mx <= bx+bw and by <= my <= by+bh:
                    selected_campaign_index = i
                    # start a battle
                    # gather team
                    team = [s for s in player["team_slots"] if s]
                    if len(team)==0:
                        battle_log.insert(0,"No team selected!")
                    else:
                        enemy_team = campaigns[i].generate_enemy_team()
                        # run battle
                        res = run_battle(team, enemy_team)
                        # apply rewards if win
                        if res["player_win"]:
                            reward = campaigns[i].reward()
                            # apply event multiplier
                            evt = WEEKLY_EVENTS[current_week_index]
                            reward = int(reward * evt.get("mult_gold",1.0))
                            currencies["gold"] += reward
                            campaigns[i].level += 1
                            battle_log = res["log"] + [f"Victory! Reward: {fmt(reward)} gold. Campaign {campaigns[i].name} advanced to level {campaigns[i].level}."] + battle_log
                        else:
                            battle_log = res["log"] + ["Defeat..."] + battle_log
            # Save/Load buttons
            if 350 <= mx <= 550 and 20 <= my <= 60:
                save_game()
            if 560 <= mx <= 760 and 20 <= my <= 60:
                load_game()

    # Draw UI
    screen.fill((18,18,25))
    # Top bar
    pygame.draw.rect(screen, (24,24,40), (0,0,WIDTH,80))
    screen.blit(BIG.render("Sun Wukong Idle RPG - Engine (Turn-based 5v5)", True, (230,230,230)), (16,8))
    # currency display
    cx = 820
    for i,(k,v) in enumerate(currencies.items()):
        screen.blit(FONT.render(f"{k.capitalize()}: {fmt(int(v))}", True, (200,220,200)), (cx, 8 + i*18))
    # Save/Load buttons
    button((350,20,200,40),"Save Game (Click)", bg=(60,110,60))
    button((560,20,200,40),"Load Game (Click)", bg=(60,60,110))
    # Code input
    pygame.draw.rect(screen,(40,40,40),(820,140,420,36))
    screen.blit(FONT.render("Enter Code and press Enter: " + input_text, True, (230,230,230)), (828,148))

    # Campaign list
    for i,c in enumerate(campaigns):
        rect = (20,120 + i*60,300,48)
        col = (80,80,120) if i!=selected_campaign_index else (120,80,80)
        pygame.draw.rect(screen, col, rect)
        screen.blit(FONT.render(f"{c.name} (Lvl {c.level}) - Base reward {fmt(c.base_reward_gold)}", True, (240,240,240)), (rect[0]+8,rect[1]+10))

    # Team display
    pygame.draw.rect(screen,(32,32,48),(350,120,420,300))
    screen.blit(BIG.render("Team (5 slots)", True, (230,230,230)), (356,126))
    for i in range(5):
        x = 360 + (i%5)*82
        y = 160
        slot = player["team_slots"][i]
        pygame.draw.rect(screen,(40,40,60),(x,y,76,96))
        if slot:
            screen.blit(FONT.render(f"{slot.name}", True, (220,220,220)), (x+4,y+6))
            screen.blit(FONT.render(f"Lvl {slot.level} {slot.cls}", True, (180,200,200)), (x+4,y+28))
            screen.blit(FONT.render(f"HP {int(slot.current_stats['hp'])}", True, (200,180,180)), (x+4,y+46))
            screen.blit(FONT.render(f"ATK {int(slot.current_stats['attack'])}", True, (200,180,180)), (x+4,y+66))
        else:
            screen.blit(FONT.render("Empty", True, (120,120,120)), (x+8,y+40))

    # Roster (scroll limited)
    pygame.draw.rect(screen,(30,30,40),(350,440,420,300))
    screen.blit(BIG.render("Roster", True, (220,220,220)), (356,446))
    ry = 480
    for i,ch in enumerate(player["roster"]):
        if ry > 720: break
        screen.blit(FONT.render(f"{ch.name} L{ch.level} ★{ch.stars} {ch.cls}", True, (220,220,220)), (360,ry))
        ry += 22

    # Battle Log panel
    log_lines = battle_log[:20]
    draw_text_block(log_lines, 800, 200, 460, 520, title="Battle Log")

    # Campaign info
    sel = campaigns[selected_campaign_index]
    pygame.draw.rect(screen,(28,28,36),(20,340,300,120))
    screen.blit(FONT.render(f"Selected: {sel.name}", True, (240,240,240)), (26,346))
    screen.blit(FONT.render(f"Level: {sel.level}", True, (200,200,200)), (26,366))
    evt = WEEKLY_EVENTS[current_week_index]
    screen.blit(FONT.render(f"Weekly Event: {evt['name']}", True, (200,180,120)), (26,396))
    screen.blit(FONT.render(f"{evt.get('description','')}", True, (160,160,160)), (26,416))

    # Footer instructions
    screen.blit(FONT.render("Click a campaign to fight it. Type codes and press Enter. Save/Load buttons at top.", True, (180,180,180)), (20,720))

    pygame.display.flip()

pygame.quit()
sys.exit()

# -----------------------
# Main game loop
# -----------------------
load_game()

running = True
while running:
    screen.fill((0, 0, 0))

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            elif event.key == pygame.K_RETURN:
                code = input_text.strip().upper()
                if code in CODES:
                    CODES[code]()  # run the function
                    battle_log.append(f"Code {code} redeemed!")
                else:
                    battle_log.append(f"Invalid code: {code}")
                input_text = ""
            else:
                input_text += event.unicode

    # Draw currencies
    y = 10
    for k,v in currencies.items():
        screen.blit(FONT.render(f"{k}: {fmt(v)}", True, (255,255,0)), (10,y))
        y += 20

    # Draw current input
    screen.blit(FONT.render("Enter Code: " + input_text, True, (200,200,200)), (10, HEIGHT-40))

    # Draw log
    oy = HEIGHT - 200
    for line in battle_log[-8:]:
        screen.blit(FONT.render(line, True, (220,220,220)), (10, oy))
        oy += 20

    pygame.display.flip()
    clock.tick(30)

save_game()
pygame.quit()
sys.exit()

'''
# main.py
from pygame import Rect
import pygame, sys, json
from roster import Roster
from battle import battle
from campaign import generate_enemy_team, get_stage_rewards
from ui import draw_menu, draw_roster, draw_battle_history, draw_battle_details, draw_inventory
from copy import deepcopy

WIDTH, HEIGHT = 800, 600
MAX_BATTLE_HISTORY = 10

def load_templates(filename):
    """Load JSON templates as a list of dicts."""
    with open(filename, "r") as f:
        data = json.load(f)
        # Convert dict to list if needed
        if isinstance(data, dict):
            return list(data.values())
        return data

def draw_back_button(screen, button_font):
    button_rect = Rect(650, 500, 120, 50)
    pygame.draw.rect(screen, (100, 100, 100), button_rect)
    pygame.draw.rect(screen, (255, 255, 255), button_rect, 2)
    screen.blit(button_font.render("Back", True, (255, 255, 255)), (button_rect.x + 30, button_rect.y + 15))
    return button_rect

def draw_reward_preview(screen, font, stage, rewards):
    screen.fill((30, 30, 60))
    screen.blit(font.render(f"Stage {stage} Rewards", True, (255, 255, 0)), (50, 50))
    y = 120
    for item, amount in rewards.items():
        screen.blit(font.render(f"{item}: {amount}", True, (255, 255, 255)), (50, y))
        y += 30

    fight_btn = Rect(200, 400, 150, 50)
    back_btn = Rect(400, 400, 150, 50)
    pygame.draw.rect(screen, (0, 200, 0), fight_btn)
    pygame.draw.rect(screen, (200, 0, 0), back_btn)
    screen.blit(font.render("Fight", True, (0, 0, 0)), (fight_btn.x+40, fight_btn.y+15))
    screen.blit(font.render("Back", True, (0, 0, 0)), (back_btn.x+40, back_btn.y+15))
    return fight_btn, back_btn

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Sun Wukong Idle - Prototype")
    font = pygame.font.SysFont("arial", 20)
    button_font = pygame.font.SysFont("arial", 18)
    clock = pygame.time.Clock()

    hero_templates = load_templates("data/heroes.json")
    enemy_templates = load_templates("data/enemies.json")

    roster = Roster()
    roster.load_templates_into_roster(hero_templates)
    if not roster.heroes:
        for h in hero_templates:
            roster.add_from_template(h)

    # Game state
    current_screen = "menu"
    selected = 0
    stage = 1
    battle_history = []
    last_battle_log = None
    detail_index = 0
    rewards = None
    inventory = {"Coins":0,"Gems":0,"Gear":0,"XP":0,"Essence":0}

    menu_options = [
        {"label":"View Roster","screen":"roster"},
        {"label":"Start Campaign Battle","action":"campaign_battle"},
        {"label":"Inventory","screen":"inventory"},
        {"label":"Battle History","screen":"battle_history"},
    ]

    running = True
    while running:
        screen.fill((8,12,30))
        fight_btn = back_btn = back_button = None

        # Draw screens
        if current_screen == "menu":
            draw_menu(screen, font, [opt["label"] for opt in menu_options], selected)
        elif current_screen == "roster":
            draw_roster(screen, font, roster, selected)
            back_button = draw_back_button(screen, button_font)
        elif current_screen == "inventory":
            draw_inventory(screen, font, inventory)
            back_button = draw_back_button(screen, button_font)
        elif current_screen == "battle_history":
            draw_battle_history(screen, font, battle_history, selected)
            back_button = draw_back_button(screen, button_font)
        elif current_screen == "battle_details" and battle_history:
            draw_battle_details(screen, font, battle_history[detail_index])
            back_button = draw_back_button(screen, button_font)
        elif current_screen == "reward_preview":
            fight_btn, back_btn = draw_reward_preview(screen, font, stage, rewards)

        # Overlay: last battle brief
        if last_battle_log:
            y = 420
            rounds = last_battle_log.get("rounds", [])
            if rounds:
                for line in rounds[-1]:
                    screen.blit(font.render(line, True, (255,200,200)), (50, y))
                    y += 18
            else:
                screen.blit(font.render(f"Result: {last_battle_log.get('result','?')}", True, (255,200,200)), (50, y))

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                roster.save_to_file("roster_save.json")
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx,my = event.pos
                if back_button and back_button.collidepoint((mx,my)):
                    if current_screen in ("roster","inventory","battle_history"):
                        current_screen = "menu"; selected=0
                    elif current_screen == "battle_details":
                        current_screen = "battle_history"
                    elif current_screen == "reward_preview":
                        current_screen = "menu"

                if current_screen == "reward_preview" and fight_btn and back_btn:
                    if fight_btn.collidepoint((mx,my)):
                        team_copy = [deepcopy(h) for h in roster.get_team(5)]
                        enemies_copy = [deepcopy(e) for e in generate_enemy_team(stage, enemy_templates)]

                        last_battle_log = battle(team_copy, enemies_copy)
                        battle_history.append(last_battle_log)
                        if len(battle_history) > MAX_BATTLE_HISTORY:
                            battle_history.pop(0)

                        if last_battle_log.get("player_win"):
                            for item, amount in rewards.items():
                                inventory[item] = inventory.get(item, 0) + amount

                        stage += 1
                        current_screen = "menu"

                    elif back_btn.collidepoint((mx,my)):
                        current_screen = "menu"

                # Roster selection
                if current_screen == "roster":
                    base_x, base_y = 40, 80
                    for i,h in enumerate(roster.heroes):
                        rect = Rect(base_x, base_y+i*28, 420,24)
                        if rect.collidepoint((mx,my)):
                            selected=i; break

                # Battle history click
                if current_screen == "battle_history" and battle_history:
                    base_x, base_y = 40, 80
                    for i,entry in enumerate(battle_history):
                        rect = Rect(base_x, base_y+i*28, 700, 24)
                        if rect.collidepoint((mx,my)):
                            detail_index=i
                            current_screen="battle_details"
                            selected=i
                            break

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if current_screen != "menu":
                        if current_screen=="battle_details":
                            current_screen="battle_history"
                            selected=detail_index
                        else:
                            current_screen="menu"
                            selected=0
                    else:
                        roster.save_to_file("roster_save.json")
                        running=False

                elif current_screen=="menu":
                    if event.key==pygame.K_DOWN: selected=(selected+1)%len(menu_options)
                    elif event.key==pygame.K_UP: selected=(selected-1)%len(menu_options)
                    elif event.key==pygame.K_RETURN:
                        option = menu_options[selected]
                        if "screen" in option:
                            current_screen=option["screen"]; selected=0
                        elif "action" in option and option["action"]=="campaign_battle":
                            rewards = get_stage_rewards(stage)
                            current_screen="reward_preview"

                elif current_screen=="roster":
                    if event.key==pygame.K_DOWN: selected=min(len(roster.heroes)-1,selected+1)
                    elif event.key==pygame.K_UP: selected=max(0,selected-1)
                    elif event.key==pygame.K_RETURN:
                        detail=roster.heroes[selected].to_dict()
                        fake={"title":f"Hero: {detail.get('name')}", "rounds":[ [f"Level {detail.get('level')} {detail.get('cls')}"] ], "player_win":None}
                        battle_history.append(fake)
                        if len(battle_history)>MAX_BATTLE_HISTORY: battle_history.pop(0)
                        detail_index=len(battle_history)-1
                        current_screen="battle_details"

                elif current_screen=="inventory":
                    current_screen="menu"; selected=0

                elif current_screen=="battle_history" and battle_history:
                    if event.key==pygame.K_DOWN: selected=min(len(battle_history)-1,selected+1)
                    elif event.key==pygame.K_UP: selected=max(0,selected-1)
                    elif event.key==pygame.K_RETURN:
                        detail_index=selected
                        current_screen="battle_details"

                elif current_screen=="battle_details":
                    if event.key==pygame.K_RETURN:
                        current_screen="battle_history"; selected=detail_index

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()


if __name__=="__main__":
    main()
