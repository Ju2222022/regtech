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
    """Charge l'historique des signaux depuis la Watch Tower."""
    if os.path.exists(SIGNALS_DB_PATH):
        try:
            with open(SIGNALS_DB_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def load_cards_data():
    """Charge toutes les Legal Cards validées."""
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

    # Chargement des données
    signals_dict = load_signals_data()
    cards_list = load_cards_data()

    # Calcul des KPIs
    total_signals = len(signals_dict)
    inbox_signals = sum(1 for s in signals_dict.values() if s.get("status") == "inbox")
    bookmarked_signals = sum(1 for s in signals_dict.values() if s.get("status") == "bookmark")
    total_cards = len(cards_list)

    # --- SECTION 1 : KPIs ---
    st.header("🎯 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Signals Tracked", total_signals)
    col2.metric("Pending Alerts (Inbox)", inbox_signals, delta="- To Review" if inbox_signals > 0 else "All Clear", delta_color="inverse")
    col3.metric("Bookmarked Signals", bookmarked_signals)
    col4.metric("Active Legal Cards", total_cards)

    st.divider()

    # --- SECTION 2 : VISUALIZATIONS ---
    col_charts1, col_charts2 = st.columns(2, gap="large")

    with col_charts1:
        st.subheader("📈 Signals by Priority")
        if total_signals > 0:
            # Transformation du dictionnaire en DataFrame pour facilement faire des graphiques
            df_signals = pd.DataFrame(signals_dict.values())
            
            # On compte les occurrences de chaque priorité et on met un peu de couleur
            priority_counts = df_signals['priority'].value_counts().reset_index()
            priority_counts.columns = ['Priority', 'Count']
            
            # Graphique natif Streamlit
            st.bar_chart(priority_counts.set_index('Priority'), color="#FF4B4B")
        else:
            st.info("📡 No signals data available yet. Run a scan in the Watch Tower.")

    with col_charts2:
        st.subheader("🗂️ Legal Cards Coverage")
        if total_cards > 0:
            # Extraction des catégories depuis les métadonnées des fiches JSON
            cats = [c.get('metadata', {}).get('category', 'Unknown') for c in cards_list]
            df_cats = pd.DataFrame(cats, columns=['Category'])
            
            cat_counts = df_cats['Category'].value_counts().reset_index()
            cat_counts.columns = ['Category', 'Count']
            
            # Graphique natif Streamlit
            st.bar_chart(cat_counts.set_index('Category'), color="#0068C9")
        else:
            st.info("📝 No legal cards active. Save your first card in the Editor.")
    
    st.divider()

    # --- SECTION 3 : RECENT ACTIVITY TABLE ---
    st.subheader("⏱️ Recent Regulatory Activity")
    if total_signals > 0:
        df_recent = pd.DataFrame(signals_dict.values())
        
        # On garde les colonnes intéressantes
        if all(col in df_recent.columns for col in ['date', 'title', 'market', 'priority', 'status']):
            df_display = df_recent[['date', 'title', 'market', 'priority', 'status']].copy()
            
            # Tri par date décroissante
            df_display['date'] = pd.to_datetime(df_display['date'], errors='coerce')
            df_display = df_display.sort_values(by='date', ascending=False).head(10)
            
            # Formatage de la date pour un affichage propre
            df_display['date'] = df_display['date'].dt.strftime('%Y-%m-%d')
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No recent activity to display.")

if __name__ == "__main__":
    main()
