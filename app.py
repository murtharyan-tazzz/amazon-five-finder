import os
import re
import requests
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, static_folder="static")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()
SERPAPI_URL = "https://serpapi.com/search.json"

def money_value(item):
    value = item.get("extracted_price")
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(item.get("price", ""))
    match = re.search(r"[\d,]+(?:\.\d{1,2})?", raw)
    return float(match.group(0).replace(",", "")) if match else None

def relevance_score(item, query):
    # Transparent heuristic, not an objective product-quality measurement.
    title = (item.get("title") or "").lower()
    words = [w.lower() for w in re.findall(r"[a-zA-Z0-9]+", query) if len(w) > 2]
    matched = sum(1 for w in words if w in title)
    relevance = matched / max(1, len(words))
    rating = item.get("rating")
    count = item.get("reviews") or 0
    try:
        rating = float(rating)
        count = int(count)
    except (TypeError, ValueError):
        rating, count = 0, 0
    # Bayesian-style shrinkage reduces the influence of tiny review samples.
    adjusted_rating = ((count * rating) + (50 * 4.0)) / (count + 50) if rating else 0
    review_confidence = min(1.0, count / 500)
    return (relevance * 45) + (adjusted_rating / 5 * 40) + (review_confidence * 15)

def serpapi(params):
    response = requests.get(SERPAPI_URL, params={**params, "api_key": SERPAPI_KEY}, timeout=45)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data

@app.get("/")
def home():
    return send_from_directory("static", "index.html")

@app.get("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")

@app.get("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js")

@app.get("/api/status")
def status():
    return jsonify({"configured": bool(SERPAPI_KEY)})

@app.post("/api/search")
def search():
    if not SERPAPI_KEY:
        return jsonify({
            "error": "The app needs a SerpApi key. Add SERPAPI_KEY in the hosting provider's environment variables."
        }), 503

    body = request.get_json(silent=True) or {}
    query = str(body.get("query", "")).strip()
    if not query:
        return jsonify({"error": "Enter a product search phrase."}), 400
    if len(query) > 180:
        return jsonify({"error": "Search phrase is too long."}), 400

    max_price = body.get("max_price")
    try:
        max_price = float(max_price) if max_price not in (None, "") else None
    except (TypeError, ValueError):
        return jsonify({"error": "Maximum price must be a number."}), 400

    include_details = bool(body.get("include_details", True))

    try:
        data = serpapi({
            "engine": "amazon",
            "amazon_domain": "amazon.com",
            "k": query,
            "device": "desktop"
        })
        candidates = data.get("organic_results", [])
        cleaned = []
        seen = set()

        for item in candidates:
            asin = item.get("asin")
            title = item.get("title")
            link = item.get("link_clean") or item.get("link")
            if not asin or not title or asin in seen:
                continue
            seen.add(asin)
            price = money_value(item)
            if max_price is not None and (price is None or price > max_price):
                continue
            cleaned.append({
                "asin": asin,
                "title": title,
                "link": link or f"https://www.amazon.com/dp/{asin}/",
                "price": item.get("price"),
                "numeric_price": price,
                "rating": item.get("rating"),
                "review_count": item.get("reviews"),
                "image": item.get("thumbnail"),
                "sponsored": bool(item.get("sponsored")),
                "bought_last_month": item.get("bought_last_month"),
                "score": round(relevance_score(item, query), 1),
                "score_note": "Heuristic based on title relevance, rating, and review-count confidence; not an independent lab test."
            })

        cleaned.sort(key=lambda x: (x["score"], x["review_count"] or 0), reverse=True)
        top = cleaned[:5]

        if include_details:
            for product in top:
                try:
                    detail = serpapi({
                        "engine": "amazon_product",
                        "amazon_domain": "amazon.com",
                        "asin": product["asin"]
                    }).get("product_results", {})
                    product["description"] = detail.get("description") or ""
                    product["brand"] = detail.get("brand") or ""
                    product["features"] = detail.get("feature_bullets") or []
                    product["specifications"] = detail.get("product_details") or {}
                    product["detail_rating"] = detail.get("rating")
                    product["detail_review_count"] = detail.get("reviews")
                    product["detail_price"] = detail.get("price")
                    # Keep review excerpts only when returned by the provider.
                    product["review_highlights"] = detail.get("reviews") if isinstance(detail.get("reviews"), list) else []
                except Exception as detail_error:
                    product["detail_error"] = str(detail_error)[:240]

        return jsonify({
            "query": query,
            "count_returned": len(top),
            "candidate_count": len(cleaned),
            "ranking_note": "Sponsored status is shown, but sponsored listings are not automatically ranked higher. Scores are screening aids, not verified quality judgments.",
            "products": top
        })

    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        return jsonify({"error": f"Product search provider returned HTTP {status_code}. Check your API account/limits and try again."}), 502
    except Exception as exc:
        return jsonify({"error": f"Search failed: {str(exc)[:400]}"}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
