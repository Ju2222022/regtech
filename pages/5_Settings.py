import streamlit as st
import sys
import os

# Connexion au moteur backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.referential import ReferentialManager

st.set_page_config(page_title="Settings | RegWatch", page_icon="⚙️", layout="wide")

def main():
    st.title("⚙️ Platform Settings (Super Admin)")
    st.markdown("Manage your ontology structure, tenant profile, and global logic.")

    # Initialisation du gestionnaire de données
    ref_manager = ReferentialManager()
    data = ref_manager.data

    # On passe l'Ontologie en premier onglet car c'est le cœur du métier
    tab1, tab2, tab3 = st.tabs(["🗂️ Ontology Builder", "🏢 Tenant Profile", "🌐 Global Rules"])

   # ---------------------------------------------------------
    # ONGLET 1 : ONTOLOGIE (Vue Arborescente et Édition)
    # ---------------------------------------------------------
    with tab1:
        st.subheader("Ontology Tree View")
        st.markdown("Your regulatory perimeters and sub-categories are grouped by internal owner.")
        
        # Initialisation du mode édition dans le cache de la page
        if "editing_category" not in st.session_state:
            st.session_state["editing_category"] = None

        categories = ref_manager.get_categories()
        
        # === BLOC ÉDITION (S'affiche uniquement si on a cliqué sur Modify) ===
        if st.session_state["editing_category"]:
            cat_to_edit = ref_manager.get_category_by_id(st.session_state["editing_category"])
            
            if cat_to_edit:
                st.warning(f"✏️ **Editing Mode:** {cat_to_edit.get('category_label')} ({cat_to_edit.get('category_id')})")
                
                with st.form("edit_category_form"):
                    col_macro, col_group = st.columns(2)
                    with col_macro:
                        edit_perimeter = st.text_input("Macro Perimeter", value=cat_to_edit.get('perimeter', ''))
                    with col_group:
                        edit_group = st.text_input("Owner Group", value=cat_to_edit.get('internal_owner_group', ''))
                        
                    col_label, col_id = st.columns(2)
                    with col_label:
                        edit_label = st.text_input("Sub-Category Label", value=cat_to_edit.get('category_label', ''))
                    with col_id:
                        # L'ID est désactivé pour éviter de casser la base de données
                        st.text_input("Unique ID (Cannot be changed)", value=cat_to_edit.get('category_id', ''), disabled=True)
                    
                    edit_def = st.text_area("Business Definition", value=cat_to_edit.get('business_definition', ''))
                    
                    st.markdown("**Matching Configuration (Comma separated)**")
                    config = cat_to_edit.get("matching_engine_config", {})
                    # Transformation des listes en texte pour le formulaire
                    str_strict = ", ".join(config.get("strict_technical_attributes", []))
                    str_fuzzy = ", ".join(config.get("fuzzy_keywords_fallbacks", []))
                    
                    edit_strict = st.text_area("Strict Attributes", value=str_strict)
                    edit_fuzzy = st.text_area("Fuzzy Keywords", value=str_fuzzy)
                    
                    col_submit, col_cancel = st.columns([1, 5])
                    with col_submit:
                        submitted = st.form_submit_button("💾 Save Changes", type="primary")
                    with col_cancel:
                        canceled = st.form_submit_button("❌ Cancel")
                        
                    if canceled:
                        st.session_state["editing_category"] = None
                        st.rerun()
                        
                    if submitted:
                        # Reconstruction de la fiche avec les nouvelles données
                        cat_to_edit["perimeter"] = edit_perimeter
                        cat_to_edit["internal_owner_group"] = edit_group
                        cat_to_edit["category_label"] = edit_label
                        cat_to_edit["business_definition"] = edit_def
                        
                        # Re-transformation du texte en listes propres pour le JSON
                        cat_to_edit["matching_engine_config"]["strict_technical_attributes"] = [x.strip() for x in edit_strict.split(",") if x.strip()]
                        cat_to_edit["matching_engine_config"]["fuzzy_keywords_fallbacks"] = [x.strip() for x in edit_fuzzy.split(",") if x.strip()]
                        
                        if ref_manager.update_category(cat_to_edit):
                            st.session_state["editing_category"] = None
                            st.success("Successfully updated!")
                            st.rerun()
                st.divider()

        # === BLOC AFFICHAGE NORMAL (Caché si on est en édition) ===
        elif not categories:
            st.info("No categories defined. Start building your ontology below.")
        else:
            # 1. Regroupement intelligent
            tree = {}
            for cat in categories:
                perimeter = cat.get('perimeter', 'Uncategorized Perimeter')
                group = cat.get('internal_owner_group', 'Unassigned Group')
                
                if perimeter not in tree:
                    tree[perimeter] = {}
                if group not in tree[perimeter]:
                    tree[perimeter][group] = []
                    
                tree[perimeter][group].append(cat)
            
            # 2. Affichage dynamique
            for perimeter_name, groups in tree.items():
                st.markdown(f"## 🌍 {perimeter_name}")
                
                for group_name, sub_categories in groups.items():
                    st.markdown(f"#### 📁 {group_name}")
                    
                    for cat in sub_categories:
                        label = cat.get('category_label', 'Unnamed')
                        cat_id = cat.get('category_id', 'NO_ID')
                        
                        with st.expander(f"📄 {label}  |  ID: {cat_id}"):
                            st.write(f"**Definition:** {cat.get('business_definition', '')}")
                            st.write(f"**Scope:** {cat.get('operational_scope', '')}")
                            
                            st.divider()
                            col_edit, col_dup, col_del, _ = st.columns([1, 1, 1, 4])
                            with col_edit:
                                # ACTION : Passer en mode édition
                                if st.button("✏️ Modify", key=f"edit_{cat_id}"):
                                    st.session_state["editing_category"] = cat_id
                                    st.rerun()
                            with col_dup:
                                st.button("📑 Duplicate", key=f"dup_{cat_id}")
                            with col_del:
                                # ACTION : Supprimer
                                if st.button("🗑️ Delete", key=f"del_{cat_id}", type="primary"):
                                    if ref_manager.delete_category(cat_id):
                                        st.rerun()
                    
                st.divider()
        
        # 3. Formulaire d'ajout (Caché pendant l'édition pour ne pas polluer l'écran)
        if not st.session_state["editing_category"]:
            st.subheader("➕ Add New Sub-Category")
            with st.expander("Open Category Creator Form"):
                with st.form("add_category_form"):
                    col_macro, col_group = st.columns(2)
                    with col_macro:
                        new_perimeter = st.text_input("Macro Perimeter", placeholder="e.g., Electronics, Textile, Food...")
                    with col_group:
                        new_group = st.text_input("Owner Group", placeholder="e.g., Optical & Lighting Technology")
                        
                    col_label, col_id = st.columns(2)
                    with col_label:
                        new_label = st.text_input("Sub-Category Label", placeholder="e.g., Laser Devices")
                    with col_id:
                        new_id = st.text_input("Unique ID", placeholder="e.g., SUB_CAT_LASER")
                    
                    submitted = st.form_submit_button("Create Skeleton", type="primary")
                    
                    if submitted:
                        if not new_id or not new_label:
                            st.error("Error: ID and Label are required.")
                        else:
                            new_cat = {
                                "perimeter": new_perimeter if new_perimeter else "Uncategorized Perimeter",
                                "internal_owner_group": new_group if new_group else "Unassigned Group",
                                "category_id": new_id,
                                "category_label": new_label,
                                "business_definition": "Definition to be added...",
                                "operational_scope": "Scope to be defined...",
                                "matching_engine_config": {"strict_technical_attributes": [], "fuzzy_keywords_fallbacks": []},
                                "expected_deliverables": [],
                                "reference_legal_framework": [],
                                "automated_watcher_queries": []
                            }
                            if ref_manager.add_category(new_cat):
                                st.rerun()
                            else:
                                st.error("Error: This ID already exists.")
                    
    # ---------------------------------------------------------
    # ONGLET 2 : PROFIL (Désormais éditable)
    # ---------------------------------------------------------
    with tab2:
        st.subheader("Tenant Information")
        profile = data.get("tenant_profile", {})
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Company Name", value=profile.get("company_name", ""))
        with col2:
            st.text_input("Industry Sector", value=profile.get("industry_sector", ""))
        st.button("💾 Save Profile Settings")

    # ---------------------------------------------------------
    # ONGLET 3 : RÈGLES GLOBALES (Désormais éditable)
    # ---------------------------------------------------------
    with tab3:
        st.subheader("Global Routing Rules")
        rules = data.get("global_routing_rules", {})
        
        st.checkbox("Enable Mandatory Fallback Category", value=rules.get("has_mandatory_fallback", False))
        st.text_input("Fallback Category ID", value=rules.get("mandatory_fallback_category_id", ""))
        st.checkbox("Allow Multi-labeling (Overlaps)", value=rules.get("allow_multi_labeling", True))
        st.button("💾 Save Engine Rules")

if __name__ == "__main__":
    main()
