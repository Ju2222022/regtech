import json
import urllib.request
import urllib.error
from datetime import datetime
import os
import pandas as pd

# ── Configuration & Cost ───────────────────────────────────────────────────────
TIMEFRAMES = {
    "⚡ Last 7 days":    {"time_range": "week"},
    "⚡ Last 30 days":   {"time_range": "month"},
    "📅 Last 12 months": {"time_range": "year"},
}

HAIKU_INPUT_COST  = 0.80
HAIKU_OUTPUT_COST = 4.00

# ── Dynamic Data Loaders (Ontology & Pool) ─────────────────────────────────────
def get_dynamic_sources(markets: list) -> list:
    """Extracts target domains from regulatory_pool.csv based on selected markets."""
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
            # Clean URLs to extract pure domains
            clean_domains = [url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0] for url in raw_urls]
            return list(set(clean_domains))
            
    except Exception as e:
        print(f"Error reading regulatory pool sources: {e}")
        
    # Safe fallback
    return ["eur-lex.europa.eu", "legifrance.gouv.fr"]

def get_market_language(market: str) -> str:
    """Extracts target language from regulatory_pool.csv based on the market."""
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
        
    return "en" # Fallback to English

def get_category_context(category_name: str) -> str:
    """Extracts the strict business definition from default_ontology.csv to guide the AI."""
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'default_ontology.csv')
        df = pd.read_csv(csv_path)
        
        # Check sub-categories first, then categories
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
    """Generates a dynamic system prompt tailored to the product's exact definition."""
    return f"""You are Agent 1, a regulatory intelligence extractor for product compliance.

You receive web search results and must extract structured regulatory entries.
Always output in English, regardless of the source language.

IMPORTANT CONTEXT ABOUT THE PRODUCT CATEGORY:
{business_definition}

OUTPUT — respond ONLY with a valid JSON array, no markdown:
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
- Skip generic news unless they announce a specific regulatory change.
- urgency HIGH = deadline < 6 months or already in force.
- urgency MEDIUM = deadline 6-18 months.
- urgency LOW = consultation or > 18 months.
- If nothing relevant found, return [].
"""

# ── Translation ────────────────────────────────────────────────────────────────
def translate_topic(anthropic_key: str, topic: str, target_lang: str) -> str:
    """Translate a watch topic into the target language using Claude Haiku."""
    if target_lang == "en":
        return topic

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 200,
        "system": "Translate the given regulatory topic into the target language. Return ONLY the translated query string.",
        "messages": [{
            "role": "user",
            "content": f"Translate this regulatory watch topic into the language corresponding to ISO code '{target_lang}':\n\n{topic}"
        }]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return data["content"][0]["text"].strip()
    except Exception:
        return topic

# ── Tavily Search ──────────────────────────────────────────────────────────────
def search_tavily(tavily_key: str, query: str, domains: list, timeframe_cfg: dict = None) -> list:
    """Search web using Tavily Search API with domain filtering."""
    def _call(payload_dict: dict) -> list:
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=json.dumps(payload_dict).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {tavily_key}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read()).get("results", [])

    time_params = {}
    if timeframe_cfg and timeframe_cfg.get("time_range"):
        time_params["time_range"] = timeframe_cfg["time_range"]

    base = {
        "query": query,
        "search_depth": "advanced",
        "max_results": 10,
        "include_raw_content": False,
        **time_params,
    }

    try:
        results = _call({**base, "include_domains": domains}) if domains else []
    except Exception:
        results = []

    if not results:
        try:
            results = _call(base)
        except Exception:
            results = []

    return [
        {
            "title": r.get("title", ""),
            "url":   r.get("url", ""),
            "content": r.get("content", "")[:800],
        }
        for r in results
    ]

# ── Jina.ai Enrichment ─────────────────────────────────────────────────────────
def fetch_with_jina(url: str) -> str:
    jina_url = f"https://r.jina.ai/{url}"
    req = urllib.request.Request(
        jina_url,
        headers={"Accept": "text/plain", "X-Return-Format": "text"},
        method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")[:2000]
    except Exception as e:
        return f"[Jina fetch failed: {e}]"

def enrich_with_jina(results: list, max_enrich: int = 2) -> list:
    priority_domains = ["eur-lex.europa.eu", "legifrance.gouv.fr", "samr.gov.cn"]
    enriched = []
    jina_count = 0
    for r in results:
        url = r.get("url", "")
        should_enrich = (
            jina_count < max_enrich and
            (any(d in url for d in priority_domains) or url.endswith(".pdf"))
        )
        if should_enrich:
            deep = fetch_with_jina(url)
            if "[Jina fetch failed" not in deep:
                r["content"] = deep
                r["enriched_by_jina"] = True
            jina_count += 1
        enriched.append(r)
    return enriched

# ── Claude Extraction ──────────────────────────────────────────────────────────
def extract_regulatory_entries(
    anthropic_key: str,
    topic_en: str,
    search_results: list,
    markets: list,
    system_prompt: str
) -> tuple:
    if not search_results:
        return [], {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    results_text = "\n\n".join([
        f"Title: {r['title']}\nURL: {r['url']}\n"
        f"{'[Jina enriched] ' if r.get('enriched_by_jina') else ''}"
        f"Content: {r['content']}"
        for r in search_results
    ])

    user_message = (
        f"Extract regulatory entries from these search results.\n\n"
        f"Topic: {topic_en}\n"
        f"Target markets: {', '.join(markets)}\n"
        f"Search date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"Search results:\n{results_text}\n\n"
        f"Return JSON array only."
    )

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    usage = data.get("usage", {})
    inp   = usage.get("input_tokens", 0)
    out   = usage.get("output_tokens", 0)
    cost  = (inp * HAIKU_INPUT_COST + out * HAIKU_OUTPUT_COST) / 1_000_000

    raw = data["content"][0]["text"].strip()
    start = raw.find("[")
    end   = raw.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end+1]), {"input_tokens": inp, "output_tokens": out, "cost_usd": round(cost, 5)}
        except Exception:
            pass
    return [], {"input_tokens": inp, "output_tokens": out, "cost_usd": round(cost, 5)}

# ── Deduplication ──────────────────────────────────────────────────────────────
def deduplicate_entries(entries: list) -> list:
    seen_titles = []
    unique = []
    for entry in entries:
        title = entry.get("title", "").lower().strip()
        title_words = set(title.split())
        is_dup = False
        for seen in seen_titles:
            seen_words = set(seen.split())
            if not title_words or not seen_words:
                continue
            overlap = len(title_words & seen_words) / max(len(title_words), len(seen_words))
            if overlap > 0.7:
                is_dup = True
                break
        if not is_dup:
            seen_titles.append(title)
            unique.append(entry)
    return unique

# ── Main Run Function ──────────────────────────────────────────────────────────
def run_live_watch(
    anthropic_key: str,
    tavily_key: str,
    categories: list,
    markets: list,
    timeframe_label: str = "⚡ Last 30 days",
    use_jina: bool = True
) -> tuple:
    """
    Executes a real-time regulatory watch session fully driven by the ontology and regulatory pool.
    """
    timeframe_cfg = TIMEFRAMES.get(timeframe_label, {"time_range": "month"})
    base_topic = " ".join(categories) + " regulatory requirements safety updates"
    
    # 1. Fetch exact business definition to guide AI extraction
    main_category = categories[0] if categories else ""
    business_context = get_category_context(main_category)
    system_prompt = get_system_prompt(business_context)

    all_raw_results = []
    total_usage = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    # 2. Iterate dynamically over requested markets
    for market in markets:
        # Fetch specific language and domains for this market
        market_lang = get_market_language(market)
        market_domains = get_dynamic_sources([market])
        
        # Translate topic to target language if not English
        target_topic = translate_topic(anthropic_key, base_topic, market_lang) if market_lang != "en" else base_topic
        
        # Tavily Search
        market_results = search_tavily(tavily_key, target_topic, market_domains, timeframe_cfg)
        all_raw_results.extend(market_results)
        
    # Deduplicate raw search URLs to avoid redundant Jina calls
    unique_urls = set()
    filtered_results = []
    for r in all_raw_results:
        if r['url'] not in unique_urls:
            unique_urls.add(r['url'])
            filtered_results.append(r)

    # 3. Optional Jina Enrichment
    if use_jina and filtered_results:
        filtered_results = enrich_with_jina(filtered_results, max_enrich=3)

    # 4. Claude Extraction
    extracted_entries, usage = extract_regulatory_entries(
        anthropic_key, base_topic, filtered_results, markets, system_prompt
    )
    
    total_usage["input_tokens"] += usage["input_tokens"]
    total_usage["output_tokens"] += usage["output_tokens"]
    total_usage["cost_usd"] += usage["cost_usd"]

    # 5. Final Deduplication
    unique_entries = deduplicate_entries(extracted_entries)

    return unique_entries, total_usage
