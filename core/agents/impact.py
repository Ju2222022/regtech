import os
import json

def find_matching_legal_cards(signal_data):
    """
    Croise les métadonnées d'un signal entrant avec les fiches du référentiel local.
    Retourne une liste des données JSON des fiches correspondantes.
    """
    # Chemin vers le dossier de sauvegarde défini dans 3_Editor.py
    base_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'legal_cards')
    matched_cards = []
    
    # 1. Extraction des marchés (gère le cas où il y a plusieurs pays comme "EU, France")
    markets_string = signal_data.get('market', '')
    markets = [m.strip() for m in markets_string.split(',') if m.strip()]
    
    # 2. Extraction des catégories
    categories = signal_data.get('categories', [])
    
    # 3. Recherche des combinaisons
    for market in markets:
        for category in categories:
            # On recrée la nomenclature exacte utilisée dans l'éditeur
            safe_cat = str(category).replace(" ", "_").replace("/", "-")
            safe_market = str(market).replace(" ", "_").replace("/", "-")
            
            filename = f"{safe_cat}_{safe_market}.json"
            file_path = os.path.join(base_dir, filename)
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        card_data = json.load(f)
                        matched_cards.append({
                            "filename": filename,
                            "market": market,
                            "category": category,
                            "data": card_data
                        })
                except Exception as e:
                    print(f"Erreur de lecture pour la fiche {filename}: {e}")
                    
    return matched_cards

from core.agents.watcher import call_gemini

def analyze_gap_with_gemini(gemini_key: str, signal_data: dict, legal_card_data: dict) -> dict:
    """
    Envoie le signal et la fiche de référence à Gemini pour une analyse d'écart (Gap Analysis).
    """
    system_prompt = """You are a Regulatory Affairs Expert.
Your task is to perform a strict Gap Analysis between a NEW regulatory signal and an EXISTING internal product compliance framework (Legal Card).

--- INSTRUCTIONS ---
1. Read the new regulatory signal summary.
2. Read the existing Legal Card (Requirements, Markings, Documents).
3. Compare them carefully. 
   - If the new regulation introduces a limit, a marking, or a document that is NOT present in the existing card, it is a DELTA.
   - If the existing card already covers the requirements described in the signal, it is COMPLIANT.

--- OUTPUT FORMAT ---
You must output STRICTLY in JSON format with the following structure:
{
    "status": "🔴 Delta Detected" or "🟢 Already Compliant" or "⚪ Unclear / Manual Check Required",
    "analysis": "A brief explanation (2-3 sentences) of your comparison.",
    "gaps": [
        {
            "type": "Requirement | Marking | Document", 
            "description": "Clear description of what is missing or needs updating in the current Legal Card."
        }
    ]
}"""

    # Préparation des données pour l'IA
    user_prompt = f"=== NEW REGULATORY SIGNAL ===\n"
    user_prompt += f"Title: {signal_data.get('title', 'N/A')}\n"
    user_prompt += f"Summary: {signal_data.get('summary', 'N/A')}\n\n"
    
    user_prompt += f"=== EXISTING LEGAL CARD (JSON) ===\n"
    user_prompt += json.dumps(legal_card_data, indent=2)

    try:
        # On utilise force_json=True pour garantir que Gemini renvoie bien notre structure
        result = call_gemini(gemini_key, system_prompt, user_prompt, force_json=True)
        
        # Nettoyage de la réponse au cas où Gemini ajoute des balises Markdown
        raw_text = result["text"].strip()
        if raw_text.startswith("```json"): 
            raw_text = raw_text[7:]
        if raw_text.startswith("```"): 
            raw_text = raw_text[3:]
        if raw_text.endswith("```"): 
            raw_text = raw_text[:-3]
            
        return json.loads(raw_text.strip())
        
    except Exception as e:
        return {
            "status": "⚠️ Error",
            "analysis": f"L'analyse IA a échoué : {str(e)}",
            "gaps": []
        }
