import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Legal Card Editor | RegWatch", page_icon="📝", layout="wide")

# ==========================================
# DATA LOADING
# ==========================================
@st.cache_data
def get_active_countries():
    """Extract unique countries dynamically from the Regulatory Pool."""
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'regulatory_pool.csv')
        df = pd.read_csv(csv_path)
        if 'Geographic Zone' in df.columns:
            return sorted(df['Geographic Zone'].dropna().unique().tolist())
        return ["EU", "France", "USA", "China"]
    except Exception:
        return ["EU", "France", "USA", "China"]

@st.cache_data
def get_ontology_data():
    """Extract full hierarchical data from the Default Ontology."""
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'default_ontology.csv')
        df = pd.read_csv(csv_path)
        return df
    except Exception:
        return pd.DataFrame(columns=["perimeter", "category_label", "sub_category_label"])

def main():
    st.title("📝 Legal Card Editor")
    st.markdown("Manage your single source of truth for product compliance.")

    # ==========================================
    # HEADER : DYNAMIC MATRIX SELECTION
    # ==========================================
    st.markdown("### 🎯 Card Selection")
    
    ontology_df = get_ontology_data()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # PERIMETER
        all_perimeters = sorted(ontology_df['perimeter'].dropna().unique().tolist()) if 'perimeter' in ontology_df.columns else ["Electronics"]
        selected_perimeter = st.selectbox("Perimeter", all_perimeters)
        
    with col2:
        # CATEGORY (Filtered by Perimeter)
        filtered_cats = ontology_df[ontology_df['perimeter'] == selected_perimeter] if 'perimeter' in ontology_df.columns else ontology_df
        all_categories = sorted(filtered_cats['category_label'].dropna().unique().tolist()) if 'category_label' in filtered_cats.columns else ["Audio"]
        selected_category = st.selectbox("Category", all_categories)
        
    with col3:
        # SUB-CATEGORY (Filtered by Category)
        filtered_subcats = filtered_cats[filtered_cats['category_label'] == selected_category] if 'category_label' in filtered_cats.columns else filtered_cats
        all_subcategories = sorted(filtered_subcats['sub_category_label'].dropna().unique().tolist()) if 'sub_category_label' in filtered_subcats.columns else ["Mp3 player"]
        selected_subcategory = st.selectbox("Sub-Category", all_subcategories)

    with col4:
        # TARGET MARKET (From Regulatory Pool)
        available_countries = get_active_countries()
        selected_market = st.selectbox("Target Market", available_countries)

    st.divider()

    # ==========================================
    # MAIN LAYOUT: 75% Editor / 25% Watch Tower Alerts
    # ==========================================
    main_col, side_col = st.columns([3, 1], gap="large")

    with main_col:
        # --- SECTION 1: IDENTITY ---
        st.subheader("1. Identity & Scope")
        st.text_area("Product Legal Definition", 
                     "Enter the official legal definition for this product category...", 
                     height=80)
        st.text_input("Covered HS Codes (Customs)", "Ex: 8527.13.00, 8519.81.00")
        
        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECTION 2: PRODUCT REQUIREMENTS (GENERIC TABLE) ---
        st.subheader("2. Technical & Product Requirements")
        st.markdown("Add all physical, chemical, or technical limits your product must respect.")
        
        req_df = pd.DataFrame([
            {"Type": "Chemical", "Parameter": "", "Limit": "", "Reference": ""}
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
            {"Placement": "On Product", "Requirement": "", "Description": "", "Mandatory": True}
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
            {"Document": "", "Description": "", "Retention": ""}
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
            * **2026-07-22** - Julien Dlubala - *Initial card creation.*
            """)

    # ==========================================
    # SIDE PANEL: Watch Tower Alerts & Actions
    # ==========================================
    with side_col:
        st.button("💾 Save Legal Card", type="primary", use_container_width=True)
        st.caption("Status: Draft")
        
        st.divider()
        
        st.markdown("### 📡 Watch Tower Alerts")
        st.info("✅ No active alerts for this specific Legal Card.")

if __name__ == "__main__":
    main()
