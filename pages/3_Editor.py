import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

st.set_page_config(page_title="Legal Card Editor | RegWatch", page_icon="📝", layout="wide")

# ==========================================
# DATA LOADING
# ==========================================
@st.cache_data
def get_active_countries():
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
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'default_ontology.csv')
        return pd.read_csv(csv_path)
    except Exception:
        return pd.DataFrame(columns=["perimeter", "category_label", "sub_category_label"])

def generate_markdown_export(data_dict):
    md = f"# Legal Card: {data_dict['metadata'].get('category', 'Unknown')} - {data_dict['metadata'].get('market', 'Unknown')}\n\n"
    md += f"**Perimeter:** {data_dict['metadata'].get('perimeter', 'Unknown')} | **Sub-Category:** {data_dict['metadata'].get('sub_category', 'Unknown')}\n"
    md += f"**Last Updated:** {data_dict['metadata'].get('last_updated', 'Unknown')}\n\n---\n\n"
    
    md += "## 1. Identity & Scope\n"
    md += f"**Legal Definition:**\n{data_dict['identity']['definition']}\n\n"
    md += f"**HS Codes:** {data_dict['identity']['hs_codes']}\n\n"
    
    md += "## 2. Technical & Product Requirements\n"
    for req in data_dict['requirements']:
        if any(req.values()):
            md += f"* **[{req.get('Type', '')}]** {req.get('Parameter', '')}: {req.get('Limit', '')} *(Ref: {req.get('Reference', '')})*\n"
    
    md += "\n## 3. Marking & Information\n"
    for mark in data_dict['markings']:
        if any(mark.values()):
            mand = "🔴 Mandatory" if mark.get('Mandatory') else "⚪ Optional"
            md += f"* **{mark.get('Placement', '')}** - {mark.get('Requirement', '')} ({mand}): {mark.get('Description', '')}\n"
            
    md += "\n## 4. Conformity Documents\n"
    for doc in data_dict['documents']:
        if any(doc.values()):
            md += f"* **{doc.get('Document', '')}** (Retention: {doc.get('Retention', '')}): {doc.get('Description', '')}\n"
            
    return md

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
        all_perimeters = sorted(ontology_df['perimeter'].dropna().unique().tolist()) if 'perimeter' in ontology_df.columns else []
        selected_perimeter = st.selectbox("Perimeter", all_perimeters, index=None, placeholder="Select Perimeter...")
        
    with col2:
        # Cascade logic: Only show categories if perimeter is selected
        if selected_perimeter and 'perimeter' in ontology_df.columns:
            filtered_cats = ontology_df[ontology_df['perimeter'] == selected_perimeter]
        else:
            filtered_cats = pd.DataFrame()
            
        all_categories = sorted(filtered_cats['category_label'].dropna().unique().tolist()) if 'category_label' in filtered_cats.columns else []
        selected_category = st.selectbox("Category", all_categories, index=None, placeholder="Select Category...")
        
    with col3:
        # Cascade logic: Only show sub-categories if category is selected
        if selected_category and 'category_label' in filtered_cats.columns:
            filtered_subcats = filtered_cats[filtered_cats['category_label'] == selected_category]
        else:
            filtered_subcats = pd.DataFrame()
            
        all_subcategories = sorted(filtered_subcats['sub_category_label'].dropna().unique().tolist()) if 'sub_category_label' in filtered_subcats.columns else []
        selected_subcategory = st.selectbox("Sub-Category", all_subcategories, index=None, placeholder="Select Sub-Category...")

    with col4:
        available_countries = get_active_countries()
        selected_market = st.selectbox("Target Market", available_countries, index=None, placeholder="Select Market...")

    # Check if matrix is complete
    matrix_is_complete = all([selected_perimeter, selected_category, selected_subcategory, selected_market])

    st.divider()

    # ==========================================
    # MAIN LAYOUT: 75% Editor / 25% Actions
    # ==========================================
    main_col, side_col = st.columns([3, 1], gap="large")

    with main_col:
        # --- SECTION 1: IDENTITY ---
        st.subheader("1. Identity & Scope")
        product_def = st.text_area("Product Legal Definition", "Enter the official legal definition for this product category...", height=80)
        hs_codes = st.text_input("Covered HS Codes (Customs)", "Ex: 8527.13.00, 8519.81.00")
        
        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECTION 2: PRODUCT REQUIREMENTS ---
        st.subheader("2. Technical & Product Requirements")
        req_df_init = pd.DataFrame([{"Type": "Chemical", "Parameter": "", "Limit": "", "Reference": ""}])
        req_df_out = st.data_editor(
            req_df_init,
            column_config={
                "Type": st.column_config.SelectboxColumn("Requirement Type", options=["Chemical", "Mechanical", "Electrical", "Radio", "Environmental", "Safety", "Other"], required=True),
                "Parameter": st.column_config.TextColumn("Parameter / Substance", required=True),
                "Limit": st.column_config.TextColumn("Limit / Target", required=True),
                "Reference": st.column_config.TextColumn("Regulatory Reference")
            },
            num_rows="dynamic", use_container_width=True, key="req_editor"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECTION 3: MARKING & INFORMATION ---
        st.subheader("3. Marking & Information")
        marking_df_init = pd.DataFrame([{"Placement": "On Product", "Requirement": "", "Description": "", "Mandatory": True}])
        marking_df_out = st.data_editor(
            marking_df_init,
            column_config={
                "Placement": st.column_config.SelectboxColumn("Placement", options=["On Product", "On Packaging", "In Manual", "E-commerce (Web)", "Accompanying Document"], required=True),
                "Requirement": st.column_config.TextColumn("Requirement", required=True),
                "Description": st.column_config.TextColumn("Details / Content"),
                "Mandatory": st.column_config.CheckboxColumn("Mandatory", default=True)
            },
            num_rows="dynamic", use_container_width=True, key="marking_editor"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECTION 4: MARKET ACCESS & DOCS ---
        st.subheader("4. Conformity Documents & Access")
        docs_df_init = pd.DataFrame([{"Document": "", "Description": "", "Retention": ""}])
        docs_df_out = st.data_editor(docs_df_init, num_rows="dynamic", use_container_width=True, key="docs_editor")
        
        st.divider()

        with st.expander("🕒 History", expanded=False):
            st.markdown(f"* **{datetime.now().strftime('%Y-%m-%d')}** - Julien Dlubala - *Draft session.*")

    # ==========================================
    # BUILD DATA OBJECT (JSON)
    # ==========================================
    legal_card_data = {
        "metadata": {
            "perimeter": selected_perimeter or "Unassigned",
            "category": selected_category or "Unassigned",
            "sub_category": selected_subcategory or "Unassigned",
            "market": selected_market or "Unassigned",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "owner": "Julien Dlubala"
        },
        "identity": {
            "definition": product_def,
            "hs_codes": hs_codes
        },
        "requirements": req_df_out.to_dict('records'),
        "markings": marking_df_out.to_dict('records'),
        "documents": docs_df_out.to_dict('records')
    }
    
    json_string = json.dumps(legal_card_data, indent=4, ensure_ascii=False)
    md_string = generate_markdown_export(legal_card_data)

    # ==========================================
    # SIDE PANEL: Actions
    # ==========================================
    with side_col:
        st.markdown("### 💾 Storage")
        
        if st.button("Save to Internal Database", type="primary", use_container_width=True, disabled=not matrix_is_complete):
            try:
                save_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'legal_cards')
                os.makedirs(save_dir, exist_ok=True)
                
                safe_cat = str(selected_category).replace(" ", "_").replace("/", "-")
                safe_market = str(selected_market).replace(" ", "_").replace("/", "-")
                filename = f"{safe_cat}_{safe_market}.json"
                file_path = os.path.join(save_dir, filename)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(json_string)
                
                st.success(f"File saved: `{filename}`")
            except Exception as e:
                st.error(f"Save failed: {str(e)}")
                
        if not matrix_is_complete:
            st.caption("⚠️ Please select Perimeter, Category, Sub-Category, and Market to enable saving.")
        
        st.divider()
        
        st.markdown("### 📥 Export")
        st.download_button(
            label="Download JSON Data",
            data=json_string,
            file_name=f"LegalCard_{str(selected_category).replace(' ','_')}_{str(selected_market).replace(' ','_')}.json",
            mime="application/json",
            use_container_width=True,
            disabled=not matrix_is_complete
        )
        
        st.download_button(
            label="Download Text (Markdown)",
            data=md_string,
            file_name=f"LegalCard_{str(selected_category).replace(' ','_')}_{str(selected_market).replace(' ','_')}.md",
            mime="text/markdown",
            use_container_width=True,
            disabled=not matrix_is_complete
        )
        
        st.divider()
        st.markdown("### 📡 Watch Tower Alerts")
        st.info("✅ No active alerts for this specific Legal Card.")

if __name__ == "__main__":
    main()
