# Amazon Five Finder — Android-friendly web app

This project creates a small installable web app. Open it in Chrome on Android and use **Add to Home screen** to get an app-like icon.

## Important: search provider and API key

This version uses the SerpApi Amazon search endpoint. SerpApi is a third-party search-data provider, not Amazon. You need a SerpApi account and API key; check its current plan, credit usage, and terms before using it. A normal search uses one API search. Enabling extra product details can make up to five additional product-page API requests.

SerpApi docs:
- Amazon search: https://serpapi.com/amazon-search-api
- Amazon organic results: https://serpapi.com/amazon-organic-results
- Amazon product details: https://serpapi.com/amazon-product-results

Amazon's official Creators API is another route, but Amazon's current docs say access requires enrollment in Amazon Associates, at least 10 qualifying sales in the past 30 days, API registration, and credentials. It is not a no-setup public search API:
https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction

## Deploy to Render (recommended for phone use)

1. Create an account at https://render.com.
2. Create a new **Web Service** and connect/upload this project from a GitHub repository.
3. Use the included `render.yaml` settings, or set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
4. In Render's Environment settings, add:
   - Key: `SERPAPI_KEY`
   - Value: your SerpApi API key
5. Deploy. Render will give you an HTTPS web address.
6. Open that address in Chrome on your Android phone.
7. Tap Chrome's three-dot menu → **Add to Home screen** (or **Install app**, if shown).

Do not put your SerpApi key into `static/index.html`, share it publicly, or commit it to GitHub.

## Local test

1. Install Python 3.10+.
2. Run `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and replace the placeholder with your SerpApi key.
4. Run `python app.py`.
5. Open `http://127.0.0.1:5000` on the computer.

## How ranking works

The app searches Amazon results, filters by the optional maximum price, and ranks the remaining listings using a visible heuristic:
- title overlap with the search phrase,
- rating adjusted toward a 4.0 baseline when review count is small,
- review-count confidence.

This is a first-pass screening score, not an objective measure of quality. Sponsored listings are labeled but are not automatically promoted. Independent research, authenticity checks, and deep review analysis are not included in this starter build.

## Known limitations

- Amazon search results and fields vary; some prices, ratings, or review counts may be missing.
- Search results are limited to the data returned by the provider.
- Product details are best-effort and may be absent.
- The app does not bypass CAPTCHAs, logins, paywalls, or anti-bot controls.
- The app currently returns up to five products; it does not claim to have exhaustively evaluated every Amazon product.
- No API key is included. The app cannot search live Amazon results until you configure one.
