# abilities.py
import random

# abilities.py
class AbilityHandler:
    def __init__(self, cursor, cnx):
        self.cursor = cursor
        self.cnx = cnx

    def use_ability(self, attacker, ability, target_entity):
        query = "SELECT boss, hp FROM entities WHERE name = ?"
        values = (target_entity,)
        self.cursor.execute(query, values)
        result = self.cursor.fetchone()
        if result:
            is_boss, target_max_hp = result
            if ability == 'attack':
                self.attack(attacker, target_entity, is_boss)
            elif ability == 'heal':
                self.heal(attacker, target_entity, target_max_hp, is_boss)

    def attack(self, attacker, target, is_boss):
        damage = random.randint(10, 50) if is_boss else 10
        query = """
        UPDATE aiworld 
        SET health_points = CASE WHEN health_points - ? < 0 THEN 0 ELSE health_points - ? END
        WHERE entity = ? AND time = (SELECT MAX(time) FROM aiworld WHERE entity = ?)
        """
        values = (damage, damage, target, target)
        self.cursor.execute(query, values)
        self.cnx.commit()

    def heal(self, healer, target, target_max_hp, is_boss):
        healing = random.randint(10, 50) if is_boss else 10
        query = """
        UPDATE aiworld 
        SET health_points = CASE WHEN health_points + ? > ? THEN ? ELSE health_points + ? END
        WHERE entity = ? AND time = (SELECT MAX(time) FROM aiworld WHERE entity = ?)
        """
        values = (healing, target_max_hp, target_max_hp, healing, target, target)
        self.cursor.execute(query, values)
        self.cnx.commit()