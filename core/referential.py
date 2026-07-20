import json
import os

class ReferentialManager:
    def __init__(self):
        # On définit le chemin physique du fichier de base de données
        # Il sera créé dans le dossier "core" de ton projet
        self.db_path = os.path.join(os.path.dirname(__file__), 'ontology_db.json')
        self.data = self._load_database()

    def _load_database(self):
        """Charge les données depuis le fichier JSON, ou initialise une structure vide."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            except Exception as e:
                print(f"Erreur de lecture de la base de données : {e}")
                
        # Structure par défaut si le fichier n'existe pas encore
        return {
            "tenant_profile": {},
            "global_routing_rules": {},
            "categories": []
        }

    def _save_database(self):
        """Écrit instantanément les données actuelles dans le fichier JSON physique."""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as file:
                json.dump(self.data, file, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur de sauvegarde de la base de données : {e}")

    def get_categories(self):
        return self.data.get("categories", [])

    def get_category_by_id(self, category_id):
        for cat in self.get_categories():
            if cat.get("category_id") == category_id:
                return cat
        return None

    def add_category(self, category_data):
        if not self.get_category_by_id(category_data.get("category_id")):
            self.data.setdefault("categories", []).append(category_data)
            self._save_database()  # <-- SAUVEGARDE SUR DISQUE
            return True
        return False

    def update_category(self, updated_category):
        categories = self.get_categories()
        for idx, cat in enumerate(categories):
            if cat.get("category_id") == updated_category.get("category_id"):
                categories[idx] = updated_category
                self._save_database()  # <-- SAUVEGARDE SUR DISQUE
                return True
        return False

    def delete_category(self, category_id):
        categories = self.get_categories()
        initial_length = len(categories)
        self.data["categories"] = [cat for cat in categories if cat.get("category_id") != category_id]
        
        if len(self.data["categories"]) < initial_length:
            self._save_database()  # <-- SAUVEGARDE SUR DISQUE
            return True
        return False
