import streamlit as st
import pandas as pd

st.set_page_config(page_title="Legal Card Editor | RegWatch", page_icon="📝", layout="wide")

def main():
    st.title("📝 Legal Card Editor")
    st.markdown("Manage and update your single source of truth for product compliance.")

    # ==========================================
    # HEADER : MATRIX SELECTION
    # ==========================================
    st.markdown("### 🎯 Card Selection")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.selectbox("Perimeter", ["Electronics & Measuring devices", "Mobility"])
    with col2:
        st.selectbox("Category", ["Audio", "Wearables", "E-Bikes"])
    with col3:
        st.selectbox("Sub-Category", ["Mp3 player", "Smartwatches", "Audio Headsets"])
    with col4:
        st.selectbox("Target Market", ["EU", "France", "USA", "China"])

    st.divider()

    # ==========================================
    # MAIN LAYOUT: 80% Editor / 20% Context Panel
    # ==========================================
    main_col, side_col = st.columns([3, 1], gap="large")

    with main_col:
        # The 4 Pillars using Tabs
        tabs = st.tabs([
            "📌 1. Identity & Scope", 
            "⚙️ 2. Tech & Chem Specs", 
            "🏷️ 3. Marking & Info", 
            "🌍 4. Market Access"
        ])
        
        # PILLAR 1
        with tabs[0]:
            st.subheader("Identity & Scope")
            st.text_area("Product Legal Definition", 
                         "\"Electrical and electronic equipment\" means equipment which is dependent on electric currents or electromagnetic fields in order to work properly...", 
                         height=100)
            st.text_input("Covered HS Codes (Customs)", "8527.13.00, 8519.81.00")
            st.info("💡 **Note:** If the product has a radiocommunication function, it might crossover with the 'Electronic equipment using bluetooth' card.")
            
        # PILLAR 2
        with tabs[1]:
            st.subheader("Technical & Chemical Specifications")
            
            st.markdown("##### 🧪 Chemical Restrictions (Substances)")
            # Using st.data_editor to allow adding/removing rows dynamically like in Excel
            chem_df = pd.DataFrame([
                {"Substance": "Lead (Pb)", "Limit": "Max 0.1% by weight", "Regulation": "RoHS Directive"}, 
                {"Substance": "Cadmium (Cd)", "Limit": "Max 0.01% by weight", "Regulation": "RoHS Directive"}
            ])
            st.data_editor(chem_df, num_rows="dynamic", use_container_width=True, key="chem_editor")
            
            st.markdown("##### 📏 Technical Standards (Design & Testing)")
            tech_df = pd.DataFrame([
                {"Standard Ref": "EN 301 489", "Type": "EMC", "Mandatory": True, "Notes": "Harmonized standard"},
                {"Standard Ref": "EN 60065", "Type": "Acoustic Safety", "Mandatory": True, "Notes": "Output voltage ≤ 150 mV"}
            ])
            st.data_editor(tech_df, num_rows="dynamic", use_container_width=True, key="tech_editor")
            
        # PILLAR 3
        with tabs[2]:
            st.subheader("Marking & Information Requirements")
            st.markdown("Organize requirements by physical placement to generate accurate operational briefs.")
            
            # Sub-tabs to avoid duplicating instructions
            marking_tabs = st.tabs(["📦 On Product", "🏷️ On Packaging", "📖 In Manual", "💻 E-commerce"])
            
            with marking_tabs[0]:
                st.checkbox("CE Marking (min 5mm)", value=True)
                st.checkbox("WEEE Crossed-out Bin", value=True)
                st.checkbox("Manufacturer Name & Address", value=True)
                st.text_area("Specific Warnings (Product)", "If French market: \"At full power, prolonged listening to the music player may damage the ear of the user\" under specific pictogram.")
                
            with marking_tabs[1]:
                st.markdown("*Packaging specific requirements...*")
                st.checkbox("Triman Logo (France)", value=True)
                
            with marking_tabs[2]:
                st.markdown("*Manual specific requirements...*")
                st.text_area("Mandatory Sentences", "The product is conformed to the RED directive 2014/53/EU. The EU declaration of conformity is available at [link]")
                
            with marking_tabs[3]:
                st.markdown("*Online display requirements...*")
                st.text_area("Digital Info", "AGEC Law: Recyclability score and repair info must be available digitally for 2 years after last unit is placed on market.")

        # PILLAR 4
        with tabs[3]:
            st.subheader("Market Access & Operations")
            st.multiselect("Required Conformity Documents", 
                           ["EU Declaration of Conformity", "EMC Test Reports", "RoHS Test Reports", "Safety Risk Assessment"],
                           default=["EU Declaration of Conformity", "EMC Test Reports"])
            st.text_area("Importation Rules", "Decathlon assumes importer obligations: verify technical documentation, ensure legal marking, and check Safety Business Gateway.")

    # ==========================================
    # SIDE PANEL: Context & Actions
    # ==========================================
    with side_col:
        st.markdown("### 📊 Metadata")
        st.success("**Status:** Validated ✅")
        st.caption("**Owner:** Julien Dlubala")
        st.caption("**Last updated:** 2026-07-20")
        
        st.divider()
        
        st.markdown("### 🔔 Watch Tower")
        st.warning("⚠️ **1 Pending Signal**\n\n[Draft] EU Battery Regulation might impact this card's chemical limits.")
        st.button("Review Gap", use_container_width=True)
        
        st.divider()
        
        st.markdown("### 🤖 Assistant AI")
        st.markdown("*Distribute requirements to operational teams:*")
        
        if st.button("📤 Generate Packaging Brief", type="primary", use_container_width=True):
            st.toast("IA is extracting packaging logos and warnings...", icon="⏳")
            
        if st.button("📤 Generate R&D Brief", use_container_width=True):
            st.toast("IA is extracting chemical limits and testing standards...", icon="⏳")
            
        st.divider()
        st.button("💾 Save Card", type="secondary", use_container_width=True)

if __name__ == "__main__":
    main()
