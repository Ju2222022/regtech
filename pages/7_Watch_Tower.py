import streamlit as st
import time
import os
import pandas as pd
import csv

st.set_page_config(page_title="Watch Tower | RegWatch", page_icon="📡", layout="wide")

# ==========================================
# DATA LOADING
# ==========================================
@st.cache_data
def get_active_countries():
    """Extract unique countries dynamically from the Regulatory Pool."""
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'regulatory_pool.csv')
        df = pd.read_csv(csv_path)
        countries = sorted(df['Geographic Zone'].dropna().unique().tolist())
        return countries
    except Exception:
        return ["EU", "France", "USA", "China", "UK", "Canada", "India"]

@st.cache_data
def get_tenant_categories():
    """Extract sub-categories dynamically from the Default Ontology."""
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'default_ontology.csv')
        categories = []
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # We use category_label as it represents the specific sub-category name
                cat_name = row.get("category_label", "").strip()
                if cat_name and cat_name not in categories:
                    categories.append(cat_name)
        return sorted(categories)
    except Exception:
        return ["E-Bikes (EPAC)", "Smartwatches", "Audio Headsets"]

def main():
    st.title("📡 Watch Tower")
    st.markdown("Automated regulatory scanning and gap analysis.")

    # ==========================================
    # ZONE 1 : RADAR CONFIGURATION
    # ==========================================
    st.header("🎯 1. Radar", divider="blue")
    
    col1, col2 = st.columns(2)
    with col1:
        # Dynamically loaded from ontology
        available_categories = get_tenant_categories()
        categories = st.multiselect(
            "Product Scope",
            available_categories,
            default=available_categories[:2] if available_categories else []
        )
    with col2:
        # Dynamically loaded from regulatory pool
        available_countries = get_active_countries()
        countries = st.multiselect(
            "Target Geographies",
            available_countries,
            default=["EU", "France"] if "EU" in available_countries else available_countries[:2]
        )
        
    run_scan = st.button("🚀 Run Scan", type="primary", use_container_width=True)

    # ==========================================
    # ZONE 2 : WATCH FEED (RESULTS)
    # ==========================================
    if run_scan:
        with st.spinner("Agent 1 is scanning global sources..."):
            time.sleep(1.5) # Simulating scan time

        st.header("📋 2. Watch Feed", divider="blue")
        
        # KPIs
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Signals Detected", "12")
        kpi2.metric("New Alerts", "3", "since last scan")
        kpi3.metric("Est. AI Cost", "$0.14")

        # Tab layout for Inbox Zero methodology
        tab_inbox, tab_bookmark, tab_archive = st.tabs(["📥 Inbox (Unread)", "📌 Bookmarked", "🗄️ Archive"])

        with tab_inbox:
            st.markdown("### 🔴 High Priority (Action Required)")
            
            # Card 1
            with st.container(border=True):
                st.markdown("#### 📄 [Draft] EU Battery Regulation: New removability requirements for e-scooters")
                st.caption("🌍 **Market:** EU | 🏛️ **Source:** [eur-lex.europa.eu](https://eur-lex.europa.eu) | 📅 **Published:** 2026-07-14 | ⏱️ **Detected:** Today")
                
                st.info("**AI Summary:** The new regulation mandates that LMT batteries (used in e-bikes and e-scooters) must be easily replaceable by an independent professional using commercially available tools starting February 2027.")
                
                st.markdown("##### ⚡ Gap Analysis Prediction")
                st.warning("🔍 2 Legal Cards potentially impacted: \n* EU - E-Bikes \n* FR - E-Bikes")
                
                col_a, col_b, col_c, col_d = st.columns([2, 2, 1, 1])
                with col_a:
                    st.button("📝 Assess Impact", key="assess_1", type="primary", use_container_width=True)
                with col_b:
                    st.button("💬 Chat with Assistant", key="chat_1", use_container_width=True)
                with col_c:
                    st.button("📌 Bookmark", key="bookmark_1", use_container_width=True)
                with col_d:
                    st.button("🚫 Dismiss", key="dismiss_1", use_container_width=True)

            # Card 2
            with st.container(border=True):
                st.markdown("#### 📘 [Guidance] ANSES: New restrictions on flame retardants")
                st.caption("🌍 **Market:** France | 🏛️ **Source:** [anses.fr](https://www.anses.fr) | 📅 **Published:** 2026-07-20 | ⏱️ **Detected:** Yesterday")
                
                st.info("**AI Summary:** ANSES recommends the ban of 3 new chemical compounds used as flame retardants in rigid plastics of sports equipment and audio headsets by late 2026.")
                
                st.markdown("##### ⚡ Gap Analysis Prediction")
                st.warning("🔍 1 Legal Card potentially impacted: \n* FR - Audio Headsets")
                
                col_a, col_b, col_c, col_d = st.columns([2, 2, 1, 1])
                with col_a:
                    st.button("📝 Assess Impact", key="assess_2", type="primary", use_container_width=True)
                with col_b:
                    st.button("💬 Chat with Assistant", key="chat_2", use_container_width=True)
                with col_c:
                    st.button("📌 Bookmark", key="bookmark_2", use_container_width=True)
                with col_d:
                    st.button("🚫 Dismiss", key="dismiss_2", use_container_width=True)

            st.markdown("### 🟡 Medium Priority (Monitor)")
            
            # Card 3
            with st.container(border=True):
                st.markdown("#### ⚖️ [In Force] MIIT: Standard for wireless wearable devices updated")
                st.caption("🌍 **Market:** China | 🏛️ **Source:** [miit.gov.cn](https://www.miit.gov.cn) | 📅 **Published:** 2026-07-18 | ⏱️ **Detected:** 3 days ago")
                
                st.info("**AI Summary:** Minor update regarding the declaration format for Bluetooth transmission power in wearable devices. Technical limits remain unchanged.")
                
                st.markdown("##### ⚡ Gap Analysis Prediction")
                st.success("✅ No structural gap identified. Existing Legal Card (CN - Smartwatches) covers the technical limits.")
                
                col_a, col_b, col_c, col_d = st.columns([2, 2, 1, 1])
                with col_a:
                    st.button("📝 Assess Impact", key="assess_3", type="primary", use_container_width=True)
                with col_b:
                    st.button("💬 Chat with Assistant", key="chat_3", use_container_width=True)
                with col_c:
                    st.button("📌 Bookmark", key="bookmark_3", use_container_width=True)
                with col_d:
                    st.button("🚫 Dismiss", key="dismiss_3", use_container_width=True)

        with tab_bookmark:
            st.markdown("*Your bookmarked signals will appear here for later review.*")
            
        with tab_archive:
            st.markdown("*Processed and dismissed signals are archived here for audit trail purposes.*")

if __name__ == "__main__":
    main()
