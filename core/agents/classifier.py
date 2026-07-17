import json
import streamlit as st
import google.generativeai as genai
from typing import List, Dict

class ProductClassifierAgent:
    def __init__(self, referential_manager):
        self.ref_manager = referential_manager
        self._setup_gemini()

    def _setup_gemini(self):
        """Configure l'accès à Gemini via les secrets Streamlit."""
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
            # Gemini 1.5 Flash est parfait : ultra-rapide, économique et doué pour le JSON
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        except KeyError:
            st.error("⚠️ The GEMINI_API_KEY is missing from Streamlit Secrets. The AI won't respond.")
            self.model = None

    def _build_structured_prompt(self, product_description: str) -> str:
        """Construit le prompt BMAD avec l'ontologie en contexte."""
        categories = self.ref_manager.get_categories()
        
        # On ne garde que l'essentiel pour économiser des tokens
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
        Respond ONLY with a valid JSON object matching this exact schema:
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

        prompt = f"""
        {system_rules}
        
        --- REGULATORY ONTOLOGY ---
        {ontology_context}
        
        --- PRODUCT TO ANALYZE ---
        {product_description}
        
        --- OUTPUT FORMAT EXPECTATIONS ---
        {output_format}
        """
        return prompt

    def analyze_product(self, product_description: str) -> dict:
        """Envoie le prompt à Gemini et retourne un dictionnaire."""
        if not self.model:
            return {"error": "LLM Model not configured."}

        prompt = self._build_structured_prompt(product_description)
        
        try:
            # On force le modèle à cracher du JSON pur
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1 # Température basse pour éviter la créativité sur du réglementaire
                )
            )
            
            # On transforme le texte JSON de Gemini en vrai dictionnaire Python
            result = json.loads(response.text)
            
            # Mise à jour du tracker de coûts (approximatif pour la démo)
            if "session_tokens" in st.session_state:
                st.session_state["session_tokens"]["calls"] += 1
                
            return result
            
        except Exception as e:
            print(f"Erreur API Gemini: {e}")
            return {"error": f"Failed to analyze product: {str(e)}"}
