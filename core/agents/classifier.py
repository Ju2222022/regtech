import json
import re
import requests
import streamlit as st

class ProductClassifierAgent:
    def __init__(self, referential_manager):
        self.ref_manager = referential_manager

    def _clean_json_output(self, text: str) -> dict:
        text = text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except Exception as e:
            return {"error": f"JSON Parsing failed: {str(e)}"}

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
        You are an Expert Technical Classifier.
        Analyze the provided product description and map it to our internal organizational ontology.
        
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

        return f"{system_rules}\n\n--- INTERNAL ONTOLOGY ---\n{ontology_context}\n\n--- PRODUCT TO ANALYZE ---\n{product_description}\n\n--- OUTPUT EXPECTATIONS ---\n{output_format}"

    def analyze_product(self, product_description: str) -> dict:
        prompt = self._build_structured_prompt(product_description)
        
        try:
            # 1. Nettoyage absolu de la clé API
            raw_key = str(st.secrets["GEMINI_API_KEY"])
            api_key = "".join(raw_key.split())
            
            # 2. URL fixée en dur vers le modèle stable
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            url = url.encode('ascii', 'ignore').decode('ascii')
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1}
            }
            
            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
            
            if response.status_code != 200:
                return {"error": f"API HTTP {response.status_code}: {response.text}"}
                
            data = response.json()
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
            
            # 3. Extraction des Tokens d'utilisation
            usage = data.get("usageMetadata", {})
            total_tokens = usage.get("totalTokenCount", 0)
            
            result = self._clean_json_output(raw_text)
            result["_tokens"] = total_tokens
            
            return result
            
        except Exception as e:
            return {"error": f"Failed to analyze product: {str(e)}"}
