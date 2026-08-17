import streamlit as st
import time
import os
import pandas as pd
import json
from datetime import datetime

# ==========================================
# SYSTÈME DE PERSISTANCE JSON
# ==========================================
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'signals_state.json')

def load_signals():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_signals(data):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# IMPORT DU MOTEUR IA
# ==========================================
try:
    from core.agents.watcher import run_live_watch
    from core.agents.impact import find_matching_legal_cards, analyze_gap_with_gemini
    from core.agents.updater import generate_card_update
except ImportError:
    st.error("Impossible de trouver les agents dans `core/agents/`.")

# ==========================================
# DATA LOADING (Single Source of Truth)
# ==========================================
@st.cache_data
def get_active_countries():
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'regulatory_pool.csv')
        df = pd.read_csv(csv_path)
        if 'Geographic Zone' in df.columns:
            return sorted(df['Geographic Zone'].dropna().unique().tolist())
        return [] 
    except Exception:
        return [] 

@st.cache_data
def get_ontology_data():
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'default_ontology.csv')
        return pd.read_csv(csv_path)
    except Exception:
        return pd.DataFrame(columns=["category_id", "perimeter", "category_label", "sub_category_label"])

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "scan_executed" not in st.session_state:
    st.session_state.scan_executed = False

if "signals_db" not in st.session_state:
    st.session_state.signals_db = load_signals()
    
if "last_kpi_cost" not in st.session_state:
    st.session_state.last_kpi_cost = 0.0

def update_signal_status(sig_id, new_status):
    st.session_state.signals_db[sig_id]["status"] = new_status
    save_signals(st.session_state.signals_db)

# ==========================================
# MAIN APP
# ==========================================
def main():
    st.title("📡 Watch Tower")
    st.markdown("Automated regulatory scanning and gap analysis.")

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
        countries = st.multiselect("Target Geographies", available_countries, default=[])

    selected_timeframe = st.selectbox("Timeframe (Search Depth)", ["⚡ Last 7 days", "⚡ Last 30 days", "📅 Last 12 months"], index=2)
        
    gemini_key = st.secrets.get("GEMINI_API_KEY", "")
    tavily_key = st.secrets.get("TAVILY_API_KEY", "")
    
    categories_to_scan = selected_subcategories if selected_subcategories else selected_categories
    ready_to_scan = bool(categories_to_scan and countries)
        
    if st.button("🚀 Run Scan", type="primary", use_container_width=True, disabled=not ready_to_scan):
        if not (gemini_key and tavily_key):
            st.error("⚠️ API keys (Gemini & Tavily) missing in your secrets setup.")
        else:
            with st.status(f"🚀 Initializing scan for {selected_timeframe}...", expanded=True) as status_box:
                try:
                    def update_status(message):
                        status_box.update(label=message, state="running")

                    live_entries, usage = run_live_watch(
                        gemini_key=gemini_key,
                        tavily_key=tavily_key,
                        categories=categories_to_scan,
                        markets=countries,
                        timeframe_label=selected_timeframe,
                        status_callback=update_status
                    )
                    
                    new_db = {}
                    for idx, entry in enumerate(live_entries):
                        sig_id = f"sig_{datetime.now().strftime('%H%M%S')}_{idx}"
                        new_db[sig_id] = {
                            "title": entry.get("title", "Untitled Signal"),
                            "url": entry.get("url", ""),
                            "market": ", ".join(entry.get("markets", countries)),
                            "categories": categories_to_scan,
                            "source": entry.get("source", "Web Search"),
                            "date": entry.get("date", datetime.now().strftime("%Y-%m-%d")),
                            "summary": entry.get("summary", "No summary provided."),
                            "impact": entry.get("impact_prediction", "Impact assessment required."),
                            "status": "inbox",
                            "priority": entry.get("urgency", "low").lower()
                        }
                    
                    if new_db:
                        st.session_state.signals_db.update(new_db)
                        save_signals(st.session_state.signals_db)
                        
                        est_cost = (usage['input_tokens'] / 1_000_000 * 0.075) + (usage['output_tokens'] / 1_000_000 * 0.30)
                        st.session_state.last_kpi_cost = round(est_cost, 4)
                        status_box.update(label=f"✅ Scan complete! Found {len(new_db)} new signals.", state="complete", expanded=False)
                    else:
                        status_box.update(label=f"ℹ️ Scan complete. No new regulatory alerts found for this scope.", state="complete", expanded=False)
                        
                    st.session_state.scan_executed = True
                    
                except Exception as e:
                    status_box.update(label="❌ Scan failed", state="error", expanded=True)
                    st.error(f"Scan failed: {str(e)}")

    # ==========================================
    # ZONE 2 : WATCH FEED (RESULTS)
    # ==========================================
    if True: # Always display the Watch Feed zone
        st.header("📋 2. Watch Feed", divider="blue")
        
        kpi1, kpi2, kpi3 = st.columns(3)
        inbox_count = sum(1 for s in st.session_state.signals_db.values() if s["status"] == "inbox")
        
        kpi1.metric("Total Signals Tracked", len(st.session_state.signals_db))
        kpi2.metric("Unread Alerts", inbox_count)
        kpi3.metric("Est. AI Cost (Last Scan)", f"${st.session_state.last_kpi_cost}")

        tab_inbox, tab_bookmark, tab_archive = st.tabs(["📥 Inbox (Unread)", "📌 Bookmarked", "🗄️ Archive"])

        def render_signal_card(sig_id, data):
            with st.container(border=True):
                if data.get("url"):
                    st.markdown(f"#### 📄 [{data['title']}]({data['url']})")
                else:
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
                    assess_clicked = st.button("📝 Assess Impact", key=f"assess_{sig_id}", type="primary", use_container_width=True)
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

                # LOGIQUE D'ANALYSE MULTI-FICHES
                if assess_clicked:
                    with st.spinner("Analyzing impact against internal Legal Cards..."):
                        matched_cards = find_matching_legal_cards(data)
                        
                        if not matched_cards:
                            st.warning("⚠️ No matching Legal Card found for this market/category. Please create one in the Editor to enable Gap Analysis.")
                        else:
                            analyses_list = []
                            for card_info in matched_cards:
                                result = analyze_gap_with_gemini(gemini_key, data, card_info['data'])
                                analyses_list.append({
                                    "card": card_info['data'],
                                    "analysis": result
                                })
                            
                            st.session_state.signals_db[sig_id]["gap_analyses"] = analyses_list
                            save_signals(st.session_state.signals_db)

                # AFFICHAGE DE L'ANALYSE (Sélecteur si multiples)
                if "gap_analyses" in data and data["gap_analyses"]:
                    st.divider()
                    analyses_list = data["gap_analyses"]
                    selected_idx = 0
                    
                    if len(analyses_list) > 1:
                        st.markdown("### 🗂️ Multiple Legal Cards Impacted")
                        options = []
                        for idx, item in enumerate(analyses_list):
                            meta = item['card'].get('metadata', {})
                            opt_label = f"{meta.get('category', 'Unknown')} > {meta.get('sub_category', 'Unknown')} | 🌍 {meta.get('market', '')}"
                            options.append(opt_label)
                        
                        selected_option = st.selectbox("Select which Legal Card to review and update:", options, key=f"sel_card_{sig_id}")
                        selected_idx = options.index(selected_option)
                    
                    selected_gap = analyses_list[selected_idx]
                    result = selected_gap["analysis"]
                    card_data = selected_gap["card"]
                    
                    meta = card_data.get('metadata', {})
                    cat_display = meta.get('category', 'Unknown Category')
                    subcat_display = meta.get('sub_category', '')
                    market_display = meta.get('market', 'Unknown Market')
                    
                    if subcat_display and subcat_display != "Unassigned":
                        ui_title = f"{cat_display} > {subcat_display} | 🌍 {market_display}"
                    else:
                        ui_title = f"{cat_display} | 🌍 {market_display}"
                        
                    st.markdown(f"#### 🔍 Gap Analysis : **{ui_title}**")
                    
                    if "Delta" in result.get('status', ''):
                        st.error(f"**Status:** {result.get('status')}")
                    elif "Compliant" in result.get('status', ''):
                        st.success(f"**Status:** {result.get('status')}")
                    else:
                        st.warning(f"**Status:** {result.get('status')}")
                    
                    st.markdown(f"**Analysis:** {result.get('analysis')}")
                    
                    if result.get('gaps'):
                        st.markdown("**Identified Gaps:**")
                        for gap in result.get('gaps'):
                            st.markdown(f"- **[{gap.get('type')}]** {gap.get('description')}")
                            
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("✨ Auto-Draft Update in Editor", key=f"draft_{sig_id}_{selected_idx}", type="primary"):
                            with st.spinner("AI is drafting the updated Legal Card..."):
                                try:
                                    updated_card = generate_card_update(gemini_key, card_data, result)
                                    # NOUVEAU: On envoie le JSON modifié ET l'analyse pour le contexte
                                    st.session_state.draft_update = {
                                        "card": updated_card,
                                        "analysis": result
                                    }
                                    st.switch_page("pages/3_Editor.py")
                                except Exception as e:
                                    st.error(f"❌ Gemini API Error during drafting: {str(e)}. Please try again in a few seconds.")

        with tab_inbox:
            inbox_signals = {k: v for k, v in st.session_state.signals_db.items() if v["status"] == "inbox"}
            
            # Si la base de données est totalement vide (aucun scan jamais lancé)
            if len(st.session_state.signals_db) == 0:
                st.info("📡 Your watch feed is empty. Select your parameters in the Radar above and click 'Run Scan' to start tracking!")
            # Si on a déjà des alertes mais qu'elles sont toutes traitées (Archive/Bookmark)
            elif not inbox_signals:
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
