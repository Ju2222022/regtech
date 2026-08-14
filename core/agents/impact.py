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
