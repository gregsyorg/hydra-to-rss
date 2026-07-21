import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

JSON_URLS = [
    "https://hydralinks.cloud/sources/onlinefix.json",
    "https://hydralinks.cloud/sources/fitgirl.json",
    "https://hydralinks.cloud/sources/dodi.json",
    "https://hydralinks.cloud/sources/xatab.json"
]

def fetch_json(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # Intento 1: Acceso directo
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code in (403, 503):
            # Cloudflare bloquea IPs de GitHub Actions. 
            # Usamos proxies públicos como alternativa para obtener los datos en crudo.
            proxies = [
                f"https://api.allorigins.win/raw?url={urllib.parse.quote(url)}",
                f"https://api.codetabs.com/v1/proxy?quest={urllib.parse.quote(url)}"
            ]
            
            for proxy_url in proxies:
                try:
                    req_proxy = urllib.request.Request(proxy_url, headers=headers)
                    with urllib.request.urlopen(req_proxy, timeout=15) as response:
                        return json.loads(response.read().decode('utf-8'))
                except Exception:
                    continue
            
            print(f"[aviso] no se pudo leer {url}: HTTP Error {e.code} (incluso con proxies)")
            return None
        else:
            print(f"[aviso] no se pudo leer {url}: HTTP Error {e.code}")
            return None
    except Exception as e:
        print(f"[aviso] no se pudo leer {url}: {e}")
        return None

def build_rss(items):
    rss = ET.Element('rss', {'version': '2.0'})
    channel = ET.SubElement(rss, 'channel')
    
    ET.SubElement(channel, 'title').text = 'Hydra Links RSS'
    ET.SubElement(channel, 'link').text = 'https://github.com/gregsyorg/hydra-to-rss'
    ET.SubElement(channel, 'description').text = 'Feed RSS de juegos de Hydra Links'
    
    for item in items:
        item_el = ET.SubElement(channel, 'item')
        ET.SubElement(item_el, 'title').text = item.get('title', 'Sin título')
        
        uris = item.get('uris', [])
        link = uris[0] if uris else 'https://hydralinks.cloud/'
        ET.SubElement(item_el, 'link').text = link
        ET.SubElement(item_el, 'guid').text = link
        
        desc = f"Fuente: {item.get('source_name', 'Desconocido')}"
        if 'fileSize' in item:
            desc += f" | Tamaño: {item['fileSize']}"
        ET.SubElement(item_el, 'description').text = desc
        
        pub_date = item.get('uploadDate')
        if pub_date:
            try:
                # Intenta convertir la fecha ISO al formato estándar de RSS (RFC 822)
                dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                pub_date_rfc = dt.strftime("%a, %d %b %Y %H:%M:%S %z")
                ET.SubElement(item_el, 'pubDate').text = pub_date_rfc
            except Exception:
                ET.SubElement(item_el, 'pubDate').text = pub_date

    xml_str = ET.tostring(rss, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="  ")

def main():
    all_downloads = []
    
    for url in JSON_URLS:
        data = fetch_json(url)
        if data and 'downloads' in data:
            source_name = data.get('name', url.split('/')[-1].replace('.json', ''))
            for d in data['downloads']:
                d['source_name'] = source_name
                all_downloads.append(d)
                
    # Ordenamiento léxico de las fechas ISO 8601 para mantener siempre lo más reciente arriba
    all_downloads.sort(key=lambda x: x.get('uploadDate', ''), reverse=True)
    all_downloads = all_downloads[:300]  # Limita a las 300 últimas entradas para no saturar el feed
    
    xml_content = build_rss(all_downloads)
    
    with open('feed.xml', 'w', encoding='utf-8') as f:
        f.write(xml_content)
        
    print(f"Escrito feed.xml con {len(all_downloads)} entradas.")

if __name__ == '__main__':
    main()
