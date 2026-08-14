import os
import json
from core.agents.watcher import call_gemini

def find_matching_legal_cards(signal_data):
    """
    Recherche les fiches réglementaires correspondantes en lisant directement 
    les métadonnées internes des fichiers JSON pour respecter strictement l'ontologie.
    """
    base_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'legal_cards')
    matched_cards = []
    
    if not os.path.exists(base_dir):
        return matched_cards
        
    # 1. Nettoyage des critères de recherche issus du signal
    markets_string = signal_data.get('market', '')
    signal_markets = [m.strip().lower() for m in markets_string.split(',') if m.strip()]
    
    # Watch Tower enregistre ici soit les catégories, soit les sous-catégories sélectionnées
    signal_cats = [str(c).lower().strip() for c in signal_data.get('categories', [])]
    
    # 2. On scanne le contenu de tous les fichiers JSON
    for filename in os.listdir(base_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(base_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    card_data = json.load(f)
                    
                meta = card_data.get('metadata', {})
                card_market = str(meta.get('market', '')).lower().strip()
                card_cat = str(meta.get('category', '')).lower().strip()
                card_subcat = str(meta.get('sub_category', '')).lower().strip()
                
                # --- Vérification du Marché (Target Market) ---
                market_match = False
                for sm in signal_markets:
                    if sm in card_market or card_market in sm:
                        market_match = True
                        break
                        
                # --- Vérification de l'Ontologie (Category ou Sub-Category) ---
                cat_match = False
                for sc in signal_cats:
                    # On accepte une correspondance partielle pour ignorer les soucis de parenthèses
                    if card_cat and (sc in card_cat or card_cat in sc):
                        cat_match = True
                    if card_subcat and (sc in card_subcat or card_subcat in sc):
                        cat_match = True

                # Si le marché et le noeud de l'ontologie correspondent, c'est la bonne fiche !
                if market_match and cat_match:
                    # On évite les doublons au cas où
                    if not any(c['filename'] == filename for c in matched_cards):
                        matched_cards.append({
                            "filename": filename,
                            "data": card_data
                        })
            except Exception as e:
                print(f"⚠️ Erreur de lecture de {filename}: {e}")
                
    return matched_cards

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
