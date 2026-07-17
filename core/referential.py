import json
import os
from typing import Dict, List, Optional

class ReferentialManager:
    def __init__(self, filepath: str = "data/legal_categories.json"):
        self.filepath = filepath
        self.data = self._load_referential()

    def _load_referential(self) -> dict:
        """Loads the JSON referential file. Falls back to a skeletal structure if missing."""
        if not os.path.exists(self.filepath):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            # Default empty agnostic structure
            default_structure = {
                "_meta": {"version": "2.2_FINAL", "description": "RegWatch Agnostic Schema", "tenant_id": "default"},
                "tenant_profile": {"company_name": "New Client", "industry_sector": "Unknown"},
                "global_routing_rules": {"has_mandatory_fallback": False, "mandatory_fallback_category_id": "", "allow_multi_labeling": True},
                "defined_ontology": []
            }
            self.save_referential(default_structure)
            return default_structure
        
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_referential(self, data: dict) -> bool:
        """Saves the ontology data back to the JSON file."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.data = data
            return True
        except Exception as e:
            print(f"Error saving referential: {e}")
            return False

    def get_categories(self) -> List[dict]:
        """Returns all defined categories in the ontology."""
        return self.data.get("defined_ontology", [])

    def get_category_by_id(self, category_id: str) -> Optional[dict]:
        """Retrieves a specific category configuration."""
        for cat in self.get_categories():
            if cat.get("category_id") == category_id:
                return cat
        return None

    def get_fallback_category(self) -> Optional[dict]:
        """Retrieves the mandatory fallback category if enabled."""
        rules = self.data.get("global_routing_rules", {})
        if rules.get("has_mandatory_fallback"):
            fallback_id = rules.get("mandatory_fallback_category_id")
            return self.get_category_by_id(fallback_id)
        return None

    def add_category(self, new_category: dict) -> bool:
        """Adds a new dynamic category to the ontology database."""
        categories = self.get_categories()
        # Prevent duplicate IDs
        if any(cat.get("category_id") == new_category.get("category_id") for cat in categories):
            return False
        
        categories.append(new_category)
        self.data["defined_ontology"] = categories
        return self.save_referential(self.data)

    def delete_category(self, category_id: str) -> bool:
        """Deletes a category from the ontology by its ID."""
        categories = self.get_categories()
        initial_length = len(categories)
        
        # Filtre la liste pour exclure l'ID à supprimer
        updated_categories = [cat for cat in categories if cat.get("category_id") != category_id]
        
        if len(updated_categories) < initial_length:
            self.data["defined_ontology"] = updated_categories
            return self.save_referential(self.data)
        return False

    def update_category(self, updated_category: dict) -> bool:
        """Updates an existing category in the ontology."""
        categories = self.get_categories()
        for i, cat in enumerate(categories):
            if cat.get("category_id") == updated_category.get("category_id"):
                categories[i] = updated_category
                self.data["defined_ontology"] = categories
                return self.save_referential(self.data)
        return False
