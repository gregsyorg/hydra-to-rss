#!/usr/bin/env python3
"""
Genera un feed RSS 2.0 (feed.xml) a partir de fuentes JSON de HydraLinks
utilizando los endpoints oficiales de la API.
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from xml.sax.saxutils import escape

OUTPUT_FILE = "feed.xml"

# Endpoints oficiales de las fuentes en la API de Hydra
JSON_URLS = [
    "https://hydralinks.cloud/sources/onlinefix.json",
    "https://hydralinks.cloud/sources/fitgirl.json",
    "https://hydralinks.cloud/sources/dodi.json",
    "https://hydralinks.cloud/sources/xatab.json",
]


def fetch_json(url):
    # Usamos cloudscraper si está disponible, o urllib estándar con headers de navegador
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except ImportError:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))


def to_rfc822(value):
    if value is None:
        return format_datetime(datetime.now(timezone.utc))
    if isinstance(value, (int, float)):
        return format_datetime(datetime.fromtimestamp(value, timezone.utc))
    s = str(value).strip()
    try:
        return format_datetime(parsedate_to_datetime(s))
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return format_datetime(dt)
    except Exception:
        return format_datetime(datetime.now(timezone.utc))


def extract_magnet(raw_item):
    candidates = (
        raw_item.get("uris")
        or raw_item.get("magnets")
        or raw_item.get("downloads")
        or [raw_item.get("magnet")]
        or [raw_item.get("link")]
        or [raw_item.get("url")]
    )

    if isinstance(candidates, str):
        candidates = [candidates]

    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.startswith("magnet:"):
                return candidate
            elif isinstance(candidate, dict):
                link = candidate.get("url") or candidate.get("link") or candidate.get("uri")
                if link and str(link).startswith("magnet:"):
                    return str(link)
    return None


def build_item(raw):
    magnet = extract_magnet(raw)
    if not magnet:
        return None

    title = raw.get("title") or raw.get("name") or "Sin título"
    description = raw.get("description") or raw.get("fileSize") or ""
    guid = raw.get("guid") or raw.get("id") or magnet
    date_val = raw.get("uploadDate") or raw.get("createdAt") or raw.get("date")
    date = to_rfc822(date_val)

    return {
        "title": str(title),
        "link": str(magnet),
        "description": str(description),
        "guid": str(guid),
        "pubDate": date,
    }


def collect_items(urls):
    items = []
    for url in urls:
        try:
            data = fetch_json(url)
        except Exception as e:
            print(f"[aviso] no se pudo leer {url}: {e}", file=sys.stderr)
            continue

        raw_items = []
        if isinstance(data, list):
            raw_items = data
        elif isinstance(data, dict):
            raw_items = data.get("downloads") or data.get("items") or data.get("results") or []

        for raw in raw_items:
            if isinstance(raw, dict):
                item = build_item(raw)
                if item:
                    items.append(item)

    return items


def render_feed(items):
    now = format_datetime(datetime.now(timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "  <channel>",
        "    <title>HydraLinks Magnet RSS Feed</title>",
        "    <link>https://hydralinks.cloud/</link>",
        "    <description>Feed generado automáticamente con enlaces Magnet</description>",
        f"    <lastBuildDate>{now}</lastBuildDate>",
    ]
    for it in items:
        parts += [
            "    <item>",
            f"      <title>{escape(it['title'])}</title>",
            f"      <link>{escape(it['link'])}</link>",
            f"      <description>{escape(it['description'])}</description>",
            f'      <guid isPermaLink="false">{escape(it["guid"])}</guid>',
            f"      <pubDate>{it['pubDate']}</pubDate>",
            "    </item>",
        ]
    parts += ["  </channel>", "</rss>", ""]
    return "\n".join(parts)


def main():
    items = collect_items(JSON_URLS)
    
    if not items:
        print("[aviso] No se encontraron items.")
    
    xml = render_feed(items)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"Escrito {OUTPUT_FILE} con {len(items)} entradas.")


if __name__ == "__main__":
    main()
