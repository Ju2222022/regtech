import streamlit as st
import pandas as pd

st.set_page_config(page_title="Legal Card Editor | RegWatch", page_icon="📝", layout="wide")

def main():
    st.title("📝 Legal Card Editor")
    st.markdown("Manage your single source of truth for product compliance.")

    # ==========================================
    # HEADER : MATRIX SELECTION
    # ==========================================
    st.markdown("### 🎯 Card Selection")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.selectbox("Perimeter", ["Electronics & Measuring devices", "Mobility", "Apparel & Textile", "Heavy Equipment"])
    with col2:
        st.selectbox("Category", ["Audio", "Wearables", "E-Bikes", "Footwear"])
    with col3:
        st.selectbox("Sub-Category", ["Mp3 player", "Smartwatches", "Audio Headsets", "Running Shoes"])
    with col4:
        st.selectbox("Target Market", ["EU", "France", "USA", "China"])

    st.divider()

    # ==========================================
    # MAIN LAYOUT: 75% Editor / 25% Watch Tower Alerts
    # ==========================================
    main_col, side_col = st.columns([3, 1], gap="large")

    with main_col:
        # --- SECTION 1: IDENTITY ---
        st.subheader("1. Identity & Scope")
        st.text_area("Product Legal Definition", 
                     "\"Electrical and electronic equipment\" means equipment which is dependent on electric currents or electromagnetic fields in order to work properly...", 
                     height=80)
        st.text_input("Covered HS Codes (Customs)", "8527.13.00, 8519.81.00")
        
        st.markdown("<br>", unsafe_allow_html=True) # Spacer

        # --- SECTION 2: PRODUCT REQUIREMENTS (GENERIC TABLE) ---
        st.subheader("2. Technical & Product Requirements")
        st.markdown("Add all physical, chemical, or technical limits your product must respect.")
        
        req_df = pd.DataFrame([
            {"Type": "Chemical", "Parameter": "Lead (Pb)", "Limit": "Max 0.1% by weight", "Reference": "RoHS Directive"},
            {"Type": "Radio", "Parameter": "Transmission Power", "Limit": "Max 20mW", "Reference": "RED 2014/53/EU"},
            {"Type": "Safety", "Parameter": "Output Voltage", "Limit": "≤ 150 mV", "Reference": "EN 60065"}
        ])
        
        st.data_editor(
            req_df,
            column_config={
                "Type": st.column_config.SelectboxColumn(
                    "Requirement Type",
                    help="Categorize the requirement",
                    options=["Chemical", "Mechanical", "Electrical", "Radio", "Environmental", "Safety", "Other"],
                    required=True,
                ),
                "Parameter": st.column_config.TextColumn("Parameter / Substance", required=True),
                "Limit": st.column_config.TextColumn("Limit / Target", required=True),
                "Reference": st.column_config.TextColumn("Regulatory Reference")
            },
            num_rows="dynamic",
            use_container_width=True,
            key="req_editor"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECTION 3: MARKING & INFORMATION (GENERIC TABLE) ---
        st.subheader("3. Marking & Information")
        st.markdown("List all logos, warnings, and digital information required.")
        
        marking_df = pd.DataFrame([
            {"Placement": "On Product", "Requirement": "CE Marking", "Description": "Min 5mm height, visible and indelible.", "Mandatory": True},
            {"Placement": "On Packaging", "Requirement": "Triman Logo", "Description": "Info-tri mandatory for French market.", "Mandatory": True},
            {"Placement": "In Manual", "Requirement": "SAR Value", "Description": "Required if transmitting power > 20 mW.", "Mandatory": True},
            {"Placement": "E-commerce (Web)", "Requirement": "Recyclability Score", "Description": "Available digitally for 2 years (AGEC law).", "Mandatory": True}
        ])
        
        st.data_editor(
            marking_df,
            column_config={
                "Placement": st.column_config.SelectboxColumn(
                    "Placement",
                    options=["On Product", "On Packaging", "In Manual", "E-commerce (Web)", "Accompanying Document"],
                    required=True,
                ),
                "Requirement": st.column_config.TextColumn("Requirement", required=True),
                "Description": st.column_config.TextColumn("Details / Content"),
                "Mandatory": st.column_config.CheckboxColumn("Mandatory", default=True)
            },
            num_rows="dynamic",
            use_container_width=True,
            key="marking_editor"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECTION 4: MARKET ACCESS & DOCS ---
        st.subheader("4. Conformity Documents & Access")
        docs_df = pd.DataFrame([
            {"Document": "EU Declaration of Conformity", "Description": "Must be kept for 10 years, translated in all retail languages.", "Retention": "10 Years"},
            {"Document": "EMC Test Report", "Description": "From accredited laboratory (ISO 17025).", "Retention": "10 Years"}
        ])
        
        st.data_editor(
            docs_df,
            num_rows="dynamic",
            use_container_width=True,
            key="docs_editor"
        )
        
        st.divider()

        # --- HISTORY EXPANDER (Bottom) ---
        with st.expander("🕒 History", expanded=False):
            st.markdown("""
            * **2026-07-20** - Julien Dlubala - *Validated current version.*
            * **2025-11-14** - Manon Leplat - *Added Triman logo requirement for FR market packaging.*
            * **2025-02-01** - Julien Dlubala - *Initial card creation.*
            """)

    # ==========================================
    # SIDE PANEL: Watch Tower Alerts & Actions
    # ==========================================
    with side_col:
        st.button("💾 Save Legal Card", type="primary", use_container_width=True)
        st.caption("Last saved: Just now")
        
        st.divider()
        
        st.markdown("### 📡 Watch Tower Alerts")
        
        # Simulated Gap Alert
        with st.container(border=True):
            st.warning("⚠️ **Potential Gap Detected**")
            st.caption("Detected: Today")
            st.markdown("**[Draft] EU Battery Regulation** might impact your chemical limits (Substances).")
            st.button("🔍 Review Signal", use_container_width=True)

if __name__ == "__main__":
    main()
