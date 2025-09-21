import json
from character import Character

class Roster:
    def __init__(self):
        self.heroes=[]

    def load_templates_into_roster(self, templates_dict):
        # No auto-add; use add_from_template() externally
        pass

    def add_from_template(self, templ):
        c=Character(templ["id"], templ["rarity"], templ["class"], templ["stats"], templ["skills"], display_name=templ.get("name",templ["id"]))
        c.enforce_ability_counts()
        self.heroes.append(c)

    def add_hero(self, char_obj):
        self.heroes.append(char_obj)

    def save_to_file(self, filename="roster_save.json"):
        data=[h.to_dict() for h in self.heroes]
        with open(filename,"w") as f:
            json.dump(data,f, indent=2)

    def load_from_file(self, filename="roster_save.json"):
        try:
            with open(filename,"r") as f:
                data=json.load(f)
            self.heroes=[Character.from_dict(d) for d in data]
        except FileNotFoundError:
            self.heroes=[]

    def get_team(self,n=5):
        return self.heroes[:n]
