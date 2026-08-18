import json
from core.agents.watcher import call_gemini

def generate_card_update(gemini_key: str, legal_card: dict, gap_analysis: dict, signal_url: str = "") -> dict:
    """
    Prend une Legal Card existante et y intègre les nouveaux écarts identifiés par l'analyse d'impact.
    Retourne la nouvelle structure JSON mise à jour.
    """
    system_prompt = """You are a Regulatory Affairs Expert and Data Engineer.
Your task is to UPDATE an existing product compliance Legal Card (JSON) based on a Gap Analysis report.

--- INSTRUCTIONS ---
1. Read the provided EXISTING LEGAL CARD.
2. Read the GAP ANALYSIS IDENTIFIED GAPS and the SIGNAL URL provided below.
3. Integrate the missing requirements, markings, or documents into the respective arrays ("requirements", "markings", "documents").
4. Assign logical values for "Type", "Parameter", "Limit", and "Reference" based on the gap description.
5. NEW RULE: For ANY new row you add to 'requirements' or 'documents', you MUST add a new key called "Source_Link" and set its value to the SIGNAL URL provided.
6. Do NOT modify the 'metadata' or 'identity' sections. Keep them exactly as they are.
7. ALL TEXT GENERATED MUST BE STRICTLY IN ENGLISH. No French.
8. Maintain the EXACT SAME JSON SCHEMA.

--- OUTPUT FORMAT ---
You must output STRICTLY valid JSON representing the fully updated Legal Card. Do not add any conversational text."""

    # On prépare le contexte pour l'IA
    user_prompt = f"=== SIGNAL URL (To use for Source_Link) ===\n{signal_url if signal_url else 'No URL provided'}\n\n"
    user_prompt += f"=== EXISTING LEGAL CARD ===\n{json.dumps(legal_card, indent=2)}\n\n"
    user_prompt += f"=== IDENTIFIED GAPS TO INTEGRATE ===\n{json.dumps(gap_analysis.get('gaps', []), indent=2)}\n"

    try:
        # On force la réponse en JSON natif pour éviter les erreurs de parsing
        result = call_gemini(gemini_key, system_prompt, user_prompt, force_json=True)
        
        # Nettoyage classique des balises markdown si l'IA en ajoute
        raw_text = result["text"].strip()
        if raw_text.startswith("```json"): 
            raw_text = raw_text[7:]
        if raw_text.startswith("```"): 
            raw_text = raw_text[3:]
        if raw_text.endswith("```"): 
            raw_text = raw_text[:-3]
            
        updated_card = json.loads(raw_text.strip())
        return updated_card
        
    except Exception as e:
        raise Exception(f"L'IA n'a pas pu générer la mise à jour : {str(e)}")
