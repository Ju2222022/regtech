import streamlit as st

# 1. Configuration globale de l'application
st.set_page_config(
    page_title="RegWatch | Regulatory Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Initialisation du Session State (Tracker de coûts et d'états)
def init_session_state():
    """Initialise les variables globales nécessaires au fonctionnement de l'app."""
    if "session_tokens" not in st.session_state:
        # Suivi métrique affiché dans le footer de chaque page
        st.session_state["session_tokens"] = {
            "input": 0,
            "output": 0,
            "cost_usd": 0.0,
            "calls": 0
        }
    
    if "current_tenant" not in st.session_state:
        # Permettra de charger la bonne configuration JSON selon le client
        st.session_state["current_tenant"] = "default_client"

init_session_state()

# 3. Construction de l'interface principale (Landing Page)
def main():
    st.title("🛡️ RegWatch Platform")
    st.markdown("### The Last Mile of Product Compliance")
    
    st.divider()
    
    # Présentation macro de l'architecture pour l'utilisateur
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**1. Global Watch & Ontology**\n\nMonitor official sources automatically and map them to your specific product taxonomy.")
        st.warning("**3. Legal Sheet Updater**\n\nMaintain your conformity documentation up-to-date with AI-driven text suggestions.")
        
    with col2:
        st.success("**2. Risk Mapping & Impact**\n\nCross-reference incoming alerts with your hardware catalogue to identify compliance gaps.")
        st.error("**4. R&D Requirements**\n\nGenerate instant design rules, testing protocols, and marking requirements for your engineering teams.")

    st.divider()
    
    # 4. Volet Latéral : Navigation et Assistant
    with st.sidebar:
        st.header("Navigation")
        st.markdown("*Use the sidebar menu above to navigate through the modules.*")
        
        st.divider()
        
        # Espace réservé pour la Vue 6 (Chatbot Assistant)
        st.header("💬 RegWatch Assistant")
        st.caption("Your context-aware regulatory copilot.")
        
        # Zone de chat simplifiée pour la landing page
        user_query = st.chat_input("Ask a regulatory question...")
        if user_query:
            st.write(f"*(Assistant module not yet connected)* You asked: {user_query}")
        
        st.divider()
        
        # Affichage des métriques de coûts (Session State)
        st.caption("📊 **Session Cost Tracker**")
        tokens = st.session_state["session_tokens"]
        st.code(f"Calls: {tokens['calls']} | Cost: ${tokens['cost_usd']:.4f}")

if __name__ == "__main__":
    main()
