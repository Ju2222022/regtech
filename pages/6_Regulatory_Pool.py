import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Regulatory Pool | RegWatch", page_icon="🌍", layout="wide")

# ==========================================
# GESTION DES DONNÉES (Sauvegarde locale)
# ==========================================
# Chemin dynamique vers le fichier CSV dans le dossier data/
DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'regulatory_pool.csv')

def load_pool_data():
    """Charge les données ou crée une structure vierge si le fichier n'existe pas."""
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=[
            "Source Name", 
            "Geographic Zone", 
            "Regulatory Domain", 
            "Acquisition Type", 
            "Query Language", 
            "URL / Endpoint", 
            "Active"
        ])

def save_pool_data(df):
    """Sauvegarde le dataframe dans le fichier CSV."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    df.to_csv(DATA_FILE, index=False)

# ==========================================
# INTERFACE UTILISATEUR
# ==========================================
def main():
    st.title("🌍 Regulatory Sources Pool")
    st.markdown("Manage your dynamic list of monitoring sources (API, RSS, Scraping) across all geographic zones and domains.")

    # Chargement des données
    df = load_pool_data()

    # Consignes d'utilisation
    with st.expander("🛠️ How to use the Data Editor", expanded=False):
        st.markdown("""
        * **Add a row:** Scroll to the bottom of the table and click the empty row.
        * **Edit a cell:** Double-click on any cell to modify its content.
        * **Delete a row:** Click the checkbox on the far left of a row, then press the `Delete` key on your keyboard.
        * **Save:** Do not forget to click the **Save Changes** button below the table!
        """)

    # Affichage du tableau interactif
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Source Name": st.column_config.TextColumn("Source Name", required=True),
            "Geographic Zone": st.column_config.TextColumn("Geographic Zone", required=True),
            "Regulatory Domain": st.column_config.TextColumn("Regulatory Domain", required=True),
            "Acquisition Type": st.column_config.SelectboxColumn(
                "Acquisition Type", 
                help="How do we extract data from this source?",
                options=["API JSON", "API XML", "RSS Feed", "Web Scraping"],
                required=True
            ),
            "Query Language": st.column_config.SelectboxColumn(
                "Query Language", 
                help="The language used by the source (determines translation needs).",
                options=["EN", "FR", "DE", "ES", "ZH", "JA", "Multi"],
                required=True
            ),
            "URL / Endpoint": st.column_config.TextColumn("URL / Endpoint", required=True),
            "Active": st.column_config.CheckboxColumn("Active Source", default=True)
        }
    )

    # Bouton de sauvegarde
    if st.button("💾 Save Changes", type="primary"):
        save_pool_data(edited_df)
        st.success("Regulatory Pool successfully updated!")
        st.balloons()

if __name__ == "__main__":
    main()
