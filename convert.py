import json
import subprocess
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# Lista de fuentes JSON
JSON_URLS = [
    "https://hydralinks.cloud/sources/onlinefix.json",
    "https://hydralinks.cloud/sources/fitgirl.json",
    "https://hydralinks.cloud/sources/dodi.json",
    "https://hydralinks.cloud/sources/xatab.json"
]

def get_json_data(url):
    # Usar curl de Linux/GitHub Actions para bypass de Cloudflare 403
    command = [
        "curl",
        "-s",
        "-L",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "-H", "Accept: application/json, text/plain, */*",
        "-H", "Accept-Language: en-US,en;q=0.9",
        "-H", "Sec-Fetch-Dest: empty",
        "-H", "Sec-Fetch-Mode: cors",
        "-H", "Sec-Fetch-Site: cross-site",
        url
    ]
    
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    if not result.stdout.strip():
        raise Exception("Respuesta vacía al descargar JSON")
        
    return json.loads(result.stdout)

def main():
    rss = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    
    SubElement(channel, 'title').text = "Hydra Multi-Source Feed"
    SubElement(channel, 'link').text = "https://github.com"
    SubElement(channel, 'description').text = "Feed RSS unificado para TorBox"

    total_items = 0

    for url in JSON_URLS:
        try:
            print(f"Descargando fuente: {url}")
            data = get_json_data(url)
            source_name = data.get('name', 'Fuente')

            downloads = data.get('downloads', []) if isinstance(data, dict) else data

            for item in downloads:
                if not isinstance(item, dict):
                    continue

                uris = item.get('uris', [])
                if not uris or not isinstance(uris, list) or len(uris) == 0:
                    continue

                magnet_url = uris[0]
                if not str(magnet_url).startswith('magnet:'):
                    continue

                rss_item = SubElement(channel, 'item')
                
                raw_title = item.get('title', 'Sin titulo')
                title_text = f"[{source_name}] {raw_title}"
                
                SubElement(rss_item, 'title').text = title_text
                SubElement(rss_item, 'enclosure', url=str(magnet_url), type='application/x-bittorrent')
                
                if 'uploadDate' in item:
                    SubElement(rss_item, 'pubDate').text = str(item['uploadDate'])

                total_items += 1

        except Exception as e:
            print(f"Error procesando {url}: {e}")

    # Guardar resultado
    xml_bytes = tostring(rss, encoding='utf-8')
    parsed_xml = minidom.parseString(xml_bytes)
    
    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(parsed_xml.toprettyxml(indent="  "))
        
    print(f"Finalizado. Total de items generados: {total_items}")

if __name__ == "__main__":
    main()
