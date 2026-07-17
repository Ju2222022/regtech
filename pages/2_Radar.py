import streamlit as st
import sys
import os
import json
import urllib.request
import urllib.error
import pandas as pd
import google.generativeai as genai
import re
import requests

# Connexion au backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.referential import ReferentialManager
from core.agents.classifier import ProductClassifierAgent

st.set_page_config(page_title="Product Screening | RegWatch", page_icon="🎯", layout="wide")

# ==========================================
# FONCTIONS DE SCRAPING (Version Robuste)
# ==========================================
def _tavily_search(query: str, tavily_key: str, max_results: int = 5) -> list:
    payload = json.dumps({"api_key": tavily_key, "query": query, "max_results": max_results, "search_depth": "advanced", "include_answer": False}).encode()
    req = urllib.request.Request("https://api.tavily.com/search", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read()).get("results", [])
    except Exception as e:
        st.error(f"Tavily Error: {str(e)}")
        return []

def _fetch_jina(url: str) -> str:
    try:
        jina_url = f"https://r.jina.ai/{url}"
        # Ajout d'un User-Agent pour éviter le blocage par certains serveurs
        headers = {"Accept": "text/plain", "X-Return-Format": "text", "User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(jina_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
        cut = 2500
        for marker in ["Avis clients", "Avis (", "Customer reviews", "Note moyenne", "Produits similaires"]:
            idx = content.find(marker)
            if 0 < idx < cut: cut = idx
        return content[:cut]
    except Exception as e:
        return ""

def clean_json_output(text: str) -> dict:
    """Nettoie la réponse de l'IA pour extraire le JSON proprement, même si elle ajoute du Markdown."""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)

def extract_tech_profile_with_gemini(snippets_text: str, model_code: str, domain: str) -> dict:
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
        api_key = st.secrets["GEMINI_API_KEY"]
        # On attaque directement le serveur de Google sans passer par leur SDK instable
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
            
        data = response.json()
        raw_text = data['candidates'][0]['content']['parts'][0]['text']
        return clean_json_output(raw_text)
        
    except Exception as e:
        return {"error": f"Direct API Error: {str(e)}"}

def profile_to_text(profile: dict, code: str) -> str:
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

    if "final_brief" not in st.session_state:
        st.session_state["final_brief"] = ""
    if "scraped_profile" not in st.session_state:
        st.session_state["scraped_profile"] = None
    if "raw_snippets" not in st.session_state:
        st.session_state["raw_snippets"] = ""

    # --- MODULE 1 : DECATHLON EXPERT MODE ---
    with st.expander("🛠️ Decathlon Expert Mode (Web Scraping & Bulk CSV)", expanded=True):
        tab_single, tab_bulk = st.tabs(["🔍 Single Product Profiler", "📂 Bulk CSV Upload"])
        
        with tab_single:
            st.markdown("Enter a Model Code to automatically draft the product brief using live web data.")
            col1, col2 = st.columns(2)
            with col1:
                model_code = st.text_input("Model Code (e.g., 8525208, 8759214)")
            with col2:
                domain = st.text_input("Target Domain", value="decathlon.fr")
                
            if st.button("Scrape & Draft Brief"):
                if not model_code:
                    st.warning("Please enter a Model Code.")
                else:
                    try:
                        tavily_key = st.secrets["TAVILY_API_KEY"]
                        with st.spinner("Scraping Decathlon & extracting technical profile..."):
                            
                            results = _tavily_search(f"Decathlon {model_code} {domain}", tavily_key)
                            
                            if not results:
                                st.error("No results found on the web for this code. Tavily might be blocked.")
                            else:
                                best_url = ""
                                for r in results:
                                    u = r.get("url", "")
                                    if "/p/" in u or "/product/" in u or model_code in u:
                                        best_url = u
                                        break
                                if not best_url:
                                    best_url = results[0].get("url", "")

                                jina_content = _fetch_jina(best_url) if best_url else ""
                                
                                # On force l'ajout des snippets Tavily même si Jina échoue
                                snippets = f"[Jina Source: {best_url}]\n{jina_content}\n\n" if jina_content else ""
                                for r in results[:4]:
                                    snippets += f"[{r.get('title')}]\n{r.get('content')}\n\n"
                                
                                st.session_state["raw_snippets"] = snippets 
                                
                                profile = extract_tech_profile_with_gemini(snippets, model_code, domain)
                                
                                # GESTION DE L'ERREUR : On arrête tout si Gemini plante
                                if "error" in profile:
                                    st.error(f"⚠️ AI Extraction Failed: {profile['error']}")
                                else:
                                    st.session_state["scraped_profile"] = profile
                                    st.session_state["final_brief"] = profile_to_text(profile, model_code)
                                    st.success("Drafting complete! Review the brief below and launch the analysis.")
                                    st.rerun()

                    except KeyError:
                        st.error("TAVILY_API_KEY missing in Streamlit Secrets.")

    # --- MODULE 2 : THE RADAR ---
    st.subheader("1. Product Brief")
    
    with st.form("screening_form"):
        product_desc = st.text_area(
            "Technical Specs or Use Case (Edit freely before analysis)", 
            value=st.session_state["final_brief"],
            height=150,
            placeholder="e.g., We are developing a new running smartwatch..."
        )
        submitted = st.form_submit_button("Launch Regulatory Analysis", type="primary")

    # --- MODULE DEBUG (Pour comprendre ce que l'IA a lu) ---
    if st.session_state["raw_snippets"]:
        with st.expander("🔍 Debug: View Raw Web Scraped Data"):
            st.text_area("What the scraper found:", value=st.session_state["raw_snippets"], height=200, disabled=True)

    # --- MODULE 3 : AFFICHAGE DU RAPPORT ---
    if submitted:
        if not product_desc.strip() or product_desc.strip() == "Product Code : Unknown. . Key tech: . Primary function: .":
            st.error("Please provide a valid product description.")
        else:
            with st.spinner("🧠 AI is mapping product specs to your ontology..."):
                result = classifier_agent.analyze_product(product_desc)
                
                if "error" in result:
                    st.error(f"Analysis Failed: {result['error']}")
                else:
                    st.success("Analysis Complete!")
                    st.divider()
                    
                    if st.session_state["scraped_profile"] and not "error" in st.session_state["scraped_profile"]:
                        with st.expander("🛠️ View Structured Tech Profile (JSON)"):
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
