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
def get_dynamic_sources(markets: list) -> list:
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'regulatory_pool.csv')
        df = pd.read_csv(csv_path)
        if 'Geographic Zone' in df.columns:
            df = df[df['Geographic Zone'].isin(markets)]
            
        domain_col = None
        for col in ['URL / Endpoint', 'Domain', 'Source', 'URL', 'Website', 'Lien']:
            if col in df.columns:
                domain_col = col
                break
                
        if domain_col:
            raw_urls = df[domain_col].dropna().unique().tolist()
            clean_domains = [url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0] for url in raw_urls]
            return list(set(clean_domains))
    except Exception as e:
        print(f"Error reading regulatory pool sources: {e}")
    return ["eur-lex.europa.eu", "legifrance.gouv.fr"]

def get_market_language(market: str) -> str:
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

def get_category_context(category_name: str) -> str:
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'default_ontology.csv')
        df = pd.read_csv(csv_path)
        match = df[df['sub_category_label'] == category_name]
        if match.empty:
            match = df[df['category_label'] == category_name]
        if not match.empty and 'business_definition' in df.columns:
            definition = match['business_definition'].iloc[0]
            if pd.notna(definition):
                return str(definition)
    except Exception as e:
        print(f"Error reading ontology context: {e}")
    return "No specific business definition provided. Focus on general product compliance and safety."

def get_system_prompt(business_definition: str) -> str:
    return f"""You are Agent 1, a regulatory intelligence extractor for product compliance.

You receive web search results and must extract structured regulatory entries.
Always output in English, regardless of the source language.

IMPORTANT CONTEXT ABOUT THE PRODUCT CATEGORY:
{business_definition}

OUTPUT SCHEMA REQUIRED (JSON Array):
[
  {{
    "title": "Short title in English",
    "source": "source domain",
    "date": "YYYY-MM-DD or estimated",
    "summary": "AI summary in English (2-3 sentences max)",
    "impact_prediction": "Description of potential gap / impact on products based on the context provided",
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
- urgency HIGH = deadline < 6 months or already in force.
- urgency MEDIUM = deadline 6-18 months.
- urgency LOW = consultation or > 18 months.
- If nothing relevant found, return an empty array [].
"""

# ── Gemini API Calls ───────────────────────────────────────────────────────────
def call_gemini(gemini_key: str, system_prompt: str, user_prompt: str, force_json: bool = False) -> dict:
    """Wrapper to call Gemini API via HTTP requests."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.2
        }
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
        with urllib.request.urlopen(req, timeout=30) as resp:
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

    system = "Translate the given regulatory topic into the target language. Return ONLY the translated query string."
    user = f"Translate this regulatory watch topic into the language corresponding to ISO code '{target_lang}':\n\n{topic}"
    
    result = call_gemini(gemini_key, system, user)
    translated = result["text"].strip()
    return translated if translated else topic

def extract_regulatory_entries(gemini_key: str, topic_en: str, search_results: list, markets: list, system_prompt: str) -> tuple:
    if not search_results:
        return [], {"input_tokens": 0, "output_tokens": 0}

    results_text = "\n\n".join([
        f"Title: {r['title']}\nURL: {r['url']}\n"
        f"{'[Jina enriched] ' if r.get('enriched_by_jina') else ''}"
        f"Content: {r['content']}"
        for r in search_results
    ])

    user_message = (
        f"Extract regulatory entries from these search results.\n\n"
        f"Topic: {topic_en}\nTarget markets: {', '.join(markets)}\n"
        f"Search date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"Search results:\n{results_text}"
    )

    result = call_gemini(gemini_key, system_prompt, user_message, force_json=True)
    
    try:
        entries = json.loads(result["text"])
        if not isinstance(entries, list):
            entries = []
    except json.JSONDecodeError:
        entries = []
        
    return entries, {"input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"]}

# ── Tavily Search & Jina ───────────────────────────────────────────────────────
def search_tavily(tavily_key: str, query: str, domains: list, timeframe_cfg: dict = None) -> list:
    def _call(payload_dict: dict) -> list:
        req = urllib.request.Request(
            "https://api.tavily.com/search",
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
        except: pass
    if not results:
        try: results = _call(base)
        except: pass

    return [{"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")[:800]} for r in results]

def enrich_with_jina(results: list, max_enrich: int = 2) -> list:
    priority_domains = ["eur-lex.europa.eu", "legifrance.gouv.fr", "samr.gov.cn"]
    enriched = []
    jina_count = 0
    for r in results:
        url = r.get("url", "")
        should_enrich = (jina_count < max_enrich and (any(d in url for d in priority_domains) or url.endswith(".pdf")))
        if should_enrich:
            try:
                req = urllib.request.Request(f"https://r.jina.ai/{url}", headers={"Accept": "text/plain", "X-Return-Format": "text"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    r["content"] = resp.read().decode("utf-8", errors="ignore")[:2000]
                    r["enriched_by_jina"] = True
            except:
                pass
            jina_count += 1
        enriched.append(r)
    return enriched

# ── Deduplication ──────────────────────────────────────────────────────────────
def deduplicate_entries(entries: list) -> list:
    seen_titles = []
    unique = []
    for entry in entries:
        title = entry.get("title", "").lower().strip()
        title_words = set(title.split())
        is_dup = any(len(title_words & set(seen.split())) / max(len(title_words), len(set(seen.split()))) > 0.7 for seen in seen_titles if title_words)
        if not is_dup:
            seen_titles.append(title)
            unique.append(entry)
    return unique

# ── Main Run Function ──────────────────────────────────────────────────────────
def run_live_watch(
    gemini_key: str,
    tavily_key: str,
    categories: list,
    markets: list,
    timeframe_label: str = "⚡ Last 30 days",
    use_jina: bool = True
) -> tuple:
    timeframe_cfg = TIMEFRAMES.get(timeframe_label, {"time_range": "month"})
    base_topic = " ".join(categories) + " regulatory requirements safety updates"
    
    main_category = categories[0] if categories else ""
    business_context = get_category_context(main_category)
    system_prompt = get_system_prompt(business_context)

    all_raw_results = []
    total_usage = {"input_tokens": 0, "output_tokens": 0}

    for market in markets:
        market_lang = get_market_language(market)
        market_domains = get_dynamic_sources([market])
        target_topic = translate_topic(gemini_key, base_topic, market_lang) if market_lang != "en" else base_topic
        market_results = search_tavily(tavily_key, target_topic, market_domains, timeframe_cfg)
        all_raw_results.extend(market_results)
        
    unique_urls = set()
    filtered_results = [r for r in all_raw_results if r['url'] not in unique_urls and not unique_urls.add(r['url'])]

    if use_jina and filtered_results:
        filtered_results = enrich_with_jina(filtered_results, max_enrich=3)

    extracted_entries, usage = extract_regulatory_entries(gemini_key, base_topic, filtered_results, markets, system_prompt)
    
    total_usage["input_tokens"] += usage["input_tokens"]
    total_usage["output_tokens"] += usage["output_tokens"]

    return deduplicate_entries(extracted_entries), total_usage
