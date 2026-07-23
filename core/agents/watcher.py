import json
import urllib.request
import urllib.error
from datetime import datetime
import os
import pandas as pd
import time

# ── Configuration ──────────────────────────────────────────────────────────────
TIMEFRAMES = {
    "⚡ Last 7 days":    {"time_range": "week"},
    "⚡ Last 30 days":   {"time_range": "month"},
    "📅 Last 12 months": {"time_range": "year"},
}

# AJOUT : Configuration des timeouts et retry
GEMINI_TIMEOUT = 120  # 2 minutes au lieu de 40s
MAX_RETRIES = 3
RETRY_DELAY = 2

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

# ── Gemini API Calls (VERSION CORRIGÉE) ────────────────────────────────────────
def call_gemini(gemini_key: str, system_prompt: str, user_prompt: str, force_json: bool = False) -> dict:
    """
    Appel Gemini avec retry automatique, timeout étendu et gestion des blocages.
    """
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8000  # AJOUT : Limite explicite
        },
        # AJOUT : Configuration de sécurité plus permissive
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
        ]
    }
    
    if force_json:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}, 
                method="POST"
            )
            
            # MODIFICATION : Timeout augmenté
            with urllib.request.urlopen(req, timeout=GEMINI_TIMEOUT) as resp:
                data = json.loads(resp.read())
            
            # AJOUT : Vérification de blocage par les filtres de sécurité
            if "candidates" not in data or not data["candidates"]:
                if "promptFeedback" in data and data["promptFeedback"].get("blockReason"):
                    raise Exception(f"Gemini a bloqué la requête : {data['promptFeedback']['blockReason']}")
                raise Exception("Gemini n'a retourné aucun candidat (réponse vide)")
            
            candidate = data["candidates"][0]
            
            # AJOUT : Vérification du finish_reason
            finish_reason = candidate.get("finishReason", "")
            if finish_reason == "SAFETY":
                raise Exception("Réponse bloquée par les filtres de sécurité Gemini")
            elif finish_reason == "MAX_TOKENS":
                print("⚠️ Warning: Réponse tronquée (limite de tokens atteinte)")
            
            # AJOUT : Vérification que la réponse contient du texte
            if "content" not in candidate or "parts" not in candidate["content"]:
                raise Exception("Structure de réponse Gemini invalide")
            
            parts = candidate["content"]["parts"]
            if not parts or "text" not in parts[0]:
                raise Exception("Gemini n'a retourné aucun texte")
            
            text_response = parts[0]["text"]
            usage = data.get("usageMetadata", {})
            
            return {
                "text": text_response,
                "input_tokens": usage.get("promptTokenCount", 0),
                "output_tokens": usage.get("candidatesTokenCount", 0)
            }
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            error_msg = f"Gemini API refusée (Code {e.code}): {error_body}"
            
            # Gestion spécifique des erreurs 429 (rate limit) et 503 (overload)
            if e.code in [429, 503] and attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"⏳ Retry {attempt + 1}/{MAX_RETRIES} après {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            raise Exception(error_msg)
            
        except urllib.error.URLError as e:
            if "timeout" in str(e).lower() and attempt < MAX_RETRIES - 1:
                print(f"⏳ Timeout détecté, retry {attempt + 1}/{MAX_RETRIES}...")
                time.sleep(RETRY_DELAY)
                continue
            raise Exception(f"Timeout Gemini après {GEMINI_TIMEOUT}s: {e}")
            
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"⚠️ Erreur Gemini (tentative {attempt + 1}/{MAX_RETRIES}): {e}")
                time.sleep(RETRY_DELAY)
                continue
            raise Exception(f"Erreur finale Gemini: {e}")
    
    raise Exception(f"Échec après {MAX_RETRIES} tentatives")


def generate_smart_query(gemini_key: str, business_definition: str, fallback_category: str) -> str:
    if not business_definition: 
        return fallback_category
    
    system_prompt = "You are an expert in regulatory intelligence and SEO."
    user_prompt = f"Read this product definition:\n{business_definition}\n\nGenerate a single search engine query (max 6 words) to find recent regulatory updates or laws for this product. Return ONLY the search query string, nothing else."
    
    try:
        result = call_gemini(gemini_key, system_prompt, user_prompt)
        query = result["text"].strip()
        # AJOUT : Validation basique
        if not query or len(query) > 100:
            return fallback_category
        return query
    except Exception as e:
        print(f"⚠️ Erreur génération query, fallback: {e}")
        return fallback_category


def translate_topic(gemini_key: str, topic: str, target_lang: str) -> str:
    if target_lang == "en": 
        return topic
    
    system = "Translate the given search query into the target language. Return ONLY the translated string."
    user = f"Translate into ISO code '{target_lang}':\n\n{topic}"
    
    try:
        result = call_gemini(gemini_key, system, user)
        translated = result["text"].strip()
        return translated if translated else topic
    except Exception as e:
        print(f"⚠️ Erreur traduction, utilisation de l'original: {e}")
        return topic


def extract_regulatory_entries(gemini_key: str, topic_en: str, search_results: list, 
                               markets: list, business_definition: str, 
                               strict_attributes: str) -> tuple:
    """
    VERSION CORRIGÉE : Limitation du payload et meilleure gestion d'erreur
    """
    
    # AJOUT : Limitation du nombre de résultats pour éviter payload trop gros
    MAX_RESULTS = 15
    if len(search_results) > MAX_RESULTS:
        print(f"⚠️ Limitation à {MAX_RESULTS} résultats (sur {len(search_results)})")
        search_results = search_results[:MAX_RESULTS]
    
    system_prompt = f"""You are Agent 1, a regulatory intelligence extractor. Always output in English.

--- PRODUCT CONTEXT ---
DEFINITION: {business_definition[:500] if business_definition else 'N/A'}
ATTRIBUTES: {strict_attributes[:300] if strict_attributes else 'N/A'}
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

STRICT RULES:
- Only include genuine regulatory content (laws, standards, official regulations).
- If nothing relevant is found, return an empty array: []
- Maximum 10 entries in the output.
- Each summary must be concise (max 3 sentences)."""

    # MODIFICATION : Limitation de la longueur du contenu par résultat
    results_text = "\n\n".join([
        f"Title: {r['title'][:200]}\nURL: {r['url']}\nContent: {r['content'][:600]}" 
        for r in search_results
    ])
    
    user_message = f"""Keywords: {topic_en}
Markets: {', '.join(markets)}

Search results to analyze:
{results_text}"""

    try:
        result = call_gemini(gemini_key, system_prompt, user_message, force_json=True)
        
        raw_text = result["text"].strip()
        
        # Nettoyage des markdown
        if raw_text.startswith("```json"): 
            raw_text = raw_text[7:]
        if raw_text.startswith("```"): 
            raw_text = raw_text[3:]
        if raw_text.endswith("```"): 
            raw_text = raw_text[:-3]
        
        raw_text = raw_text.strip()
        
        # AJOUT : Validation JSON plus robuste
        if not raw_text:
            print("⚠️ Gemini a retourné une chaîne vide")
            return [], {"input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"]}
        
        try:
            entries = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON invalide de Gemini: {e}")
            print(f"Réponse reçue: {raw_text[:500]}")
            return [], {"input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"]}
        
        if not isinstance(entries, list):
            print(f"⚠️ Gemini n'a pas retourné une liste: {type(entries)}")
            entries = []
            
        return entries, {
            "input_tokens": result["input_tokens"], 
            "output_tokens": result["output_tokens"]
        }
        
    except Exception as e:
        print(f"❌ Erreur extraction réglementaire: {e}")
        return [], {"input_tokens": 0, "output_tokens": 0}


# ── Routing: Web Search (Tavily) ───────────────────────────────────────────────
def search_tavily(tavily_key: str, query: str, domains: list, timeframe_cfg: dict = None) -> list:
    def _call(payload_dict: dict) -> list:
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=json.dumps(payload_dict).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {tavily_key}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()).get("results", [])

    time_params = {"time_range": timeframe_cfg["time_range"]} if timeframe_cfg and "time_range" in timeframe_cfg else {}
    base = {
        "query": query, 
        "search_depth": "advanced", 
        "max_results": 10, 
        "include_raw_content": False, 
        **time_params
    }
    
    results = []
    
    # 1. Tentative avec domaines stricts
    if domains:
        try: 
            results = _call({**base, "include_domains": domains})
        except Exception as e:
            print(f"⚠️ Recherche sur domaines spécifiques échouée: {e}")
            
    # 2. Fallback sur recherche globale
    if not results:
        try: 
            results = _call(base)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Tavily API refusée (Code {e.code}): {error_body}")
        except Exception as e:
            raise Exception(f"Erreur Tavily: {e}")

    return [
        {
            "title": r.get("title", "No title"), 
            "url": r.get("url", ""), 
            "content": r.get("content", "")[:1000]  # MODIFICATION : Limite augmentée
        } 
        for r in results
    ]


# ── Main Run Function ──────────────────────────────────────────────────────────
def run_live_watch(gemini_key: str, tavily_key: str, categories: list, markets: list, 
                   timeframe_label: str = "📅 Last 12 months") -> tuple:
    """
    VERSION CORRIGÉE avec meilleure gestion d'erreur et diagnostics
    """
    
    timeframe_cfg = TIMEFRAMES.get(timeframe_label, {"time_range": "year"})
    main_category = categories[0] if categories else "regulatory compliance"
    
    print(f"🔍 Analyse pour: {main_category} | Marchés: {markets}")
    
    ontology_context = get_ontology_context(main_category)
    
    # Génération de la requête
    if ontology_context["keywords"] != main_category:
        base_query = ontology_context["keywords"]
    else:
        base_query = generate_smart_query(gemini_key, ontology_context["definition"], main_category)
    
    search_query = base_query + " regulatory compliance law update"
    print(f"📝 Requête générée: {search_query}")
    
    all_raw_results = []
    total_usage = {"input_tokens": 0, "output_tokens": 0}

    # Recherche par marché
    for market in markets:
        print(f"\n🌍 Recherche pour {market}...")
        market_lang = get_market_language(market)
        sources = get_market_sources([market])
        web_domains = [src["domain"] for src in sources]
        
        target_query = translate_topic(gemini_key, search_query, market_lang)
        
        try:
            market_results = search_tavily(tavily_key, target_query, web_domains, timeframe_cfg)
            print(f"   ✅ {len(market_results)} résultats trouvés")
            all_raw_results.extend(market_results)
        except Exception as e:
            print(f"   ❌ Erreur recherche {market}: {e}")
            continue
        
    # Vérification des résultats
    if not all_raw_results:
        print(f"⚠️ Aucun résultat Tavily pour '{search_query}'")
        return [], total_usage

    # Déduplication
    unique_urls = set()
    filtered_results = [
        r for r in all_raw_results 
        if r['url'] not in unique_urls and not unique_urls.add(r['url'])
    ]
    
    print(f"\n📊 {len(filtered_results)} résultats uniques à analyser par Gemini...")

    # Extraction réglementaire
    extracted_entries, usage = extract_regulatory_entries(
        gemini_key, search_query, filtered_results, markets, 
        ontology_context["definition"], ontology_context["strict_attributes"]
    )
    
    total_usage["input_tokens"] += usage["input_tokens"]
    total_usage["output_tokens"] += usage["output_tokens"]
    
    print(f"✅ {len(extracted_entries)} entrées extraites")

    # Déduplication des titres similaires
    seen_titles = []
    unique_entries = []
    for entry in extracted_entries:
        title = entry.get("title", "").lower().strip()
        is_dup = any(
            len(set(title.split()) & set(seen.split())) / max(len(set(title.split())), 1) > 0.7 
            for seen in seen_titles
        )
        if not is_dup:
            seen_titles.append(title)
            unique_entries.append(entry)

    print(f"🎯 {len(unique_entries)} entrées finales après déduplication\n")
    print(f"💰 Usage tokens: {total_usage['input_tokens']} in / {total_usage['output_tokens']} out")
    
    return unique_entries, total_usage
