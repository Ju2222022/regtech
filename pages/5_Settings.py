import streamlit as st
import sys
import os

# Permet d'importer les modules du dossier 'core' situé au niveau parent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.referential import ReferentialManager

st.set_page_config(page_title="Settings | RegWatch", page_icon="⚙️", layout="wide")

def main():
    st.title("⚙️ Platform Settings")
    st.markdown("Configure your tenant profile, global routing rules, and product ontology.")

    # Initialisation du moteur de données
    ref_manager = ReferentialManager()
    data = ref_manager.data

    # Création des onglets pour une interface épurée
    tab1, tab2, tab3 = st.tabs(["🏢 Tenant Profile", "🗂️ Ontology Management", "🌐 Global Rules"])

    # ONGLET 1 : Profil du client
    with tab1:
        st.subheader("Tenant Information")
        profile = data.get("tenant_profile", {})
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Company Name", value=profile.get("company_name", ""), disabled=True)
        with col2:
            st.text_input("Industry Sector", value=profile.get("industry_sector", ""), disabled=True)
        st.caption("Contact support to update your core tenant identity.")

    # ONGLET 2 : L'Ontologie (Le cœur du métier)
    with tab2:
        st.subheader("Defined Ontology")
        st.markdown("Manage your regulatory categories, ownership, and semantic triggers.")
        
        categories = ref_manager.get_categories()
        
        if not categories:
            st.info("No categories defined yet in your ontology.")
        else:
            # Affichage dynamique sous forme de blocs accordéons
            for cat in categories:
                label = cat.get('category_label', 'Unnamed Category')
                cat_id = cat.get('category_id', 'NO_ID')
                criticality = cat.get('default_criticality', 'MEDIUM')
                
                # Code couleur visuel selon la criticité
                icon = "🔴" if criticality == "HIGH" else "🟠" if criticality == "MEDIUM" else "🟢"
                
                with st.expander(f"{icon} {label} ({cat_id})"):
                    st.write(f"**Internal Owner:** {cat.get('internal_owner_group', 'Not Assigned')}")
                    st.write(f"**Scope:** {cat.get('operational_scope', '')}")
                    
                    st.divider()
                    col_trig, col_deliv = st.columns(2)
                    
                    with col_trig:
                        st.markdown("**🔍 Semantic Triggers**")
                        triggers = cat.get("matching_engine_config", {})
                        st.json(triggers)
                        
                    with col_deliv:
                        st.markdown("**📋 Expected Deliverables**")
                        for item in cat.get("expected_deliverables", []):
                            st.markdown(f"- {item}")
                            
        st.divider()
        st.subheader("➕ Add New Category")
        st.info("The interactive category builder will be implemented in the next iteration. The backend engine is already configured to accept new payloads.")

    # ONGLET 3 : Règles globales de routage
    with tab3:
        st.subheader("Global Routing Rules")
        rules = data.get("global_routing_rules", {})
        
        st.checkbox("Enable Mandatory Fallback Category", value=rules.get("has_mandatory_fallback", False), disabled=True)
        st.text_input("Fallback Category ID", value=rules.get("mandatory_fallback_category_id", ""), disabled=True)
        st.checkbox("Allow Multi-labeling (Overlaps)", value=rules.get("allow_multi_labeling", True), disabled=True)

if __name__ == "__main__":
    main()
