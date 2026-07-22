import streamlit as st
import pandas as pd
import os
from datetime import datetime

try:
    from core.agents.watcher import run_live_watch
except ImportError:
    st.error("Impossible de trouver `watcher.py`. Assure-toi qu'il est bien dans `core/agents/`.")

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
    except Exception:
        pass
    return ["EU", "France", "USA", "China"]

@st.cache_data
def get_ontology_data():
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'default_ontology.csv')
        return pd.read_csv(csv_path)
    except Exception:
        return pd.DataFrame()

if 'signals_db' not in st.session_state:
    st.session_state.signals_db = {}
if 'scan_executed' not in st.session_state:
    st.session_state.scan_executed = False

def main():
    st.title("📡 Regulatory Watch Tower")
    st.markdown("Monitor global sources and identify regulatory gaps using Gemini AI.")

    ontology_df = get_ontology_data()
    available_countries = get_active_countries()

    # ==========================================
    # ZONE 1 : RADAR CONFIGURATION
    # ==========================================
    st.markdown("### 🎯 Radar Configuration")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        all_perimeters = sorted(ontology_df['perimeter'].dropna().unique().tolist()) if not ontology_df.empty and 'perimeter' in ontology_df.columns else []
        selected_perimeter = st.selectbox("Perimeter", all_perimeters, index=None, placeholder="Select Perimeter...")
        
    with col2:
        filtered_cats = ontology_df[ontology_df['perimeter'] == selected_perimeter] if selected_perimeter else pd.DataFrame()
        all_categories = sorted(filtered_cats['category_label'].dropna().unique().tolist()) if not filtered_cats.empty else []
        selected_category = st.selectbox("Category", all_categories, index=None, placeholder="Select Category...")
        
    with col3:
        filtered_subcats = filtered_cats[filtered_cats['category_label'] == selected_category] if selected_category else pd.DataFrame()
        all_subcategories = sorted(filtered_subcats['sub_category_label'].dropna().unique().tolist()) if not filtered_subcats.empty else []
        selected_subcategory = st.selectbox("Sub-Category", all_subcategories, index=None, placeholder="Select Sub-Category...")

    with col4:
        selected_market = st.selectbox("Target Market", available_countries, index=None, placeholder="Select Market...")

    # Vérification que la matrice est complète
    matrix_is_complete = all([selected_perimeter, selected_category, selected_subcategory, selected_market])

    gemini_key = st.secrets.get("GEMINI_API_KEY", "")
    tavily_key = st.secrets.get("TAVILY_API_KEY", "")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 Run Scan", type="primary", use_container_width=True, disabled=not matrix_is_complete):
        if not (gemini_key and tavily_key):
            st.error("⚠️ API keys missing in your secrets setup.")
            return

        # On affiche clairement ce que l'Agent cherche
        with st.spinner(f"Gemini & Tavily are scanning for '{selected_subcategory}' in '{selected_market}'..."):
            try:
                # On envoie la sous-catégorie exacte pour que le Watcher lise la bonne définition métier !
                live_entries, usage = run_live_watch(
                    gemini_key=gemini_key,
                    tavily_key=tavily_key,
                    categories=[selected_subcategory],
                    markets=[selected_market],
                    timeframe_label="⚡ Last 30 days"
                )
                
                new_db = {}
                for idx, entry in enumerate(live_entries):
                    sig_id = f"sig_{datetime.now().strftime('%H%M%S')}_{idx}"
                    new_db[sig_id] = {
                        "title": entry.get("title", "Untitled Signal"),
                        "market": selected_market,
                        "source": entry.get("source", "Web"),
                        "date": entry.get("date", datetime.now().strftime("%Y-%m-%d")),
                        "summary": entry.get("summary", "No summary provided."),
                        "impact": entry.get("impact_prediction", "Pending review."),
                        "status": "inbox",
                        "priority": entry.get("urgency", "LOW").lower()
                    }
                
                st.session_state.scan_executed = True
                
                if new_db:
                    # On ajoute les nouveaux résultats sans effacer les anciens qui sont dans l'inbox
                    st.session_state.signals_db.update(new_db)
                    st.success(f"Scan complete! Found {len(new_db)} signals. (Tokens used: {usage['input_tokens']} in / {usage['output_tokens']} out)")
                else:
                    # Message clair si rien n'est trouvé
                    st.warning(f"Scan completed. Tavily searched the web, but Gemini determined there were no NEW regulatory updates for '{selected_subcategory}' in the last 30 days.")
                    
            except Exception as e:
                st.error(f"Scan failed: {str(e)}")

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
