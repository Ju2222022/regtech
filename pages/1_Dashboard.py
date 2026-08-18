import streamlit as st
import pandas as pd
import os
import json

st.set_page_config(page_title="Dashboard | RegWatch", page_icon="📊", layout="wide")

# ==========================================
# DATA LOADING
# ==========================================
SIGNALS_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'signals_state.json')
CARDS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'legal_cards')

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
    signals_dict = load_signals_data()
    cards_list = load_cards_data()

    # Convert to DataFrames for easy filtering
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

    # --- 2. DYNAMIC FILTERS ---
    st.markdown("### 🎛️ Dynamic Filters")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Combine markets from both signals and cards for a unified filter
        all_markets = set()
        if not df_signals.empty and 'market' in df_signals.columns:
            all_markets.update(df_signals['market'].dropna().unique())
        if not df_cards.empty and 'market' in df_cards.columns:
            all_markets.update(df_cards['market'].dropna().unique())
        selected_market = st.multiselect("🌍 Market", sorted(list(all_markets)))

    with col2:
        all_priorities = []
        if not df_signals.empty and 'priority' in df_signals.columns:
            all_priorities = sorted(df_signals['priority'].dropna().unique().tolist())
        selected_priority = st.multiselect("🚨 Signal Priority", all_priorities)

    with col3:
        all_perimeters = []
        if not df_cards.empty and 'perimeter' in df_cards.columns:
            all_perimeters = sorted(df_cards['perimeter'].dropna().unique().tolist())
        selected_perimeter = st.multiselect("🏢 Perimeter (Cards)", all_perimeters)
        
    with col4:
        all_categories = []
        if not df_cards.empty and 'category' in df_cards.columns:
            if selected_perimeter:
                # Dynamic cascading filter: only show categories for the selected perimeter
                all_categories = sorted(df_cards[df_cards['perimeter'].isin(selected_perimeter)]['category'].dropna().unique().tolist())
            else:
                all_categories = sorted(df_cards['category'].dropna().unique().tolist())
        selected_category = st.multiselect("📁 Category (Cards)", all_categories)

    st.divider()

    # --- 3. APPLY FILTERS TO DATAFRAMES ---
    if not df_signals.empty:
        if selected_market:
            df_signals = df_signals[df_signals['market'].apply(lambda x: any(m in str(x) for m in selected_market))]
        if selected_priority:
            df_signals = df_signals[df_signals['priority'].isin(selected_priority)]

    if not df_cards.empty:
        if selected_market:
            df_cards = df_cards[df_cards['market'].isin(selected_market)]
        if selected_perimeter:
            df_cards = df_cards[df_cards['perimeter'].isin(selected_perimeter)]
        if selected_category:
            df_cards = df_cards[df_cards['category'].isin(selected_category)]

    # --- 4. CALCULATE KPIS (Based on filtered data) ---
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
