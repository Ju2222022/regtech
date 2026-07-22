import streamlit as st
import sys
import os
import json
import urllib.request
import urllib.error
import re
import time
import pandas as pd
import PyPDF2
from io import BytesIO

# Connexion au backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.referential import ReferentialManager
from core.agents.classifier import ProductClassifierAgent

st.set_page_config(page_title="Product Categorization | RegWatch", page_icon="🎯", layout="wide")

# ==========================================
# FONCTIONS DE SCRAPING & IA
# ==========================================
def _tavily_search(query: str, tavily_key: str, max_results: int = 5) -> list:
    payload = json.dumps({"api_key": tavily_key, "query": query, "max_results": max_results, "search_depth": "advanced", "include_answer": False}).encode()
    req = urllib.request.Request("https" + "://" + "api.tavily.com/search", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read()).get("results", [])
    except Exception as e:
        return []

def _fetch_jina(url: str) -> str:
    try:
        jina_url = "https" + "://" + f"r.jina.ai/{url}"
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
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except:
        return {"error": "Failed to parse JSON"}

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
        raw_key = str(st.secrets["GEMINI_API_KEY"])
        api_key = "".join(raw_key.split())
        
        # LE BOUCLIER ANTI-MARKDOWN DÉFINITIF
        protocol = "https"
        api_domain = "generativelanguage.googleapis.com"
        endpoint = f"/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
        url = protocol + "://" + api_domain + endpoint
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }
        
        data = json.dumps(payload).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            resp_data = json.loads(response.read().decode('utf-8'))
            
        raw_text = resp_data['candidates'][0]['content']['parts'][0]['text']
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
    st.title("🎯 Product Screening & Classification")
    st.markdown("Map new products to internal organizational categories instantly.")

    ref_manager = ReferentialManager()
    classifier_agent = ProductClassifierAgent(ref_manager)

    if "final_brief" not in st.session_state:
        st.session_state["final_brief"] = ""
    if "scraped_profile" not in st.session_state:
        st.session_state["scraped_profile"] = None
    if "raw_snippets" not in st.session_state:
        st.session_state["raw_snippets"] = ""

    # --- ÉTAPE 0 : IMPORTATION DES DONNÉES ---
    with st.expander("🛠️ 0. Data Import (Optional)", expanded=True):
        tab_scrape, tab_upload, tab_bulk = st.tabs(["🌐 Auto-Import (Web)", "📄 Upload Document", "📑 Bulk CSV Analysis"])
        
        # --- ONGLET 1 : SCRAPING SIMPLE ---
        with tab_scrape:
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
                        with st.spinner("Scraping & extracting technical profile..."):
                            results = _tavily_search(f"Decathlon {model_code} {domain}", tavily_key)
                            if not results:
                                st.error("No results found on the web for this code.")
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
                                snippets = f"[Jina Source: {best_url}]\n{jina_content}\n\n" if jina_content else ""
                                for r in results[:4]:
                                    snippets += f"[{r.get('title')}]\n{r.get('content')}\n\n"
                                
                                st.session_state["raw_snippets"] = snippets 
                                profile = extract_tech_profile_with_gemini(snippets, model_code, domain)
                                
                                if "error" in profile:
                                    st.error(f"⚠️ AI Extraction Failed: {profile['error']}")
                                else:
                                    st.session_state["scraped_profile"] = profile
                                    st.session_state["final_brief"] = profile_to_text(profile, model_code)
                                    st.success("Drafting complete! Review the brief below and run classification.")
                                    st.rerun()
                    except KeyError:
                        st.error("TAVILY_API_KEY missing in Streamlit Secrets.")

        # --- ONGLET 2 : UPLOAD PDF ---
        with tab_upload:
            st.markdown("Upload a technical manual, specifications sheet, or product brief to extract its content.")
            uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
            
            if uploaded_file is not None:
                if st.button("Extract Text from PDF"):
                    with st.spinner("Reading document..."):
                        try:
                            pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
                            extracted_text = ""
                            for page in pdf_reader.pages:
                                text = page.extract_text()
                                if text:
                                    extracted_text += text + "\n"
                            
                            if extracted_text.strip():
                                st.session_state["final_brief"] = extracted_text[:8000]
                                st.success("Text extracted successfully! Review it in the Product Brief below.")
                                st.rerun()
                            else:
                                st.warning("The PDF appears to be empty or contains only unreadable images.")
                        except Exception as e:
                            st.error(f"Failed to read PDF: {str(e)}")

        # --- ONGLET 3 : BULK CSV (NOUVEAU) ---
        with tab_bulk:
            st.markdown("Download the template, fill it with your model codes, and upload it for an automated batch analysis.")
            
            # 1. Génération du template
            template_df = pd.DataFrame({"model_code": ["8525208", "8759214"], "domain": ["decathlon.fr", "decathlon.fr"]})
            csv_template = template_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ 1. Download CSV Template", data=csv_template, file_name="regwatch_bulk_template.csv", mime="text/csv")
            
            st.divider()
            
            # 2. Upload et traitement
            uploaded_csv = st.file_uploader("2. Upload filled CSV", type=["csv"])
            if uploaded_csv:
                if st.button("🚀 Run Automated Bulk Analysis", type="primary"):
                    try:
                        df = pd.read_csv(uploaded_csv)
                        if "model_code" not in df.columns:
                            st.error("Invalid CSV format. Please use the provided template with the 'model_code' column.")
                        else:
                            st.info("Starting batch process. This will take time to respect Google's API rate limits...")
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            results = []
                            
                            tavily_key = st.secrets.get("TAVILY_API_KEY", "")
                            
                            for idx, row in df.iterrows():
                                m_code = str(row["model_code"]).strip()
                                dom = row.get("domain", "decathlon.fr").strip()
                                
                                status_text.text(f"Processing Model Code: {m_code} ({idx+1}/{len(df)})")
                                
                                try:
                                    # Étape A: Scraping
                                    search_res = _tavily_search(f"Decathlon {m_code} {dom}", tavily_key)
                                    best_url = search_res[0].get("url", "") if search_res else ""
                                    jina_content = _fetch_jina(best_url) if best_url else ""
                                    
                                    snippets = f"[Jina Source: {best_url}]\n{jina_content}\n\n" if jina_content else ""
                                    for r in search_res[:4]:
                                        snippets += f"[{r.get('title')}]\n{r.get('content')}\n\n"
                                    
                                    # Étape B: Profilage
                                    profile = extract_tech_profile_with_gemini(snippets, m_code, dom)
                                    
                                    if "error" not in profile:
                                        brief_text = profile_to_text(profile, m_code)
                                        # Étape C: Classification
                                        class_result = classifier_agent.analyze_product(brief_text)
                                        
                                        if "error" not in class_result:
                                            matched = class_result.get("matched_categories", [])
                                            cat_names = []
                                            for match in matched:
                                                cat_data = ref_manager.get_category_by_id(match.get("category_id"))
                                                name = cat_data.get("category_label", match.get("category_id")) if cat_data else match.get("category_id")
                                                cat_names.append(f"{name} ({match.get('confidence_score')})")
                                            
                                            results.append({
                                                "model_code": m_code,
                                                "product_summary": class_result.get("analyzed_product", "Summary unavailable"),
                                                "matched_categories": " | ".join(cat_names) if cat_names else "No Regulatory Match"
                                            })
                                        else:
                                            results.append({"model_code": m_code, "product_summary": "Classification Error", "matched_categories": class_result["error"]})
                                    else:
                                        results.append({"model_code": m_code, "product_summary": "Extraction Error", "matched_categories": profile["error"]})
                                except Exception as e:
                                    results.append({"model_code": m_code, "product_summary": "Process Error", "matched_categories": str(e)})
                                    
                                # Délai de sécurité strict (8s) pour ne pas griller le quota Google Free Tier
                                time.sleep(8) 
                                progress_bar.progress((idx + 1) / len(df))
                                
                            status_text.text("Bulk Process Complete!")
                            
                            # Affichage et export
                            res_df = pd.DataFrame(results)
                            st.success(f"Successfully analyzed {len(df)} products!")
                            st.dataframe(res_df)
                            
                            csv_results = res_df.to_csv(index=False).encode('utf-8')
                            st.download_button("⬇️ Download Final Results", data=csv_results, file_name="bulk_analysis_results.csv", mime="text/csv")
                            
                    except Exception as e:
                        st.error(f"Error reading CSV: {str(e)}")

    # --- ÉTAPE 1 : LE PRODUCT BRIEF ---
    st.subheader("1. Product Brief")
    
    with st.form("screening_form"):
        product_desc = st.text_area(
            "Technical Specs or Use Case (Edit freely before analysis)", 
            value=st.session_state["final_brief"],
            height=200,
            placeholder="Paste your product description here, or use the Data Import tools above for single items..."
        )
        submitted = st.form_submit_button("Run Classification", type="primary")

    # --- ÉTAPE 2 : CLASSIFICATION SIMPLE ---
    if submitted:
        if not product_desc.strip() or product_desc.strip() == "Product Code : Unknown. . Key tech: . Primary function: .":
            st.error("Please provide a valid product description.")
        else:
            with st.spinner("🧠 AI is mapping product specs to your ontology..."):
                result = classifier_agent.analyze_product(product_desc)
                
                if "error" in result:
                    st.error(f"Classification Failed: {result['error']}")
                else:
                    tokens = result.get("_tokens", 0)
                    cost_estimate = (tokens / 1000000) * 0.15 
                    st.toast(f"⚡ Classification OK | {tokens} tokens utilisés (~${cost_estimate:.6f})", icon="🪙")
                    
                    st.success("Classification Complete!")
                    st.divider()
                    
                    st.markdown("### 🏷️ Classification Results")
                    matched = result.get("matched_categories", [])
                    
                    if not matched:
                        st.warning("No corresponding category found in the current internal ontology.")
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

if __name__ == "__main__":
    main()
