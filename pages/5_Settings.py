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
        
        categories = ref_manager.get_categories()
        
        if not categories:
            st.info("No categories defined. Start building your ontology below.")
        else:
            # 1. Regroupement intelligent par Périmètre / Équipe
            folders = {}
            for cat in categories:
                perimeter = cat.get('internal_owner_group', 'Uncategorized Perimeter')
                if perimeter not in folders:
                    folders[perimeter] = []
                folders[perimeter].append(cat)
            
            # 2. Affichage des "Dossiers" et "Sous-Dossiers"
            for perimeter_name, sub_categories in folders.items():
                st.markdown(f"### 📁 {perimeter_name}") # Le dossier principal
                
                for cat in sub_categories:
                    label = cat.get('category_label', 'Unnamed')
                    cat_id = cat.get('category_id', 'NO_ID')
                    
                    # Le tiroir de la catégorie
                    with st.expander(f"📄 {label}  |  ID: {cat_id}"):
                        st.write(f"**Definition:** {cat.get('business_definition', '')}")
                        st.write(f"**Scope:** {cat.get('operational_scope', '')}")
                        
                        st.divider()
                        col_trig, col_deliv = st.columns(2)
                        
                        with col_trig:
                            st.markdown("**🔍 Semantic Triggers**")
                            st.json(cat.get("matching_engine_config", {}))
                            
                        with col_deliv:
                            st.markdown("**📋 Expected Deliverables**")
                            for item in cat.get("expected_deliverables", []):
                                st.markdown(f"- {item}")
                        
                        st.divider()
                        # 3. La barre d'actions de l'Admin
                        col_edit, col_dup, col_del, _ = st.columns([1, 1, 1, 4])
                        with col_edit:
                            st.button("✏️ Edit", key=f"edit_{cat_id}")
                        with col_dup:
                            st.button("📑 Duplicate", key=f"dup_{cat_id}")
                        with col_del:
                            # Utilisation du type "primary" pour le bouton supprimer (rouge dans Streamlit)
                            st.button("🗑️ Delete", key=f"del_{cat_id}", type="primary")

        st.divider()
        
        # 4. Le module d'ajout (Formulaire interactif)
        st.subheader("➕ Add New Sub-Category")
        with st.expander("Open Category Creator Form"):
            with st.form("add_category_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_group = st.text_input("Perimeter / Owner Group", placeholder="e.g., Optical & Lighting Technology")
                    new_label = st.text_input("Sub-Category Label", placeholder="e.g., Laser Devices")
                with col2:
                    new_id = st.text_input("Unique ID", placeholder="e.g., SUB_CAT_LASER")
                    new_framework = st.text_input("Base Framework", placeholder="e.g., Laser Safety Class 1")
                
                st.markdown("**Matching Configuration (Comma separated)**")
                new_strict = st.text_area("Strict Attributes", placeholder="laser, telemeter, optical_sensor")
                
                submitted = st.form_submit_button("Create & Save to Engine", type="primary")
                if submitted:
                    st.success("Form submitted! (Backend save function will be wired next).")

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
