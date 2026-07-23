import json
import urllib.request
import urllib.error
from datetime import datetime
import os
import pandas as pd

# ── Configuration ──────────────────────────────────────────────────────────────
TIMEFRAMES = {
    "⚡ Last 7 days":    {"time_range": "week"},
    "⚡ Last 30 days":   {"time_range": "month"},
    "📅 Last 12 months": {"time_range": "year"},
}

def get_market_sources(markets: list) -> list:
    sources = []
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'regulatory_pool.csv')
        df = pd.read_csv(csv_path)
        if 'Geographic Zone' in df.columns:
            df = df[df['Geographic Zone'].isin(markets)]
        for _, row in df.iterrows():
            url_col = row.get('URL / Endpoint', row.get('URL', ''))
            if pd.notna(url_col) and str(url_col).strip():
                url = str(url_col).strip()
                domain = url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                sources.append({"type": "Web", "url": url, "domain": domain})
    except Exception as e:
        print(f"Error reading sources: {e}")
    return sources

def get_market_language(market: str) -> str:
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'regulatory_pool.csv')
        df = pd.read_csv(csv_path)
        market_data = df[df['Geographic Zone'] == market]
        if not market_data.empty and 'Query Language' in df.columns:
            lang = market_data['Query Language'].iloc[0]
            if pd.notna(lang) and str(lang).upper() != "MULTI":
                return str(lang).lower()
    except Exception:
        pass
    return "en"

def get_ontology_context(category_name: str) -> dict:
    context = {"definition": "", "strict_attributes": "", "keywords": category_name}
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'default_ontology.csv')
        df = pd.read_csv(csv_path)
        match = df[df['sub_category_label'] == category_name]
        if match.empty:
            match = df[df['category_label'] == category_name]
        if not match.empty:
            if 'business_definition' in df.columns and pd.notna(match['business_definition'].iloc[0]):
                context["definition"] = str(match['business_definition'].iloc[0])
            if 'strict_attributes' in df.columns and pd.notna(match['strict_attributes'].iloc[0]):
                context["strict_attributes"] = str(match['strict_attributes'].iloc[0])
            if 'keywords' in df.columns and pd.notna(match['keywords'].iloc[0]):
                raw_keywords = str(match['keywords'].iloc[0])
                if raw_keywords.replace('|', ' ').strip():
                    context["keywords"] = raw_keywords.replace('|', ' ').strip()
    except Exception:
        pass
    return context

# ── Gemini API Calls (AVEC GESTION D'ERREUR STRICTE) ───────────────────────────
def call_gemini(gemini_key: str, system_prompt: str, user_prompt: str, force_json: bool = False) -> dict:
   url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={gemini_key}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.1}
    }
    if force_json:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.loads(resp.read())
        text_response = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        return {
            "text": text_response,
            "input_tokens": usage.get("promptTokenCount", 0),
            "output_tokens": usage.get("candidatesTokenCount", 0)
        }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        # On lève l'erreur pour la voir dans Streamlit !
        raise Exception(f"Gemini API refusée (Code {e.code}): {error_body}")
    except Exception as e:
        raise Exception(f"Erreur de connexion à Gemini: {e}")

def generate_smart_query(gemini_key: str, business_definition: str, fallback_category: str) -> str:
    if not business_definition: return fallback_category
    system_prompt = "You are an expert in regulatory intelligence and SEO."
    user_prompt = f"Read this product definition:\n{business_definition}\nGenerate a single search engine query (max 6 words) to find recent regulatory updates or laws for this product. Return ONLY the search query string."
    result = call_gemini(gemini_key, system_prompt, user_prompt)
    return result["text"].strip() if result["text"] else fallback_category

def translate_topic(gemini_key: str, topic: str, target_lang: str) -> str:
    if target_lang == "en": return topic
    system = "Translate the given search query into the target language. Return ONLY the translated string."
    user = f"Translate into ISO code '{target_lang}':\n\n{topic}"
    result = call_gemini(gemini_key, system, user)
    return result["text"].strip() if result["text"] else topic

def extract_regulatory_entries(gemini_key: str, topic_en: str, search_results: list, markets: list, business_definition: str, strict_attributes: str) -> tuple:
    system_prompt = f"""You are Agent 1, a regulatory intelligence extractor. Always output in English.
--- PRODUCT CONTEXT ---
DEFINITION: {business_definition}
ATTRIBUTES: {strict_attributes}
-----------------------
OUTPUT SCHEMA REQUIRED (JSON Array):
[
  {{
    "title": "Short title in English",
    "source": "source domain",
    "date": "YYYY-MM-DD",
    "summary": "AI summary in English (2-3 sentences max)",
    "impact_prediction": "Impact based ON THE ATTRIBUTES provided.",
    "markets": ["EU", "France"],
    "source_language": "en|fr|zh|es|de",
    "urgency": "HIGH|MEDIUM|LOW",
    "action_required": "Concrete action or 'Monitor only'",
    "url": "source URL"
  }}
]
Rules:
- Only include genuine regulatory content (laws, standards).
- If nothing relevant is found, return []."""

    results_text = "\n\n".join([f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}" for r in search_results])
    user_message = f"Keywords: {topic_en}\nMarkets: {', '.join(markets)}\n\nSearch results:\n{results_text}"

    result = call_gemini(gemini_key, system_prompt, user_message, force_json=True)
    
    raw_text = result["text"].strip()
    if raw_text.startswith("```json"): raw_text = raw_text[7:]
    if raw_text.startswith("```"): raw_text = raw_text[3:]
    if raw_text.endswith("```"): raw_text = raw_text[:-3]
    
    try:
        entries = json.loads(raw_text.strip())
        if not isinstance(entries, list): entries = []
    except json.JSONDecodeError:
        entries = []
        
    return entries, {"input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"]}

# ── Routing: Web Search (Tavily) (AVEC GESTION D'ERREUR STRICTE) ───────────────
def search_tavily(tavily_key: str, query: str, domains: list, timeframe_cfg: dict = None) -> list:
    def _call(payload_dict: dict) -> list:
        req = urllib.request.Request(
            "[https://api.tavily.com/search](https://api.tavily.com/search)",
            data=json.dumps(payload_dict).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {tavily_key}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read()).get("results", [])

    time_params = {"time_range": timeframe_cfg["time_range"]} if timeframe_cfg and "time_range" in timeframe_cfg else {}
    base = {"query": query, "search_depth": "advanced", "max_results": 10, "include_raw_content": False, **time_params}
    
    results = []
    # 1. On tente avec les domaines stricts
    if domains:
        try: 
            results = _call({**base, "include_domains": domains})
        except Exception:
            pass # Si les domaines bloquent, on passe au fallback global
            
    # 2. Si ça n'a rien donné, on tente une recherche sur tout le web
    if not results:
        try: 
            results = _call(base)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Tavily API refusée (Code {e.code}): Vérifiez vos crédits ou votre clé. Détail: {error_body}")
        except Exception as e:
            raise Exception(f"Erreur de connexion à Tavily: {e}")

    return [{"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")[:800]} for r in results]

# ── Main Run Function ──────────────────────────────────────────────────────────
def run_live_watch(gemini_key: str, tavily_key: str, categories: list, markets: list, timeframe_label: str = "📅 Last 12 months") -> tuple:
    timeframe_cfg = TIMEFRAMES.get(timeframe_label, {"time_range": "year"})
    main_category = categories[0] if categories else ""
    ontology_context = get_ontology_context(main_category)
    
    if ontology_context["keywords"] != main_category:
        base_query = ontology_context["keywords"]
    else:
        base_query = generate_smart_query(gemini_key, ontology_context["definition"], main_category)
    
    search_query = base_query + " regulatory compliance law update"
    
    all_raw_results = []
    total_usage = {"input_tokens": 0, "output_tokens": 0}

    for market in markets:
        market_lang = get_market_language(market)
        sources = get_market_sources([market])
        web_domains = [src["domain"] for src in sources]
        
        target_query = translate_topic(gemini_key, search_query, market_lang) if market_lang != "en" else search_query
        
        # Appel Tavily
        market_results = search_tavily(tavily_key, target_query, web_domains, timeframe_cfg)
        all_raw_results.extend(market_results)
        
    # DIAGNOSTIC : Si Tavily ne trouve rien du tout
    if not all_raw_results:
        raise Exception(f"Tavily a fouillé le web mais a trouvé 0 résultat pour la requête : '{search_query}'. La recherche est peut-être trop restrictive.")

    unique_urls = set()
    filtered_results = [r for r in all_raw_results if r['url'] not in unique_urls and not unique_urls.add(r['url'])]

    # Appel Gemini
    extracted_entries, usage = extract_regulatory_entries(
        gemini_key, search_query, filtered_results, markets, 
        ontology_context["definition"], ontology_context["strict_attributes"]
    )
    
    total_usage["input_tokens"] += usage["input_tokens"]
    total_usage["output_tokens"] += usage["output_tokens"]

    seen_titles = []
    unique_entries = []
    for entry in extracted_entries:
        title = entry.get("title", "").lower().strip()
        is_dup = any(len(set(title.split()) & set(seen.split())) / max(len(set(title.split())), 1) > 0.7 for seen in seen_titles)
        if not is_dup:
            seen_titles.append(title)
            unique_entries.append(entry)

    return unique_entries, total_usage
