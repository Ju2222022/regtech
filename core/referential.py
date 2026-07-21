import json
import os
import csv

class ReferentialManager:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), 'ontology_db.json')
        self.default_csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'default_ontology.csv')
        self.data = self._load_database()

    def _load_database(self):
        # 1. Si la base de données JSON existe (session active), on la lit
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            except Exception:
                pass
                
        # 2. Sinon (redémarrage du serveur Streamlit), on charge le CSV de secours depuis GitHub
        base_data = {
            "tenant_profile": {},
            "global_routing_rules": {},
            "categories": []
        }
        
        if os.path.exists(self.default_csv_path):
            try:
                with open(self.default_csv_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cat = {
                            "category_id": row.get("category_id", ""),
                            "perimeter": row.get("perimeter", "Uncategorized"),
                            "internal_owner_group": row.get("category_label", "Unassigned"),
                            "category_label": row.get("sub_category_label", "Unnamed"),
                            "business_definition": row.get("business_definition", ""),
                            "matching_engine_config": {
                                "strict_technical_attributes": [x.strip() for x in row.get("strict_attributes", "").split("|") if x.strip()],
                                "fuzzy_keywords_fallbacks": [x.strip() for x in row.get("keywords", "").split("|") if x.strip()]
                            },
                            # Les sections juridiques sont vidées car l'outil se concentre sur l'organisation
                            "reference_legal_framework": [],
                            "expected_deliverables": []
                        }
                        base_data["categories"].append(cat)
                
                # On recrée immédiatement le fichier JSON pour la session en cours
                self.data = base_data
                self._save_database()
                return base_data
            except Exception as e:
                print(f"Erreur CSV: {e}")
                
        return base_data

    def _save_database(self):
        try:
            with open(self.db_path, 'w', encoding='utf-8') as file:
                json.dump(self.data, file, indent=4, ensure_ascii=False)
        except Exception:
            pass

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
            self._save_database()
            return True
        return False

    def update_category(self, updated_category):
        categories = self.get_categories()
        for idx, cat in enumerate(categories):
            if cat.get("category_id") == updated_category.get("category_id"):
                categories[idx] = updated_category
                self._save_database()
                return True
        return False

    def delete_category(self, category_id):
        categories = self.get_categories()
        initial_length = len(categories)
        self.data["categories"] = [cat for cat in categories if cat.get("category_id") != category_id]
        if len(self.data["categories"]) < initial_length:
            self._save_database()
            return True
        return False
