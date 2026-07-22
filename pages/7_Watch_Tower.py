import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

# Import du vrai moteur de veille (Agent 1)
# Assure-toi que le chemin d'import correspond bien à ton arborescence
try:
    from core.agents.watcher import run_live_watch
except ImportError:
    st.error("Impossible de trouver `watcher.py`. Assure-toi qu'il est bien dans le dossier `core/agents/`.")

st.set_page_config(page_title="Watch Tower | RegWatch", page_icon="📡", layout="wide")

# ==========================================
# DATA LOADING & INITIALIZATION
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

if 'signals_db' not in st.session_state:
    st.session_state.signals_db = {}
if 'scan_executed' not in st.session_state:
    st.session_state.scan_executed = False

def main():
    st.title("📡 Regulatory Watch Tower")
    st.markdown("Monitor global sources and identify regulatory gaps for your product portfolio.")

    ontology_df = get_ontology_data()
    available_countries = get_active_countries()

    # ==========================================
    # ZONE 1 : RADAR CONFIGURATION
    # ==========================================
    st.markdown("### 🎯 Radar Configuration")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        all_categories = sorted(ontology_df['category_label'].dropna().unique().tolist()) if 'category_label' in ontology_df.columns else ["Audio", "Wearables"]
        selected_categories = st.multiselect("Select Categories to monitor", all_categories, default=all_categories[:1] if all_categories else None)
        
    with col2:
        countries = st.multiselect("Target Markets", available_countries, default=["EU", "France"] if "EU" in available_countries else None)
        
    with col3:
        # Clés API requises
        anthropic_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        tavily_key = st.secrets.get("TAVILY_API_KEY", "")
        
        ready_to_scan = bool(selected_categories and countries and anthropic_key and tavily_key)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Run Scan", type="primary", use_container_width=True, disabled=not ready_to_scan):
            with st.spinner("Agent 1 is scanning global sources..."):
                try:
                    # Appel du moteur IA
                    live_entries, usage = run_live_watch(
                        anthropic_key=anthropic_key,
                        tavily_key=tavily_key,
                        categories=selected_categories,
                        markets=countries,
                        timeframe_label="⚡ Last 30 days"
                    )
                    
                    # Transformation des résultats pour l'interface
                    new_db = {}
                    for idx, entry in enumerate(live_entries):
                        sig_id = f"sig_{datetime.now().strftime('%H%M%S')}_{idx}"
                        new_db[sig_id] = {
                            "title": entry.get("title", "Untitled Signal"),
                            "market": ", ".join(entry.get("markets", countries)),
                            "source": entry.get("source", "Web"),
                            "date": entry.get("date", datetime.now().strftime("%Y-%m-%d")),
                            "summary": entry.get("summary", "No summary provided."),
                            "impact": entry.get("impact_prediction", "Pending review."),
                            "status": "inbox",
                            "priority": entry.get("urgency", "LOW").lower()
                        }
                    
                    if new_db:
                        st.session_state.signals_db = new_db
                        st.session_state.scan_executed = True
                        st.success(f"Scan complete! Found {len(new_db)} signals. Estimated AI cost: ${usage.get('cost_usd', 0):.4f}")
                    else:
                        st.session_state.scan_executed = True
                        st.info("Scan completed, but no relevant regulatory signals were identified.")
                        
                except Exception as e:
                    st.error(f"Scan failed: {str(e)}")
                    
        if not (anthropic_key and tavily_key):
            st.caption("⚠️ API keys missing in secrets.toml")

    st.divider()

    # ==========================================
    # ZONE 2 : INBOX & TRIAGE
    # ==========================================
    st.markdown("### 📥 Signal Inbox")
    
    if not st.session_state.scan_executed and not st.session_state.signals_db:
        st.info("No active signals. Configure your radar and run a scan.")
        return

    inbox_signals = {k: v for k, v in st.session_state.signals_db.items() if v["status"] == "inbox"}
    
    if not inbox_signals:
        st.success("🎉 Inbox zero! All signals have been processed.")
    else:
        st.markdown(f"**{len(inbox_signals)} Pending Signal(s)**")
        
        for sig_id, sig_data in inbox_signals.items():
            priority_color = {"high": "🔴", "medium": "🟠", "low": "🟢"}.get(sig_data["priority"], "⚪")
            
            with st.expander(f"{priority_color} [{sig_data['market']}] {sig_data['title']} ({sig_data['date']})", expanded=False):
                st.markdown(f"**Source:** {sig_data['source']}")
                st.markdown(f"**AI Summary:** {sig_data['summary']}")
                st.info(f"**Predicted Impact:** {sig_data['impact']}")
                
                col1, col2, col3 = st.columns(3)
                if col1.button("🗑️ Dismiss", key=f"dismiss_{sig_id}", use_container_width=True):
                    st.session_state.signals_db[sig_id]["status"] = "dismissed"
                    st.rerun()
                    
                if col2.button("🔍 Assign for Review", key=f"review_{sig_id}", use_container_width=True):
                    st.session_state.signals_db[sig_id]["status"] = "under_review"
                    st.rerun()
                    
                if col3.button("⚡ Fast-Track Update", type="primary", key=f"fast_{sig_id}", use_container_width=True):
                    st.toast("Feature coming soon: Auto-update Legal Card!", icon="🚧")

if __name__ == "__main__":
    main()
