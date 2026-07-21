import json
import urllib.request
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# Lista de fuentes JSON de Hydra
JSON_URLS = [
    "https://hydralinks.cloud/sources/onlinefix.json",
    "https://hydralinks.cloud/sources/fitgirl.json",
    "https://hydralinks.cloud/sources/dodi.json",
    "https://hydralinks.cloud/sources/xatab.json"
]

def get_json_data(url):
    """Realiza la petición HTTP simulando un navegador real para evitar bloqueos Cloudflare/403."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode('utf-8'))

def main():
    rss = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    
    SubElement(channel, 'title').text = "Hydra Multi-Source Feed"
    SubElement(channel, 'link').text = "https://github.com"
    SubElement(channel, 'description').text = "Feed RSS unificado para TorBox"

    total_items = 0

    for url in JSON_URLS:
        try:
            data = get_json_data(url)
            source_name = data.get('name', 'Hydra Source')

            # Manejar tanto la estructura 'downloads' como si viniera directamente una lista
            downloads = data.get('downloads', []) if isinstance(data, dict) else data

            for item in downloads:
                if not isinstance(item, dict):
                    continue

                # Extraer URIs o magnets directos
                uris = item.get('uris', [])
                magnet = None

                if uris and len(uris) > 0:
                    magnet = uris[0]
                elif 'magnet' in item:
                    magnet = item['magnet']
                elif 'url' in item and str(item['url']).startswith('magnet:'):
                    magnet = item['url']

                if not magnet or not str(magnet).startswith('magnet:'):
                    continue

                rss_item = SubElement(channel, 'item')
                title_text = f"[{source_name}] {item.get('title', item.get('name', 'Sin titulo'))}"
                
                SubElement(rss_item, 'title').text = title_text
                SubElement(rss_item, 'enclosure', url=str(magnet), type='application/x-bittorrent')
                
                # Intentar añadir fecha si existe
                date_val = item.get('uploadDate', item.get('fileSize', None))
                if date_val:
                    SubElement(rss_item, 'pubDate').text = str(date_val)

                total_items += 1

        except Exception as e:
            print(f"Error procesando la fuente {url}: {e}")

    # Generar y guardar el XML
    xml_str = minidom.parseString(tostring(rss)).toprettyxml(indent="  ")
    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)
        
    print(f"Proceso finalizado. Total de juegos agregados: {total_items}")

if __name__ == "__main__":
    main()
