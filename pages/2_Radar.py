import streamlit as st
import sys
import os
import json
import urllib.request
import urllib.error
import pandas as pd
import google.generativeai as genai

# Connexion au backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.referential import ReferentialManager
from core.agents.classifier import ProductClassifierAgent

st.set_page_config(page_title="Product Screening | RegWatch", page_icon="🎯", layout="wide")

# ==========================================
# FONCTIONS DE SCRAPING (Inspirées de profiler.py)
# ==========================================
def _tavily_search(query: str, tavily_key: str, max_results: int = 5) -> list:
    payload = json.dumps({"api_key": tavily_key, "query": query, "max_results": max_results, "search_depth": "advanced", "include_answer": False}).encode()
    req = urllib.request.Request("https://api.tavily.com/search", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read()).get("results", [])
    except Exception:
        return []

def _fetch_jina(url: str) -> str:
    try:
        jina_url = f"https://r.jina.ai/{url}"
        req = urllib.request.Request(jina_url, headers={"Accept": "text/plain", "X-Return-Format": "text"}, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
        cut = 2500
        for marker in ["Avis clients", "Avis (", "Customer reviews", "Note moyenne", "Produits similaires"]:
            idx = content.find(marker)
            if 0 < idx < cut: cut = idx
        return content[:cut]
    except Exception:
        return ""

def extract_tech_profile_with_gemini(snippets_text: str, model_code: str, domain: str) -> dict:
    """Utilise Gemini pour extraire le profil technique JSON depuis les snippets."""
    system_prompt = """You are Agent 2, a product technology profiler for Decathlon Electronics.
    Given web search snippets about a product, extract a structured technology profile. Focus ONLY on factual technical information. Do NOT invent.
    Respond ONLY with valid JSON matching this structure:
    {
      "name": "", "description": "",
      "technologies": {"wireless": [], "power": [], "primary_function": "", "sensors": [], "connectivity": []},
      "key_specs": {"battery_life": "", "water_resistance": "", "weight": ""}
    }"""
    
    prompt = f"{system_prompt}\n\nModel code: {model_code}\nDomain: {domain}\n\nSearch snippets:\n{snippets_text[:4000]}"
    
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json", temperature=0.1))
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}

def profile_to_text(profile: dict, code: str) -> str:
    """Transforme le JSON structuré en un brief texte pour l'Agent Classifier."""
    techs = profile.get("technologies", {})
    all_info = techs.get("wireless", []) + techs.get("power", []) + techs.get("sensors", []) + techs.get("connectivity", [])
    desc = profile.get("description", "")
    extra = ", ".join(all_info)
    return f"Product Code {code}: {profile.get('name', 'Unknown')}. {desc}. Key tech: {extra}. Primary function: {techs.get('primary_function', '')}."

# ==========================================
# INTERFACE UTILISATEUR
# ==========================================
def main():
    st.title("🎯 Product Screening & Risk Mapping")
    st.markdown("Identify applicable regulatory frameworks instantly.")

    ref_manager = ReferentialManager()
    classifier_agent = ProductClassifierAgent(ref_manager)

    # Variables de session pour gérer l'affichage
    if "final_brief" not in st.session_state:
        st.session_state["final_brief"] = ""
    if "scraped_profile" not in st.session_state:
        st.session_state["scraped_profile"] = None

    # --- MODULE 1 : DECATHLON EXPERT MODE (TAVILY) ---
    with st.expander("🛠️ Decathlon Expert Mode (Web Scraping & Bulk CSV)", expanded=False):
        tab_single, tab_bulk = st.tabs(["🔍 Single Product Profiler", "📂 Bulk CSV Upload"])
        
        with tab_single:
            st.markdown("Enter a Model Code to automatically draft the product brief using live web data.")
            col1, col2 = st.columns(2)
            with col1:
                model_code = st.text_input("Model Code (e.g., 8525208)")
            with col2:
                domain = st.text_input("Target Domain", value="decathlon.fr")
                
            if st.button("Scrape & Draft Brief"):
                if not model_code:
                    st.warning("Please enter a Model Code.")
                else:
                    try:
                        tavily_key = st.secrets["TAVILY_API_KEY"]
                        with st.spinner("Scraping Decathlon & extracting technical profile..."):
                            # 1. Search
                            results = _tavily_search(f"{model_code} {domain}", tavily_key)
                            best_url = results[0].get("url", "") if results else ""
                            jina_content = _fetch_jina(best_url) if best_url else ""
                            
                            snippets = f"[Jina]\n{jina_content}\n\n" if jina_content else ""
                            for r in results[:3]:
                                snippets += f"[{r.get('title')}]\n{r.get('content')}\n\n"
                            
                            # 2. Extract with Gemini
                            profile = extract_tech_profile_with_gemini(snippets, model_code, domain)
                            
                            # 3. Save to state
                            st.session_state["scraped_profile"] = profile
                            st.session_state["final_brief"] = profile_to_text(profile, model_code)
                            st.success("Drafting complete! Review the brief below and launch the analysis.")
                    except KeyError:
                        st.error("TAVILY_API_KEY missing in Streamlit Secrets.")

        with tab_bulk:
            st.info("Batch processing will analyze multiple codes and output a consolidated Excel report.")
            # Bouton pour télécharger le template
            df_template = pd.DataFrame({"model_code": ["8525208", "8554912"], "domain_hint": ["decathlon.fr", "decathlon.fr"]})
            csv = df_template.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV Template", data=csv, file_name="regwatch_bulk_template.csv", mime="text/csv")
            
            uploaded_file = st.file_uploader("Upload filled CSV", type=["csv"])
            if uploaded_file and st.button("Run Bulk Analysis"):
                st.warning("Bulk engine UI is currently being wired. Check back in the next version!")

    st.divider()

    # --- MODULE 2 : THE RADAR (MANUAL OR AUTO-FILLED) ---
    st.subheader("1. Product Brief")
    
    with st.form("screening_form"):
        # La text area se pré-remplit si on a utilisé le scraper juste avant
        product_desc = st.text_area(
            "Technical Specs or Use Case (Edit freely before analysis)", 
            value=st.session_state["final_brief"],
            height=150,
            placeholder="e.g., We are developing a new running smartwatch..."
        )
        submitted = st.form_submit_button("Launch Regulatory Analysis", type="primary")

    # --- MODULE 3 : AFFICHAGE DU RAPPORT ---
    if submitted:
        if not product_desc.strip():
            st.error("Please provide a product description.")
        else:
            with st.spinner("🧠 AI is mapping product specs to your ontology..."):
                result = classifier_agent.analyze_product(product_desc)
                
                if "error" in result:
                    st.error(f"Analysis Failed: {result['error']}")
                else:
                    st.success("Analysis Complete!")
                    st.divider()
                    
                    # Affichage du profil technique si le scraper a été utilisé
                    if st.session_state["scraped_profile"] and not "error" in st.session_state["scraped_profile"]:
                        with st.expander("🛠️ View Raw Extracted Tech Profile (JSON)"):
                            st.json(st.session_state["scraped_profile"])
                            
                    st.markdown("### 🤖 AI Product Understanding")
                    st.info(result.get("analyzed_product", ""))
                    
                    st.divider()
                    st.markdown("### 📡 Radar: Applicable Categories")
                    matched = result.get("matched_categories", [])
                    
                    if not matched:
                        st.warning("No regulatory category was detected for this product.")
                    else:
                        for match in matched:
                            cat_id = match.get("category_id")
                            score = match.get("confidence_score", "UNKNOWN")
                            justification = match.get("justification", "")
                            
                            cat_details = ref_manager.get_category_by_id(cat_id)
                            label = cat_details.get("category_label", cat_id) if cat_details else cat_id
                            icon = "🟢" if score == "HIGH" else "🟠" if score == "MEDIUM" else "🔴"
                            
                            with st.expander(f"{icon} {label} (Confidence: {score})", expanded=True):
                                st.markdown(f"**AI Justification:** *{justification}*")
                                if cat_details:
                                    st.divider()
                                    col_fw, col_deliv = st.columns(2)
                                    with col_fw:
                                        st.markdown("**⚖️ Legal Framework**")
                                        for fw in cat_details.get("reference_legal_framework", []):
                                            st.markdown(f"- {fw}")
                                    with col_deliv:
                                        st.markdown("**📋 Deliverables**")
                                        for dl in cat_details.get("expected_deliverables", []):
                                            st.markdown(f"- {dl}")

if __name__ == "__main__":
    main()
