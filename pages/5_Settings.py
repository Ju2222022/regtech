import streamlit as st
import sys
import os
import copy
import uuid
import pandas as pd

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

    # Ajout du 4ème onglet pour l'Import/Export
    tab1, tab2, tab3, tab4 = st.tabs(["🗂️ Ontology Builder", "🏢 Tenant Profile", "🌐 Global Rules", "📥 Import / Export"])

    # ---------------------------------------------------------
    # ONGLET 1 : ONTOLOGIE (Vue Arborescente et Édition)
    # ---------------------------------------------------------
    with tab1:
        st.subheader("Ontology Tree View")
        st.markdown("Your regulatory perimeters and sub-categories are grouped by Category Label.")
        
        if "editing_category" not in st.session_state:
            st.session_state["editing_category"] = None

        categories = ref_manager.get_categories()
        
        # === BLOC ÉDITION ===
        if st.session_state["editing_category"]:
            cat_to_edit = ref_manager.get_category_by_id(st.session_state["editing_category"])
            
            if cat_to_edit:
                st.warning(f"✏️ **Editing Mode:** {cat_to_edit.get('category_label')} ({cat_to_edit.get('category_id')})")
                
                with st.form("edit_category_form"):
                    col_macro, col_category = st.columns(2)
                    with col_macro:
                        edit_perimeter = st.text_input("Macro Perimeter", value=cat_to_edit.get('perimeter', ''))
                    with col_category:
                        edit_category_val = st.text_input("Category Label", value=cat_to_edit.get('internal_owner_group', ''))
                        
                    col_label, col_id = st.columns(2)
                    with col_label:
                        edit_label = st.text_input("Sub-Category Label", value=cat_to_edit.get('category_label', ''))
                    with col_id:
                        st.text_input("Unique ID (Cannot be changed)", value=cat_to_edit.get('category_id', ''), disabled=True)
                    
                    edit_def = st.text_area("Business Definition", value=cat_to_edit.get('business_definition', ''))
                    
                    st.markdown("**Matching Configuration (Comma separated)**")
                    config = cat_to_edit.get("matching_engine_config", {})
                    str_strict = ", ".join(config.get("strict_technical_attributes", []))
                    str_fuzzy = ", ".join(config.get("fuzzy_keywords_fallbacks", []))
                    
                    edit_strict = st.text_area("Strict Attributes (Optional)", value=str_strict)
                    edit_fuzzy = st.text_area("Keywords (Optional)", value=str_fuzzy)
                    
                    col_submit, col_cancel = st.columns([1, 5])
                    with col_submit:
                        submitted = st.form_submit_button("💾 Save Changes", type="primary")
                    with col_cancel:
                        canceled = st.form_submit_button("❌ Cancel")
                        
                    if canceled:
                        st.session_state["editing_category"] = None
                        st.rerun()
                        
                    if submitted:
                        cat_to_edit["perimeter"] = edit_perimeter
                        cat_to_edit["internal_owner_group"] = edit_category_val 
                        cat_to_edit["category_label"] = edit_label
                        cat_to_edit["business_definition"] = edit_def
                        
                        cat_to_edit["matching_engine_config"]["strict_technical_attributes"] = [x.strip() for x in edit_strict.split(",") if x.strip()]
                        cat_to_edit["matching_engine_config"]["fuzzy_keywords_fallbacks"] = [x.strip() for x in edit_fuzzy.split(",") if x.strip()]
                        
                        if ref_manager.update_category(cat_to_edit):
                            st.session_state["editing_category"] = None
                            st.rerun()
                st.divider()

        # === BLOC AFFICHAGE NORMAL ===
        elif not categories:
            st.info("No categories defined. Start building your ontology below.")
        else:
            tree = {}
            for cat in categories:
                perimeter = cat.get('perimeter', 'Uncategorized Perimeter')
                category_group = cat.get('internal_owner_group', 'Unassigned Category')
                
                if perimeter not in tree:
                    tree[perimeter] = {}
                if category_group not in tree[perimeter]:
                    tree[perimeter][category_group] = []
                    
                tree[perimeter][category_group].append(cat)
            
            for perimeter_name, categories_group in tree.items():
                st.markdown(f"## 🌍 {perimeter_name}")
                
                for category_name, sub_categories in categories_group.items():
                    st.markdown(f"#### 📁 {category_name}")
                    
                    for cat in sub_categories:
                        label = cat.get('category_label', 'Unnamed')
                        cat_id = cat.get('category_id', 'NO_ID')
                        
                        with st.expander(f"📄 {label}  |  ID: {cat_id}"):
                            st.write(f"**Definition:** {cat.get('business_definition', '')}")
                            st.write(f"**Scope:** {cat.get('operational_scope', '')}")
                            
                            st.divider()
                            col_edit, col_dup, col_del, _ = st.columns([1, 1, 1, 4])
                            with col_edit:
                                if st.button("✏️ Modify", key=f"edit_{cat_id}"):
                                    st.session_state["editing_category"] = cat_id
                                    st.rerun()
                            with col_dup:
                                if st.button("📑 Duplicate", key=f"dup_{cat_id}"):
                                    new_cat = copy.deepcopy(cat)
                                    new_cat["category_id"] = f"{cat_id}_COPY"
                                    new_cat["category_label"] = f"{label} (Copy)"
                                    if ref_manager.add_category(new_cat):
                                        st.rerun()
                                    else:
                                        st.error("A copy already exists. Please modify its ID first before duplicating again.")
                            with col_del:
                                if st.button("🗑️ Delete", key=f"del_{cat_id}", type="primary"):
                                    if ref_manager.delete_category(cat_id):
                                        st.rerun()
                    
                st.divider()
        
        # Formulaire d'ajout 
        if not st.session_state["editing_category"]:
            st.subheader("➕ Add New Sub-Category")
            with st.expander("Open Category Creator Form"):
                with st.form("add_category_form"):
                    col_macro, col_category, col_label = st.columns(3)
                    with col_macro:
                        new_perimeter = st.text_input("Perimeter", placeholder="e.g., Electronics")
                    with col_category:
                        new_category_val = st.text_input("Category Label", placeholder="e.g., Energy Storage")
                    with col_label:
                        new_label = st.text_input("Sub-Category Label", placeholder="e.g., Coin Cells & Button Batteries")
                    
                    submitted = st.form_submit_button("Create Skeleton", type="primary")
                    
                    if submitted:
                        if not new_label:
                            st.error("Error: A Sub-Category Label is required.")
                        else:
                            generated_id = f"CAT_{uuid.uuid4().hex[:8].upper()}"
                            
                            new_cat = {
                                "perimeter": new_perimeter if new_perimeter else "Uncategorized Perimeter",
                                "internal_owner_group": new_category_val if new_category_val else "Unassigned Category",
                                "category_id": generated_id,
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
                                st.error("Error: Could not create the category.")
                                
    # ---------------------------------------------------------
    # ONGLET 2 : PROFIL
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
    # ONGLET 3 : RÈGLES GLOBALES 
    # ---------------------------------------------------------
    with tab3:
        st.subheader("Global Routing Rules")
        rules = data.get("global_routing_rules", {})
        
        st.checkbox("Enable Mandatory Fallback Category", value=rules.get("has_mandatory_fallback", False))
        st.text_input("Fallback Category ID", value=rules.get("mandatory_fallback_category_id", ""))
        st.checkbox("Allow Multi-labeling (Overlaps)", value=rules.get("allow_multi_labeling", True))
        st.button("💾 Save Engine Rules")

    # ---------------------------------------------------------
    # ONGLET 4 : IMPORT / EXPORT CSV (Bulk)
    # ---------------------------------------------------------
    with tab4:
        st.subheader("📥 Ontology Import / Export")
        st.markdown("Use this module to bulk update the ontology or extract it for external sharing.")

        col_export, col_import = st.columns(2)

        # ====== BLOC 1 : EXPORT ET TEMPLATE ======
        with col_export:
            st.markdown("### 1. Export Current Database")
            
            # Aplatissement du JSON vers format plat (CSV)
            export_data = []
            for cat in ref_manager.get_categories():
                row = {
                    "category_id": cat.get("category_id", ""),
                    "perimeter": cat.get("perimeter", ""),
                    "category_label": cat.get("internal_owner_group", ""),
                    "sub_category_label": cat.get("category_label", ""),
                    "business_definition": cat.get("business_definition", ""),
                    # Utilisation d'un délimiteur ' | ' pour transformer les listes en chaîne de caractères
                    "strict_attributes": " | ".join(cat.get("matching_engine_config", {}).get("strict_technical_attributes", [])),
                    "keywords": " | ".join(cat.get("matching_engine_config", {}).get("fuzzy_keywords_fallbacks", [])),
                    "legal_framework": " | ".join(cat.get("reference_legal_framework", [])),
                    "deliverables": " | ".join(cat.get("expected_deliverables", []))
                }
                export_data.append(row)
            
            df_export = pd.DataFrame(export_data)
            csv_export = df_export.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download Full Ontology (CSV)", data=csv_export, file_name="ontology_export.csv", mime="text/csv")
            
            st.divider()
            
            st.markdown("### 2. Blank Template")
            st.markdown("Start from scratch with a clean, perfectly formatted template.")
            df_template = pd.DataFrame(columns=["category_id", "perimeter", "category_label", "sub_category_label", "business_definition", "strict_attributes", "keywords", "legal_framework", "deliverables"])
            csv_template = df_template.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV Template", data=csv_template, file_name="ontology_template.csv", mime="text/csv")

        # ====== BLOC 2 : UPSERT (IMPORT INTELLIGENT) ======
        with col_import:
            st.markdown("### 3. Smart Bulk Import (Upsert)")
            st.info("💡 **Rule:** If `category_id` exists in your file, it updates the existing entry. If the ID is empty, it creates a new entry. Use `|` to separate multiple items in list columns (e.g., `Bluetooth | WiFi`).")
            
            uploaded_file = st.file_uploader("Upload configured CSV", type=["csv"])
            
            if uploaded_file and st.button("🚀 Process Bulk Import", type="primary"):
                try:
                    df_import = pd.read_csv(uploaded_file)
                    df_import = df_import.fillna("") # Remplace les valeurs vides par des chaînes de caractères
                    
                    updates_count = 0
                    creates_count = 0
                    
                    for index, row in df_import.iterrows():
                        cat_id = str(row.get("category_id", "")).strip()
                        
                        # Création de l'ID si la cellule est vide
                        if not cat_id:
                            cat_id = f"CAT_{uuid.uuid4().hex[:8].upper()}"
                            is_new = True
                        else:
                            is_new = ref_manager.get_category_by_id(cat_id) is None

                        # Fonction utilitaire pour repasser de "A | B" à la liste ["A", "B"]
                        def parse_list(col_name):
                            val = str(row.get(col_name, ""))
                            return [x.strip() for x in val.split("|") if x.strip()]

                        # Assemblage de l'objet métier
                        cat_data = {
                            "category_id": cat_id,
                            "perimeter": str(row.get("perimeter", "Uncategorized")),
                            "internal_owner_group": str(row.get("category_label", "Unassigned")),
                            "category_label": str(row.get("sub_category_label", "Unnamed Sub-Category")),
                            "business_definition": str(row.get("business_definition", "")),
                            "matching_engine_config": {
                                "strict_technical_attributes": parse_list("strict_attributes"),
                                "fuzzy_keywords_fallbacks": parse_list("keywords")
                            },
                            "reference_legal_framework": parse_list("legal_framework"),
                            "expected_deliverables": parse_list("deliverables")
                        }
                        
                        # Logique d'Upsert
                        if is_new:
                            ref_manager.add_category(cat_data)
                            creates_count += 1
                        else:
                            # On récupère l'ancienne pour ne pas écraser des données qui n'apparaissent pas dans le CSV (comme operational_scope)
                            old_cat = ref_manager.get_category_by_id(cat_id)
                            old_cat.update(cat_data) 
                            ref_manager.update_category(old_cat)
                            updates_count += 1
                            
                    st.success(f"✅ Import successful! Created: {creates_count} | Updated: {updates_count}")
                    
                except Exception as e:
                    st.error(f"❌ Error processing file: Make sure the column names match the template exactly. Details: {str(e)}")

if __name__ == "__main__":
    main()
