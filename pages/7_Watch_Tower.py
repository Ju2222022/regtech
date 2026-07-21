import streamlit as st
import time
import os
import pandas as pd

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
    """Extract full hierarchical data from the Default Ontology."""
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'default_ontology.csv')
        df = pd.read_csv(csv_path)
        return df
    except Exception:
        # Fallback empty dataframe if file missing
        return pd.DataFrame(columns=["perimeter", "category_label", "sub_category_label"])

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "scan_executed" not in st.session_state:
    st.session_state.scan_executed = False

# Mocking a database of signals with states ('inbox', 'bookmark', 'archive')
if "signals_db" not in st.session_state:
    st.session_state.signals_db = {
        "sig_1": {
            "title": "[Draft] EU Battery Regulation: New removability requirements for e-scooters",
            "market": "EU", "source": "eur-lex.europa.eu", "date": "2026-07-14",
            "summary": "The new regulation mandates that LMT batteries must be easily replaceable by an independent professional starting February 2027.",
            "impact": "2 Legal Cards potentially impacted: \n* EU - E-Bikes \n* FR - E-Bikes",
            "status": "inbox", "priority": "high"
        },
        "sig_2": {
            "title": "[Guidance] ANSES: New restrictions on flame retardants",
            "market": "France", "source": "anses.fr", "date": "2026-07-20",
            "summary": "ANSES recommends the ban of 3 new chemical compounds used as flame retardants in rigid plastics of sports equipment.",
            "impact": "1 Legal Card potentially impacted: \n* FR - Audio Headsets",
            "status": "inbox", "priority": "high"
        },
        "sig_3": {
            "title": "[In Force] MIIT: Standard for wireless wearable devices updated",
            "market": "China", "source": "miit.gov.cn", "date": "2026-07-18",
            "summary": "Minor update regarding the declaration format for Bluetooth transmission power in wearable devices.",
            "impact": "No structural gap identified. Existing Legal Card (CN - Smartwatches) covers the technical limits.",
            "status": "inbox", "priority": "medium"
        }
    }

def update_signal_status(sig_id, new_status):
    """Callback to move a signal between tabs."""
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
        # PERIMETER
        if 'perimeter' in ontology_df.columns:
            all_perimeters = sorted(ontology_df['perimeter'].dropna().unique().tolist())
        else:
            all_perimeters = ["Electronics"]
        selected_perimeters = st.multiselect("Perimeter", all_perimeters)
        
    with col2:
        # CATEGORY (Filtered by Perimeter)
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
        # SUB-CATEGORY (Filtered by Category)
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
        # COUNTRIES
        available_countries = get_active_countries()
        countries = st.multiselect(
            "Target Geographies",
            available_countries,
            default=["EU", "France"] if "EU" in available_countries else available_countries[:2]
        )
        
    if st.button("🚀 Run Scan", type="primary", use_container_width=True):
        with st.spinner("Agent 1 is scanning global sources..."):
            time.sleep(1.5)
        st.session_state.scan_executed = True

    # ==========================================
    # ZONE 2 : WATCH FEED (RESULTS)
    # ==========================================
    if st.session_state.scan_executed:
        st.header("📋 2. Watch Feed", divider="blue")
        
        kpi1, kpi2, kpi3 = st.columns(3)
        # Dynamic counting based on state
        inbox_count = sum(1 for s in st.session_state.signals_db.values() if s["status"] == "inbox")
        
        kpi1.metric("Signals Detected", len(st.session_state.signals_db))
        kpi2.metric("Unread Alerts", inbox_count)
        kpi3.metric("Est. AI Cost", "$0.14")

        tab_inbox, tab_bookmark, tab_archive = st.tabs(["📥 Inbox (Unread)", "📌 Bookmarked", "🗄️ Archive"])

        # Helper function to render cards
        def render_signal_card(sig_id, data):
            with st.container(border=True):
                st.markdown(f"#### 📄 {data['title']}")
                st.caption(f"🌍 **Market:** {data['market']} | 🏛️ **Source:** [{data['source']}](https://{data['source']}) | 📅 **Published:** {data['date']}")
                st.info(f"**AI Summary:** {data['summary']}")
                
                if data['priority'] == 'high':
                    st.warning(f"🔍 {data['impact']}")
                else:
                    st.success(f"✅ {data['impact']}")
                
                col_a, col_b, col_c, col_d = st.columns([2, 2, 1, 1])
                with col_a:
                    st.button("📝 Assess Impact", key=f"assess_{sig_id}", type="primary", use_container_width=True)
                with col_b:
                    st.button("💬 Chat with Assistant", key=f"chat_{sig_id}", use_container_width=True)
                
                # Dynamic buttons based on current state
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

        # Render Inbox
        with tab_inbox:
            inbox_signals = {k: v for k, v in st.session_state.signals_db.items() if v["status"] == "inbox"}
            if not inbox_signals:
                st.success("🎉 Inbox Zero! No new regulatory signals to process.")
            for sig_id, data in inbox_signals.items():
                render_signal_card(sig_id, data)

        # Render Bookmarks
        with tab_bookmark:
            bookmark_signals = {k: v for k, v in st.session_state.signals_db.items() if v["status"] == "bookmark"}
            if not bookmark_signals:
                st.markdown("*Your bookmarked signals will appear here.*")
            for sig_id, data in bookmark_signals.items():
                render_signal_card(sig_id, data)
            
        # Render Archive
        with tab_archive:
            archive_signals = {k: v for k, v in st.session_state.signals_db.items() if v["status"] == "archive"}
            if not archive_signals:
                st.markdown("*Processed and dismissed signals are archived here.*")
            for sig_id, data in archive_signals.items():
                render_signal_card(sig_id, data)

if __name__ == "__main__":
    main()
