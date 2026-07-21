import streamlit as st
import time

st.set_page_config(page_title="Watch Tower | RegWatch", page_icon="📡", layout="wide")

def main():
    st.title("📡 Watch Tower")
    st.markdown("Surveillance réglementaire automatisée et analyse d'impact.")

    # ==========================================
    # ZONE 1 : LE RADAR (Configuration)
    # ==========================================
    st.header("🎯 1. Le Radar", divider="blue")
    
    col1, col2 = st.columns(2)
    with col1:
        categories = st.multiselect(
            "Périmètre Produit",
            ["Montres Connectées", "Vélos Électriques (EPAC)", "Casques Audio", "Textile Sportif", "Électronique Générale"],
            default=["Montres Connectées", "Vélos Électriques (EPAC)"]
        )
    with col2:
        # Inspiré par la ligne de drapeaux de Cleo
        pays = st.multiselect(
            "Ciblage Géographique",
            ["🇪🇺 EU", "🇫🇷 France", "🇺🇸 USA", "🇨🇳 Chine", "🇬🇧 UK", "🇮🇳 Inde"],
            default=["🇪🇺 EU", "🇫🇷 France"]
        )
        
    lancer_veille = st.button("🚀 Lancer la Veille Multilingue", type="primary", use_container_width=True)

    # ==========================================
    # ZONE 2 & 3 : TRIAGE ET IMPACT (Résultats)
    # ==========================================
    if lancer_veille:
        with st.spinner("L'Agent Veilleur interroge les sources (traduction en cours)..."):
            time.sleep(1.5) # Simulation du temps de recherche

        st.header("📋 2. Centre de Triage", divider="blue")
        
        # KPIs
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Signaux Détectés", "12")
        kpi2.metric("Nouvelles Alertes", "3", "depuis la dernière veille")
        kpi3.metric("Coût IA Estimé", "$0.14")

        # Filtre de focus
        focus_nouveaute = st.toggle("✨ Afficher uniquement les nouveautés", value=True)

        st.markdown("### 🔴 Alertes Critiques (Action Requise)")
        
        # Accordéon 1 (Signal 1)
        with st.expander("🔴 EU Battery Regulation: New removability requirements for e-scooters (Feb 2027)", expanded=True):
            st.markdown("**Source:** eur-lex.europa.eu | **Date:** Aujourd'hui | **Marché:** 🇪🇺 EU")
            st.info("**Résumé IA:** La nouvelle réglementation impose que les batteries LMT (utilisées dans les vélos et trottinettes électriques) soient facilement remplaçables par un professionnel indépendant avec des outils du commerce à partir de février 2027.")
            
            # ZONE 3 (Impact) intégrée
            st.markdown("#### ⚡ Pré-Analyse d'Impact")
            st.warning("🔍 2 fiches légales potentiellement impactées : \n* EU - Vélos Électriques \n* FR - Vélos Électriques")
            
            c1, c2 = st.columns([1, 5])
            with c1:
                st.button("📝 Évaluer l'impact", key="impact_1")

        # Accordéon 2 (Signal 2)
        with st.expander("🔴 ANSES (France): Nouvelles restrictions sur les retardateurs de flamme"):
            st.markdown("**Source:** anses.fr | **Date:** Hier | **Marché:** 🇫🇷 France")
            st.info("**Résumé IA:** L'ANSES recommande l'interdiction de 3 nouveaux composés chimiques utilisés comme retardateurs de flamme dans les plastiques rigides d'équipements sportifs et casques audio d'ici fin 2026.")
            
            st.markdown("#### ⚡ Pré-Analyse d'Impact")
            st.warning("🔍 1 fiche légale potentiellement impactée : \n* FR - Casques Audio")
            
            c1, c2 = st.columns([1, 5])
            with c1:
                st.button("📝 Évaluer l'impact", key="impact_2")

        st.markdown("### 🟡 À Anticiper (Surveillance)")
        
        # Accordéon 3 (Signal 3)
        with st.expander("🟡 MIIT (China): Draft standard for wireless wearable devices"):
            st.markdown("**Source:** miit.gov.cn | **Date:** Il y a 3 jours | **Marché:** 🇨🇳 Chine")
            st.info("**Résumé IA:** Projet de norme concernant l'efficacité énergétique et la puissance d'émission Bluetooth des dispositifs portables (montres). En phase de consultation publique pendant 60 jours.")
            
            st.markdown("#### ⚡ Pré-Analyse d'Impact")
            st.success("✅ Aucune fiche légale existante pour ce marché/produit. Création recommandée ?")
            
            c1, c2 = st.columns([1, 5])
            with c1:
                st.button("📝 Créer une fiche", key="impact_3")

if __name__ == "__main__":
    main()
