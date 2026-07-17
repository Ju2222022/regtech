import json
from typing import List, Dict

class ProductClassifierAgent:
    def __init__(self, referential_manager):
        """
        Initialise l'agent avec un accès direct au moteur d'ontologie.
        """
        self.ref_manager = referential_manager

    def _build_structured_prompt(self, product_description: str) -> str:
        """
        Construit le prompt structuré (Brain-Model-Assistant) pour l'LLM.
        """
        # 1. BRAIN (Le contexte de vérité absolue)
        categories = self.ref_manager.get_categories()
        ontology_context = json.dumps([{
            "id": cat.get("category_id"),
            "label": cat.get("category_label"),
            "definition": cat.get("business_definition"),
            "strict_attributes": cat.get("matching_engine_config", {}).get("strict_technical_attributes", []),
            "fuzzy_keywords": cat.get("matching_engine_config", {}).get("fuzzy_keywords_fallbacks", [])
        } for cat in categories], indent=2)

        # 2. MODEL (Le rôle et les règles)
        system_rules = """
        You are an Expert Regulatory Affairs Classifier.
        Your task is to analyze a new product description and map it to the provided Regulatory Ontology.
        
        RULES:
        - Analyze the product description step-by-step.
        - A product can belong to MULTIPLE categories.
        - If strict attributes match, mapping is mandatory.
        - If fuzzy keywords match, use logical deduction based on the business definition.
        - If no category matches, you MUST return the fallback category if one exists, or an empty list.
        """

        # 3. ASSISTANT (Le format strict attendu en sortie)
        output_format = """
        Return ONLY a valid JSON object strictly matching this schema, without any markdown formatting or extra text:
        {
            "analyzed_product": "Short summary of the product",
            "matched_categories": [
                {
                    "category_id": "ID_OF_THE_MATCH",
                    "confidence_score": "HIGH or MEDIUM or LOW",
                    "justification": "One sentence explaining why this category applies based on the ontology."
                }
            ]
        }
        """

        # Assemblage final
        prompt = f"""
        {system_rules}
        
        --- REGULATORY ONTOLOGY ---
        {ontology_context}
        
        --- PRODUCT TO ANALYZE ---
        {product_description}
        
        --- OUTPUT FORMAT ---
        {output_format}
        """
        return prompt

    def analyze_product(self, product_description: str) -> dict:
        """
        Exécute l'analyse du produit. 
        Note : La connexion API (OpenAI, Gemini, Claude) sera branchée ici.
        """
        prompt = self._build_structured_prompt(product_description)
        
        # TODO: Remplacer ce mock par l'appel API réel vers ton fournisseur LLM
        print("Prompt envoyé à l'LLM :")
        print(prompt)
        
        # Mock de réponse de l'LLM pour tester le pipeline
        mock_response = {
            "analyzed_product": product_description[:50] + "...",
            "matched_categories": [
                {
                    "category_id": "SUB_CAT_STD_ELEC",
                    "confidence_score": "HIGH",
                    "justification": "The product is described as an electronic device, matching the standard baseline."
                }
            ]
        }
        
        return mock_response
