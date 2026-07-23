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

# ── Dynamic Data Loaders (Ontology & Pool) ─────────────────────────────────────
def get_market_sources(markets: list) -> list:
    """Reads regulatory_pool.csv and returns sources with their Acquisition Type (Web vs API)."""
    sources = []
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'regulatory_pool.csv')
        df = pd.read_csv(csv_path)
        
        if 'Geographic Zone' in df.columns:
            df = df[df['Geographic Zone'].isin(markets)]
            
        for _, row in df.iterrows():
            acq_type = str(row.get('Acquisition Type', 'Web')).strip()
            url_col = row.get('URL / Endpoint', row.get('URL', ''))
            
            if pd.notna(url_col) and str(url_col).strip():
                url = str(url_col).strip()
                domain = url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                sources.append({
                    "type": acq_type,
                    "url": url,
                    "domain": domain
                })
    except Exception as e:
        print(f"Error reading regulatory pool sources: {e}")
        
    return sources

def get_market_language(market: str) -> str:
    """Extracts target language from regulatory_pool.csv."""
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'regulatory_pool.csv')
        df = pd.read_csv(csv_path)
        market_data = df[df['Geographic Zone'] == market]
        if not market_data.empty and 'Query Language' in df.columns:
            lang = market_data['Query Language'].iloc[0]
            if pd.notna(lang) and str(lang).upper() != "MULTI":
                return str(lang).lower()
    except Exception as e:
        print(f"Error reading market language: {e}")
    return "en"

def get_ontology_context(category_name: str) -> dict:
    """Extracts business definitions, strict attributes, and keywords from the ontology."""
    context = {
        "definition": "No specific business definition provided.",
        "strict_attributes": "None specified.",
        "keywords": category_name
    }
    
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'default_ontology.csv')
        df = pd.read_csv(csv_path)
        
        # Match sub-category or category
        match = df[df['sub_category_label'] == category_name]
        if match.empty:
            match = df[df['category_label'] == category_name]
            
        if not match.empty:
            # 1. Business Definition
            if 'business_definition' in df.columns and pd.notna(match['business_definition'].iloc[0]):
                context["definition"] = str(match['business_definition'].iloc[0])
                
            # 2. Strict Attributes
            if 'strict_attributes' in df.columns and pd.notna(match['strict_attributes'].iloc[0]):
                context["strict_attributes"] = str(match['strict_attributes'].iloc[0])
                
            # 3. Keywords (for search engine optimization)
            if 'keywords' in df.columns and pd.notna(match['keywords'].iloc[0]):
                raw_keywords = str(match['keywords'].iloc[0])
                # Format pipe-separated keywords into a clean search string
                clean_keywords = raw_keywords.replace('|', ' ').strip()
                if clean_keywords:
                    context["keywords"] = clean_keywords
                    
    except Exception as e:
        print(f"Error reading ontology context: {e}")
        
    return context

def get_system_prompt(business_definition: str, strict_attributes: str) -> str:
    """Builds the strict Gemini extraction prompt using the full ontology context."""
    return f"""You are Agent 1, a highly precise regulatory intelligence extractor for product compliance.

You receive web search results and must extract structured regulatory entries.
Always output in English, regardless of the source language.

--- PRODUCT ONTOLOGY CONTEXT ---
BUSINESS DEFINITION:
{business_definition}

STRICT ATTRIBUTES TO MONITOR:
{strict_attributes}
--------------------------------

OUTPUT SCHEMA REQUIRED (JSON Array):
[
  {{
    "title": "Short title in English",
    "source": "source domain",
    "date": "YYYY-MM-DD or estimated",
    "summary": "AI summary in English (2-3 sentences max)",
    "impact_prediction": "Description of potential gap / impact based ON THE STRICT ATTRIBUTES provided.",
    "markets": ["EU", "France"],
    "source_language": "en|fr|zh|es|de",
    "urgency": "HIGH|MEDIUM|LOW",
    "action_required": "Concrete action or 'Monitor only'",
    "url": "source URL"
  }}
]

Rules:
- Translate all extracted content to English.
- Only include genuine regulatory content (directives, standards, laws, enforcement notices).
- If the search results do not explicitly affect the Product Ontology Context provided, ignore them.
- urgency HIGH = deadline < 6 months or already in force.
- urgency MEDIUM = deadline 6-18 months.
- urgency LOW = consultation or > 18 months.
- If nothing relevant is found, return an empty array [].
"""

# ── Gemini API Calls ───────────────────────────────────────────────────────────
def call_gemini(gemini_key: str, system_prompt: str, user_prompt: str, force_json: bool = False) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.1} # Low temp for factual extraction
    }
    
    if force_json:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
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
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return {"text": "[]" if force_json else "", "input_tokens": 0, "output_tokens": 0}

def translate_topic(gemini_key: str, topic: str, target_lang: str) -> str:
    if target_lang == "en":
        return topic
    system = "Translate the given search query into the target language. Return ONLY the translated string."
    user = f"Translate into ISO code '{target_lang}':\n\n{topic}"
    result = call_gemini(gemini_key, system, user)
    return result["text"].strip() if result["text"] else topic

def extract_regulatory_entries(gemini_key: str, topic_en: str, search_results: list, markets: list, system_prompt: str) -> tuple:
    if not search_results:
        return [], {"input_tokens": 0, "output_tokens": 0}

    results_text = "\n\n".join([
        f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}"
        for r in search_results
    ])

    user_message = (
        f"Extract regulatory entries from these search results.\n\n"
        f"Search keywords used: {topic_en}\nTarget markets: {', '.join(markets)}\n"
        f"Search date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"Search results:\n{results_text}"
    )

    result = call_gemini(gemini_key, system_prompt, user_message, force_json=True)
    
    # Robust JSON parsing
    raw_text = result["text"].strip()
    if raw_text.startswith("```json"): raw_text = raw_text[7:]
    if raw_text.startswith("```"): raw_text = raw_text[3:]
    if raw_text.endswith("```"): raw_text = raw_text[:-3]
    
    try:
        entries = json.loads(raw_text.strip())
        if not isinstance(entries, list):
            entries = []
    except json.JSONDecodeError as e:
        print(f"Failed to parse Gemini JSON: {e}")
        entries = []
        
    return entries, {"input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"]}

# ── Routing: Web Search (Tavily) & API ─────────────────────────────────────────
def route_api_request(source: dict) -> list:
    """Placeholder for direct API requests (e.g., EUR-Lex API, Safety Gate)."""
    # Dans une prochaine itération BMAD, nous coderons les requêtes urllib spécifiques ici.
    # Pour le moment, on retourne vide pour forcer l'usage du Web si l'API n'est pas codée.
    print(f"[Router] Requires direct API integration for: {source['url']}")
    return []

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

    time_params = {}
    if timeframe_cfg and timeframe_cfg.get("time_range"):
        time_params["time_range"] = timeframe_cfg["time_range"]

    base = {"query": query, "search_depth": "advanced", "max_results": 10, "include_raw_content": False, **time_params}
    
    results = []
    if domains:
        try: results = _call({**base, "include_domains": domains})
        except Exception as e: print(f"Tavily Domain Error: {e}")
        
    # Fallback large si la recherche par domaine est trop restrictive ou vide
    if not results:
        try: results = _call(base)
        except Exception as e: print(f"Tavily Fallback Error: {e}")

    return [{"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")[:800]} for r in results]

# ── Main Run Function ──────────────────────────────────────────────────────────
def run_live_watch(
    gemini_key: str,
    tavily_key: str,
    categories: list,
    markets: list,
    timeframe_label: str = "📅 Last 12 months"
) -> tuple:
    timeframe_cfg = TIMEFRAMES.get(timeframe_label, {"time_range": "year"})
    
    main_category = categories[0] if categories else ""
    ontology_context = get_ontology_context(main_category)
    
    # On utilise les mots-clés du CSV pour la recherche web
    search_query = ontology_context["keywords"] + " regulation compliance update"
    system_prompt = get_system_prompt(ontology_context["definition"], ontology_context["strict_attributes"])

    all_raw_results = []
    total_usage = {"input_tokens": 0, "output_tokens": 0}

    for market in markets:
        market_lang = get_market_language(market)
        sources = get_market_sources([market])
        
        web_domains = []
        for src in sources:
            if "API" in src["type"].upper():
                # Router: Envoyer vers la fonction d'API directe
                api_results = route_api_request(src)
                all_raw_results.extend(api_results)
            else:
                # Stocker le domaine pour la recherche web (Tavily)
                web_domains.append(src["domain"])
                
        target_query = translate_topic(gemini_key, search_query, market_lang) if market_lang != "en" else search_query
        
        # Lancement de la recherche Web avec les mots-clés optimisés
        market_results = search_tavily(tavily_key, target_query, web_domains, timeframe_cfg)
        all_raw_results.extend(market_results)
        
    unique_urls = set()
    filtered_results = [r for r in all_raw_results if r['url'] not in unique_urls and not unique_urls.add(r['url'])]

    # Note: Jina.ai temporairement retiré pour gagner en rapidité et stabilité. 
    # Crawl4AI prendra cette place plus tard si nécessaire.

    extracted_entries, usage = extract_regulatory_entries(gemini_key, search_query, filtered_results, markets, system_prompt)
    
    total_usage["input_tokens"] += usage["input_tokens"]
    total_usage["output_tokens"] += usage["output_tokens"]

    # Deduplication
    seen_titles = []
    unique_entries = []
    for entry in extracted_entries:
        title = entry.get("title", "").lower().strip()
        is_dup = any(len(set(title.split()) & set(seen.split())) / max(len(set(title.split())), 1) > 0.7 for seen in seen_titles)
        if not is_dup:
            seen_titles.append(title)
            unique_entries.append(entry)

    return unique_entries, total_usage
