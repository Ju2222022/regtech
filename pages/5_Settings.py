import streamlit as st
import sys
import os
import json
from collections import defaultdict

# Connexion au backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.referential import ReferentialManager

st.set_page_config(page_title="Settings | RegWatch", page_icon="⚙️", layout="wide")

def main():
    st.title("⚙️ Regulatory Ontology Settings")
    st.markdown("Manage your compliance perimeters, categories, and sub-categories.")

    ref_manager = ReferentialManager()
    categories = ref_manager.get_categories()

    # ==========================================
    # LOGIQUE DE GROUPEMENT (Mise à jour des variables)
    # ==========================================
    # On groupe d'abord par "Macro Perimeter", puis par "Category Label"
    grouped_data = defaultdict(lambda: defaultdict(list))
    
    for cat in categories:
        perimeter = cat.get("macro_perimeter", "Uncategorized Perimeter")
        
        # Note : On lit la clé JSON "internal_owner_group" si elle s'appelle encore comme ça dans ta base, 
        # mais on la stocke dans une variable propre : "category_label"
        category_label = cat.get("internal_owner_group", "Uncategorized Category") 
        
        grouped_data[perimeter][category_label].append(cat)

    # ==========================================
    # AFFICHAGE DE L'ONTOLOGIE
    # ==========================================
    for perimeter, categories_in_perimeter in grouped_data.items():
        st.markdown(f"## 🌍 {perimeter}")
        
        for category_label, sub_categories in categories_in_perimeter.items():
            st.markdown(f"### 📁 {category_label}")
            
            for sub_cat in sub_categories:
                sub_cat_label = sub_cat.get("category_label", "Unknown Label")
                sub_cat_id = sub_cat.get("category_id", "UNKNOWN_ID")
                
                # Affichage simple de la sous-catégorie
                st.markdown(f"> 📄 {sub_cat_label} | ID: {sub_cat_id}")
                
        st.divider()

    # ==========================================
    # FORMULAIRE D'AJOUT
    # ==========================================
    st.markdown("### ➕ Add New Sub-Category")
    
    with st.expander("Open Category Creator Form", expanded=False):
        with st.form("new_category_form"):
            
            # Variables de colonnes renommées pour la cohérence
            col_macro, col_category, col_label = st.columns(3)
            
            with col_macro:
                new_perimeter = st.text_input("Perimeter", placeholder="e.g., Electronics")
            with col_category:
                new_category = st.text_input("Category Label", placeholder="e.g., Energy Storage")
            with col_label:
                new_label = st.text_input("Sub-Category Label", placeholder="e.g., Coin Cells & Button Batteries")
            
            submitted = st.form_submit_button("Create Skeleton", type="primary")
            
            if submitted:
                if not new_label or not new_category:
                    st.error("Please fill at least the Category Label and Sub-Category Label.")
                else:
                    # Génération d'un ID basique
                    generated_id = f"SUB_CAT_{new_label.replace(' ', '_').upper()}"
                    
                    # Création du nouveau dictionnaire
                    new_entry = {
                        "category_id": generated_id,
                        "macro_perimeter": new_perimeter,
                        "internal_owner_group": new_category, # On garde la clé JSON attendue par ton backend
                        "category_label": new_label,
                        "business_definition": "",
                        "matching_engine_config": {
                            "strict_technical_attributes": [],
                            "fuzzy_keywords_fallbacks": []
                        },
                        "reference_legal_framework": [],
                        "expected_deliverables": []
                    }
                    
                    # Ici tu pourras brancher la fonction de sauvegarde de ton ReferentialManager
                    # ex: ref_manager.add_category(new_entry)
                    
                    st.success(f"Skeleton created for '{new_label}'! (ID: {generated_id})")
                    st.info("Backend connection to save this entry is ready to be wired.")

if __name__ == "__main__":
    main()
