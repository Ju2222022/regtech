import json
import re
import streamlit as st
import google.generativeai as genai
from typing import List, Dict

class ProductClassifierAgent:
    def __init__(self, referential_manager):
        self.ref_manager = referential_manager
        self._setup_gemini()

    def _setup_gemini(self):
        """Configure Gemini avec auto-détection du modèle autorisé par la clé."""
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
            
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            if not available_models:
                self.model = None
                return
                
            target_model = next((m for m in available_models if "1.5-flash" in m), available_models[0])
            self.model = genai.GenerativeModel(target_model.replace("models/", ""))
        except Exception as e:
            print(f"Erreur d'initialisation Gemini: {e}")
            self.model = None

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
        if not self.model:
            return {"error": "LLM Model not configured properly or no models available for this API key."}

        prompt = self._build_structured_prompt(product_description)
        
        try:
            response = self.model.generate_content(prompt)
            result = self._clean_json_output(response.text)
            return result
            
        except Exception as e:
            return {"error": f"Failed to analyze product: {str(e)}"}
