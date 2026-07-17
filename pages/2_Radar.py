import streamlit as st
import sys
import os

# Connexion au backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.referential import ReferentialManager
from core.agents.classifier import ProductClassifierAgent

st.set_page_config(page_title="Product Screening | RegWatch", page_icon="🎯", layout="wide")

def main():
    st.title("🎯 Product Screening & Risk Mapping")
    st.markdown("Describe your product to instantly identify applicable regulatory frameworks and deliverables.")

    # Initialisation des moteurs
    ref_manager = ReferentialManager()
    agent = ProductClassifierAgent(ref_manager)

    # Espace réservé pour la V2 (Scraping Decathlon & CSV)
    with st.expander("🛠️ Decathlon Expert Mode (Tavily Web Scraping & Bulk CSV) - Coming Soon"):
        st.info("This module will be activated in the next step to fetch product data via Model Codes and process CSV batches.")

    st.subheader("1. Describe your Product")
    
    with st.form("screening_form"):
        product_desc = st.text_area(
            "Product Brief, Technical Specs or Use Case", 
            placeholder="e.g., We are developing a new running smartwatch with an OLED screen, Bluetooth connectivity, and a CR2032 coin cell battery...",
            height=150
        )
        
        submitted = st.form_submit_button("Launch Regulatory Analysis", type="primary")

    # ==========================================
    # AFFICHAGE DU RAPPORT ONE-PAGE
    # ==========================================
    if submitted:
        if not product_desc.strip():
            st.error("Please provide a product description.")
        else:
            with st.spinner("🧠 AI is mapping product specs to your ontology..."):
                
                # Appel à notre Agent Gemini
                result = agent.analyze_product(product_desc)
                
                if "error" in result:
                    st.error(f"Analysis Failed: {result['error']}")
                else:
                    st.success("Analysis Complete!")
                    st.divider()
                    
                    # 1. Le résumé de l'IA (Prouver qu'elle a compris)
                    st.markdown("### 🤖 AI Product Understanding")
                    st.info(result.get("analyzed_product", "No summary provided by the AI."))
                    
                    st.divider()
                    
                    # 2. Le Radar et le Plan d'Action
                    st.markdown("### 📡 Radar: Applicable Categories")
                    matched = result.get("matched_categories", [])
                    
                    if not matched:
                        st.warning("No specific regulatory category was detected for this product based on your current Settings.")
                    else:
                        for match in matched:
                            cat_id = match.get("category_id")
                            score = match.get("confidence_score", "UNKNOWN")
                            justification = match.get("justification", "No justification provided.")
                            
                            # Récupérer les détails complets depuis notre base de données
                            cat_details = ref_manager.get_category_by_id(cat_id)
                            label = cat_details.get("category_label", cat_id) if cat_details else cat_id
                            
                            # Création d'une alerte visuelle selon le niveau de confiance
                            confidence_icon = "🟢" if score == "HIGH" else "🟠" if score == "MEDIUM" else "🔴"
                            
                            with st.expander(f"{confidence_icon} {label} (Confidence: {score})", expanded=True):
                                st.markdown(f"**AI Justification:** *{justification}*")
                                
                                if cat_details:
                                    st.divider()
                                    col_fw, col_deliv = st.columns(2)
                                    
                                    with col_fw:
                                        st.markdown("**⚖️ Reference Legal Framework**")
                                        frameworks = cat_details.get("reference_legal_framework", [])
                                        if frameworks:
                                            for fw in frameworks:
                                                st.markdown(f"- {fw}")
                                        else:
                                            st.caption("No frameworks defined in Settings.")
                                            
                                    with col_deliv:
                                        st.markdown("**📋 Expected Deliverables**")
                                        deliverables = cat_details.get("expected_deliverables", [])
                                        if deliverables:
                                            for dl in deliverables:
                                                st.markdown(f"- {dl}")
                                        else:
                                            st.caption("No deliverables defined in Settings.")

if __name__ == "__main__":
    main()
