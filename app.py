import streamlit as st

# Configuration de la page principale (doit toujours être en premier)
st.set_page_config(
    page_title="RegWatch Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("🛡️ RegWatch Platform")
    st.markdown("### AI-Driven Regulatory Intelligence & Compliance")
    st.divider()

    st.markdown("""
    Welcome to **RegWatch**, your intelligent copilot for managing global product compliance. 
    This platform automates the entire regulatory lifecycle, from monitoring official sources to updating your internal conformity documentation.
    """)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Création d'une grille 2x2 pour présenter les modules actuels
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        with st.container(border=True):
            st.markdown("#### 📡 1. Watch Tower")
            st.markdown("Monitor global regulatory sources automatically. The AI extracts actionable signals and filters out the noise based on your specific product taxonomy.")
            
        with st.container(border=True):
            st.markdown("#### 🔍 2. Gap Analysis")
            st.markdown("Instantly cross-reference incoming regulatory alerts with your existing Legal Cards to detect compliance gaps and assess business impact.")
        
    with col2:
        with st.container(border=True):
            st.markdown("#### 📝 3. Legal Card Editor")
            st.markdown("Maintain your Single Source of Truth. Manage technical requirements, markings, and conformity documents for every product and market.")
            
        with st.container(border=True):
            st.markdown("#### ✨ 4. Auto-Draft Updater")
            st.markdown("Let the AI do the heavy lifting. When a regulatory delta is detected, the agent drafts the necessary updates to your Legal Cards for your review and validation.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👈 **Use the sidebar menu to navigate through the modules and start your compliance workflow.**")

if __name__ == "__main__":
    main()
