#!/usr/bin/env python3
"""
Genera un feed RSS 2.0 (feed.xml) a partir de una o varias fuentes JSON.
Toda la configuración vive en sources.json. Solo usa la librería estándar
de Python, así que no hace falta instalar nada en GitHub Actions.
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from urllib.parse import urlparse
from xml.sax.saxutils import escape

CONFIG_FILE = "sources.json"
OUTPUT_FILE = "feed.xml"
USER_AGENT = "json-to-rss/1.0"


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def dig(obj, path):
    """Navega un objeto con una ruta separada por puntos ('a.b.c'). '' devuelve obj."""
    if not path:
        return obj
    cur = obj
    for key in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return None
    return cur


def to_rfc822(value):
    """Convierte fecha (ISO 8601, RFC 822 o timestamp) a RFC 822. Si no puede, usa 'ahora'."""
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


def is_valid_link(url):
    """Permite enlaces web (http/https) y enlaces de tipo magnet."""
    if not url:
        return False
    try:
        scheme = urlparse(str(url)).scheme.lower()
        return scheme in ("http", "https", "magnet")
    except Exception:
        return False


def build_item(raw, mapping):
    link = dig(raw, mapping.get("link", "link"))
    # Acepta enlaces http, https y magnet
    if not is_valid_link(link):
        return None
    title = dig(raw, mapping.get("title", "title"))
    description = dig(raw, mapping.get("description", "")) or ""
    guid = dig(raw, mapping.get("guid", "")) or link
    date = to_rfc822(dig(raw, mapping.get("date", "")))
    return {
        "title": str(title or "Sin título"),
        "link": str(link),
        "description": str(description),
        "guid": str(guid),
        "pubDate": date,
    }


def collect_items(config):
    mapping = config.get("mapping", {})
    items_path = mapping.get("items_path", "")
    items = []
    for url in config.get("sources", []):
        try:
            data = fetch_json(url)
        except Exception as e:
            print(f"[aviso] no se pudo leer {url}: {e}", file=sys.stderr)
            continue
        raw_items = dig(data, items_path)
        if raw_items is None and isinstance(data, list):
            raw_items = data
        if not isinstance(raw_items, list):
            print(f"[aviso] '{items_path}' no es una lista en {url}", file=sys.stderr)
            continue
        for raw in raw_items:
            item = build_item(raw, mapping)
            if item:
                items.append(item)
    return items


def render_feed(feed_meta, items):
    now = format_datetime(datetime.now(timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "  <channel>",
        f"    <title>{escape(feed_meta.get('title', 'Feed'))}</title>",
        f"    <link>{escape(feed_meta.get('link', ''))}</link>",
        f"    <description>{escape(feed_meta.get('description', ''))}</description>",
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
    config = load_config(CONFIG_FILE)
    items = collect_items(config)
    xml = render_feed(config.get("feed", {}), items)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"Escrito {OUTPUT_FILE} con {len(items)} entradas.")


if __name__ == "__main__":
    main()
