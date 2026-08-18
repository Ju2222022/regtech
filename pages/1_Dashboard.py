import streamlit as st
import pandas as pd
import os
import json

st.set_page_config(page_title="Dashboard | RegWatch", page_icon="📊", layout="wide")

# ==========================================
# DATA LOADING & PATHS
# ==========================================
SIGNALS_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'signals_state.json')
CARDS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'legal_cards')
ONTOLOGY_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'default_ontology.csv')
POOL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'regulatory_pool.csv')

@st.cache_data
def load_csv_data(filepath):
    if os.path.exists(filepath):
        return pd.read_csv(filepath)
    return pd.DataFrame()

def load_signals_data():
    if os.path.exists(SIGNALS_DB_PATH):
        try:
            with open(SIGNALS_DB_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def load_cards_data():
    cards = []
    if os.path.exists(CARDS_DIR):
        for filename in os.listdir(CARDS_DIR):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(CARDS_DIR, filename), 'r', encoding='utf-8') as f:
                        cards.append(json.load(f))
                except Exception:
                    pass
    return cards

# ==========================================
# MAIN APP
# ==========================================
def main():
    st.title("📊 Global Dashboard")
    st.markdown("Overview of your regulatory intelligence and compliance metrics.")

    # --- 1. DATA PREPARATION ---
    # Load Master CSVs
    df_ontology = load_csv_data(ONTOLOGY_PATH)
    df_pool = load_csv_data(POOL_PATH)

    # Load dynamic JSONs
    signals_dict = load_signals_data()
    cards_list = load_cards_data()

    # Convert to DataFrames
    df_signals = pd.DataFrame(signals_dict.values()) if signals_dict else pd.DataFrame()
    
    cards_flat = []
    for c in cards_list:
        meta = c.get("metadata", {})
        cards_flat.append({
            "perimeter": meta.get("perimeter", "Unknown"),
            "category": meta.get("category", "Unknown"),
            "sub_category": meta.get("sub_category", "Unknown"),
            "market": meta.get("market", "Unknown")
        })
    df_cards = pd.DataFrame(cards_flat) if cards_flat else pd.DataFrame()

    # --- 2. DYNAMIC FILTERS (Linked to CSV Masters) ---
    st.markdown("### 🎛️ Dynamic Filters")
    
    # Ligne 1 : Marché et Criticité
    col_m, col_p, _ = st.columns([2, 2, 4])
    with col_m:
        # Les marchés viennent du pool de surveillance
        master_markets = sorted(df_pool['Geographic Zone'].dropna().unique().tolist()) if 'Geographic Zone' in df_pool.columns else []
        selected_market = st.multiselect("🌍 Market (from Regulatory Pool)", master_markets)

    with col_p:
        # La priorité vient des signaux détectés
        all_priorities = sorted(df_signals['priority'].dropna().unique().tolist()) if not df_signals.empty and 'priority' in df_signals.columns else ["high", "medium", "low"]
        selected_priority = st.multiselect("🚨 Signal Priority", all_priorities)

    # Ligne 2 : Ontologie en cascade (Périmètre > Catégorie > Sous-catégorie)
    col_per, col_cat, col_sub = st.columns(3)
    
    with col_per:
        master_perimeters = sorted(df_ontology['perimeter'].dropna().unique().tolist()) if not df_ontology.empty and 'perimeter' in df_ontology.columns else []
        selected_perimeter = st.multiselect("🏢 Perimeter", master_perimeters)
        
    with col_cat:
        if selected_perimeter:
            filtered_onto_cat = df_ontology[df_ontology['perimeter'].isin(selected_perimeter)]
        else:
            filtered_onto_cat = df_ontology
        
        master_categories = sorted(filtered_onto_cat['category_label'].dropna().unique().tolist()) if not filtered_onto_cat.empty and 'category_label' in filtered_onto_cat.columns else []
        selected_category = st.multiselect("📁 Category", master_categories)

    with col_sub:
        if selected_category:
            filtered_onto_sub = df_ontology[df_ontology['category_label'].isin(selected_category)]
        elif selected_perimeter:
            filtered_onto_sub = df_ontology[df_ontology['perimeter'].isin(selected_perimeter)]
        else:
            filtered_onto_sub = df_ontology
            
        master_subcategories = sorted(filtered_onto_sub['sub_category_label'].dropna().unique().tolist()) if not filtered_onto_sub.empty and 'sub_category_label' in filtered_onto_sub.columns else []
        selected_subcategory = st.multiselect("📄 Sub-Category", master_subcategories)

    st.divider()

    # --- 3. APPLY FILTERS TO DATAFRAMES ---
    # Filtrage des signaux
    if not df_signals.empty:
        if selected_market:
            df_signals = df_signals[df_signals['market'].apply(lambda x: any(m in str(x) for m in selected_market))]
        if selected_priority:
            df_signals = df_signals[df_signals['priority'].isin(selected_priority)]
        # Pour les signaux, la liaison avec l'ontologie est moins stricte (texte brut), on filtre si des catégories matchent
        if selected_category or selected_subcategory:
            search_terms = set((selected_category or []) + (selected_subcategory or []))
            df_signals = df_signals[df_signals['categories'].apply(lambda cats: any(term in str(cats) for term in search_terms)) | df_signals['categories'].apply(len) == 0]

    # Filtrage des fiches légales (strict)
    if not df_cards.empty:
        if selected_market:
            df_cards = df_cards[df_cards['market'].isin(selected_market)]
        if selected_perimeter:
            df_cards = df_cards[df_cards['perimeter'].isin(selected_perimeter)]
        if selected_category:
            df_cards = df_cards[df_cards['category'].isin(selected_category)]
        if selected_subcategory:
            df_cards = df_cards[df_cards['sub_category'].isin(selected_subcategory)]

    # --- 4. CALCULATE KPIS ---
    total_signals = len(df_signals)
    inbox_signals = len(df_signals[df_signals['status'] == 'inbox']) if not df_signals.empty and 'status' in df_signals.columns else 0
    bookmarked_signals = len(df_signals[df_signals['status'] == 'bookmark']) if not df_signals.empty and 'status' in df_signals.columns else 0
    total_cards = len(df_cards)

    st.header("🎯 Key Metrics")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Signals Tracked", total_signals)
    kpi2.metric("Pending Alerts (Inbox)", inbox_signals, delta="- To Review" if inbox_signals > 0 else "All Clear", delta_color="inverse")
    kpi3.metric("Bookmarked Signals", bookmarked_signals)
    kpi4.metric("Active Legal Cards", total_cards)

    st.divider()

    # --- 5. VISUALIZATIONS ---
    col_charts1, col_charts2 = st.columns(2, gap="large")

    with col_charts1:
        st.subheader("📈 Signals by Priority")
        if not df_signals.empty and 'priority' in df_signals.columns:
            priority_counts = df_signals['priority'].value_counts().reset_index()
            priority_counts.columns = ['Priority', 'Count']
            st.bar_chart(priority_counts.set_index('Priority'), color="#FF4B4B")
        else:
            st.info("📡 No signal data matches the current filters.")

    with col_charts2:
        st.subheader("🗂️ Legal Cards Coverage")
        if not df_cards.empty and 'category' in df_cards.columns:
            cat_counts = df_cards['category'].value_counts().reset_index()
            cat_counts.columns = ['Category', 'Count']
            st.bar_chart(cat_counts.set_index('Category'), color="#0068C9")
        else:
            st.info("📝 No legal cards match the current filters.")
    
    st.divider()

    # --- 6. RECENT ACTIVITY TABLE ---
    st.subheader("⏱️ Recent Regulatory Activity")
    if not df_signals.empty:
        if all(col in df_signals.columns for col in ['date', 'title', 'market', 'priority', 'status']):
            df_display = df_signals[['date', 'title', 'market', 'priority', 'status']].copy()
            df_display['date'] = pd.to_datetime(df_display['date'], errors='coerce')
            df_display = df_display.sort_values(by='date', ascending=False).head(10)
            df_display['date'] = df_display['date'].dt.strftime('%Y-%m-%d')
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No recent activity to display for these filters.")

if __name__ == "__main__":
    main()
