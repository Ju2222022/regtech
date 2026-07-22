import streamlit as st
import time
import os
import pandas as pd
from datetime import datetime

# ==========================================
# IMPORT DU MOTEUR IA
# ==========================================
try:
    from core.agents.watcher import run_live_watch
except ImportError:
    st.error("Impossible de trouver `watcher.py`. Assure-toi qu'il est bien dans `core/agents/`.")

st.set_page_config(page_title="Watch Tower | RegWatch", page_icon="📡", layout="wide")

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
        return ["EU", "France", "USA", "China", "UK", "Canada", "India"]
    except Exception:
        return ["EU", "France", "USA", "China", "UK", "Canada", "India"]

@st.cache_data
def get_ontology_data():
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'default_ontology.csv')
        return pd.read_csv(csv_path)
    except Exception:
        return pd.DataFrame(columns=["perimeter", "category_label", "sub_category_label"])

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "scan_executed" not in st.session_state:
    st.session_state.scan_executed = False

if "signals_db" not in st.session_state:
    st.session_state.signals_db = {}
    
if "last_kpi_cost" not in st.session_state:
    st.session_state.last_kpi_cost = 0.0

def update_signal_status(sig_id, new_status):
    st.session_state.signals_db[sig_id]["status"] = new_status

# ==========================================
# MAIN APP
# ==========================================
def main():
    st.title("📡 Watch Tower")
    st.markdown("Automated regulatory scanning and gap analysis.")

    # --- HIERARCHICAL FILTERS ---
    st.header("🎯 1. Radar", divider="blue")
    
    ontology_df = get_ontology_data()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if 'perimeter' in ontology_df.columns:
            all_perimeters = sorted(ontology_df['perimeter'].dropna().unique().tolist())
        else:
            all_perimeters = ["Electronics"]
        selected_perimeters = st.multiselect("Perimeter", all_perimeters)
        
    with col2:
        if selected_perimeters and 'perimeter' in ontology_df.columns:
            filtered_cats = ontology_df[ontology_df['perimeter'].isin(selected_perimeters)]
        else:
            filtered_cats = ontology_df
            
        if 'category_label' in filtered_cats.columns:
            all_categories = sorted(filtered_cats['category_label'].dropna().unique().tolist())
        else:
            all_categories = ["Mobility", "Wearables"]
        selected_categories = st.multiselect("Category", all_categories)
        
    with col3:
        if selected_categories and 'category_label' in filtered_cats.columns:
            filtered_subcats = filtered_cats[filtered_cats['category_label'].isin(selected_categories)]
        else:
            filtered_subcats = filtered_cats
            
        if 'sub_category_label' in filtered_subcats.columns:
            all_subcategories = sorted(filtered_subcats['sub_category_label'].dropna().unique().tolist())
        else:
            all_subcategories = ["E-Bikes (EPAC)", "Smartwatches"]
        selected_subcategories = st.multiselect("Sub-Category", all_subcategories)

    with col4:
        available_countries = get_active_countries()
        # MODIFICATION 1 : Filtre vide par défaut (default=[])
        countries = st.multiselect("Target Geographies", available_countries, default=[])

    # MODIFICATION 2 : Ajout du choix de la période temporelle pour éviter les résultats nuls
    selected_timeframe = st.selectbox("Timeframe (Search Depth)", ["⚡ Last 7 days", "⚡ Last 30 days", "📅 Last 12 months"], index=2)
        
    gemini_key = st.secrets.get("GEMINI_API_KEY", "")
    tavily_key = st.secrets.get("TAVILY_API_KEY", "")
    
    categories_to_scan = selected_subcategories if selected_subcategories else selected_categories
    ready_to_scan = bool(categories_to_scan and countries)
        
    if st.button("🚀 Run Scan", type="primary", use_container_width=True, disabled=not ready_to_scan):
        if not (gemini_key and tavily_key):
            st.error("⚠️ API keys (Gemini & Tavily) missing in your secrets setup.")
        else:
            with st.spinner(f"Agent 1 is scanning global sources for the {selected_timeframe}..."):
                try:
                    # MODIFICATION 3 : On injecte la période choisie dans l'UI vers le moteur
                    live_entries, usage = run_live_watch(
                        gemini_key=gemini_key,
                        tavily_key=tavily_key,
                        categories=categories_to_scan,
                        markets=countries,
                        timeframe_label=selected_timeframe
                    )
                    
                    new_db = {}
                    for idx, entry in enumerate(live_entries):
                        sig_id = f"sig_{datetime.now().strftime('%H%M%S')}_{idx}"
                        new_db[sig_id] = {
                            "title": entry.get("title", "Untitled Signal"),
                            "market": ", ".join(entry.get("markets", countries)),
                            "source": entry.get("source", "Web Search"),
                            "date": entry.get("date", datetime.now().strftime("%Y-%m-%d")),
                            "summary": entry.get("summary", "No summary provided."),
                            "impact": entry.get("impact_prediction", "Impact assessment required."),
                            "status": "inbox",
                            "priority": entry.get("urgency", "low").lower()
                        }
                    
                    if new_db:
                        st.session_state.signals_db.update(new_db)
                        st.success(f"Scan complete! Found {len(new_db)} new signals.")
                        
                        est_cost = (usage['input_tokens'] / 1_000_000 * 0.075) + (usage['output_tokens'] / 1_000_000 * 0.30)
                        st.session_state.last_kpi_cost = round(est_cost, 4)
                    else:
                        st.info(f"Scan completed. No new regulatory alerts found for this scope over the {selected_timeframe}.")
                        
                    st.session_state.scan_executed = True
                    
                except Exception as e:
                    st.error(f"Scan failed: {str(e)}")

    # ==========================================
    # ZONE 2 : WATCH FEED (RESULTS)
    # ==========================================
    if st.session_state.scan_executed or st.session_state.signals_db:
        st.header("📋 2. Watch Feed", divider="blue")
        
        kpi1, kpi2, kpi3 = st.columns(3)
        inbox_count = sum(1 for s in st.session_state.signals_db.values() if s["status"] == "inbox")
        
        kpi1.metric("Total Signals Tracked", len(st.session_state.signals_db))
        kpi2.metric("Unread Alerts", inbox_count)
        kpi3.metric("Est. AI Cost (Last Scan)", f"${st.session_state.last_kpi_cost}")

        tab_inbox, tab_bookmark, tab_archive = st.tabs(["📥 Inbox (Unread)", "📌 Bookmarked", "🗄️ Archive"])

        def render_signal_card(sig_id, data):
            with st.container(border=True):
                st.markdown(f"#### 📄 {data['title']}")
                st.caption(f"🌍 **Market:** {data['market']} | 🏛️ **Source:** {data['source']} | 📅 **Published:** {data['date']}")
                st.info(f"**AI Summary:** {data['summary']}")
                
                if data['priority'] == 'high':
                    st.warning(f"🔍 {data['impact']}")
                elif data['priority'] == 'medium':
                    st.warning(f"⚠️ {data['impact']}")
                else:
                    st.success(f"✅ {data['impact']}")
                
                col_a, col_b, col_c, col_d = st.columns([2, 2, 1, 1])
                with col_a:
                    st.button("📝 Assess Impact", key=f"assess_{sig_id}", type="primary", use_container_width=True)
                with col_b:
                    st.button("💬 Chat with Assistant", key=f"chat_{sig_id}", use_container_width=True)
                
                with col_c:
                    if data['status'] != "bookmark":
                        st.button("📌 Bookmark", key=f"bookmark_{sig_id}", use_container_width=True, on_click=update_signal_status, args=(sig_id, "bookmark"))
                    else:
                        st.button("📥 To Inbox", key=f"inbox_{sig_id}", use_container_width=True, on_click=update_signal_status, args=(sig_id, "inbox"))
                with col_d:
                    if data['status'] != "archive":
                        st.button("🚫 Dismiss", key=f"dismiss_{sig_id}", use_container_width=True, on_click=update_signal_status, args=(sig_id, "archive"))
                    else:
                        st.button("📥 To Inbox", key=f"inbox_restore_{sig_id}", use_container_width=True, on_click=update_signal_status, args=(sig_id, "inbox"))

        with tab_inbox:
            inbox_signals = {k: v for k, v in st.session_state.signals_db.items() if v["status"] == "inbox"}
            if not inbox_signals:
                st.success("🎉 Inbox Zero! No new regulatory signals to process.")
            for sig_id, data in inbox_signals.items():
                render_signal_card(sig_id, data)

        with tab_bookmark:
            bookmark_signals = {k: v for k, v in st.session_state.signals_db.items() if v["status"] == "bookmark"}
            if not bookmark_signals:
                st.markdown("*Your bookmarked signals will appear here.*")
            for sig_id, data in bookmark_signals.items():
                render_signal_card(sig_id, data)
            
        with tab_archive:
            archive_signals = {k: v for k, v in st.session_state.signals_db.items() if v["status"] == "archive"}
            if not archive_signals:
                st.markdown("*Processed and dismissed signals are archived here.*")
            for sig_id, data in archive_signals.items():
                render_signal_card(sig_id, data)

if __name__ == "__main__":
    main()
