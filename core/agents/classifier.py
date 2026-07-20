import json
import re
import requests
import streamlit as st
from typing import List, Dict

class ProductClassifierAgent:
    def __init__(self, referential_manager):
        self.ref_manager = referential_manager

    def _get_best_gemini_model(self, api_key: str) -> str:
        """Interroge l'API pour lister les modèles autorisés et sélectionne le meilleur, en évitant les pièges de Google."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                models = resp.json().get('models', [])
                valid_models = [m['name'] for m in models if 'generateContent' in m.get('supportedGenerationMethods', [])]
                
                # 1. On force la recherche stricte du modèle 1.5-flash de base
                for m in valid_models:
                    if m == "models/gemini-1.5-flash":
                        return m
                        
                # 2. Sinon on cherche une variante du 1.5-flash
                for m in valid_models:
                    if "1.5-flash" in m:
                        return m
                        
                # 3. En dernier recours, on prend un flash, mais on BAN TOUTE LA GAMME 2.x
                for m in valid_models:
                    if "flash" in m and "2." not in m:
                        return m
                        
                if valid_models:
                    return valid_models[0]
        except Exception:
            pass
        return "models/gemini-1.5-flash"

    def _clean_json_output(self, text: str) -> dict:
        """Sécurise la lecture du JSON généré par l'IA."""
        text = text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    def _build_structured_prompt(self, product_description: str) -> str:
        categories = self.ref_manager.get_categories()
        
        ontology_context = json.dumps([{
            "id": cat.get("category_id"),
            "label": cat.get("category_label"),
            "definition": cat.get("business_definition"),
            "strict_attributes": cat.get("matching_engine_config", {}).get("strict_technical_attributes", []),
            "keywords": cat.get("matching_engine_config", {}).get("fuzzy_keywords_fallbacks", [])
        } for cat in categories], indent=2)

        system_rules = """
        You are an Expert Regulatory Affairs Classifier.
        Analyze the provided product description and map it to the Regulatory Ontology.
        
        RULES:
        1. A product can belong to MULTIPLE categories.
        2. Strict attributes matches trigger mandatory inclusion.
        3. Use logical deduction based on the business definition for fuzzy matches.
        4. If nothing matches, return an empty list.
        """

        output_format = """
        Respond ONLY with a valid JSON object matching this exact schema, without any text before or after:
        {
            "analyzed_product": "A very brief 1-sentence summary of the product",
            "matched_categories": [
                {
                    "category_id": "THE_EXACT_ID_FROM_ONTOLOGY",
                    "confidence_score": "HIGH or MEDIUM or LOW",
                    "justification": "One clear sentence explaining the match."
                }
            ]
        }
        """

        return f"{system_rules}\n\n--- REGULATORY ONTOLOGY ---\n{ontology_context}\n\n--- PRODUCT TO ANALYZE ---\n{product_description}\n\n--- OUTPUT FORMAT EXPECTATIONS ---\n{output_format}"

    def analyze_product(self, product_description: str) -> dict:
        prompt = self._build_structured_prompt(product_description)
        
    try:
            # On utilise .strip() pour nettoyer les espaces/sauts de ligne invisibles
            api_key = st.secrets["GEMINI_API_KEY"].strip()
            
            # Récupération dynamique du modèle, également nettoyée
            model_name = self._get_best_gemini_model(api_key).strip()
            
            # Construction sécurisée de l'URL
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1}
            }
            
            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
            
            if response.status_code != 200:
                return {"error": f"API HTTP {response.status_code}: {response.text}"}
                
            data = response.json()
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
            return self._clean_json_output(raw_text)
            
        except Exception as e:
            return {"error": f"Failed to analyze product: {str(e)}"}
