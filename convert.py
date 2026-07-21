import json
import urllib.request
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# Lista con todas las fuentes JSON de Hydra que quieras incluir
JSON_URLS = [
    "https://hydralinks.cloud/sources/onlinefix.json",
    "https://hydralinks.cloud/sources/fitgirl.json",
    "https://hydralinks.cloud/sources/dodi.json",
    "https://hydralinks.cloud/sources/xatab.json"
    # Añade aquí todas las URLs que quieras entre comillas y separadas por comas
]

def main():
    rss = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    
    SubElement(channel, 'title').text = "Hydra Multi-Source Feed"
    SubElement(channel, 'link').text = "https://github.com"
    SubElement(channel, 'description').text = "Feed RSS unificado para TorBox"

    total_items = 0

    for url in JSON_URLS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())

            source_name = data.get('name', 'Fuente')

            for item in data.get('downloads', []):
                uris = item.get('uris', [])
                if not uris:
                    continue
                
                rss_item = SubElement(channel, 'item')
                # Añadimos el nombre de la fuente al título para identificarlo fácil
                item_title = f"[{source_name}] {item.get('title', 'Sin titulo')}"
                
                SubElement(rss_item, 'title').text = item_title
                SubElement(rss_item, 'enclosure', url=uris[0], type='application/x-bittorrent')
                
                if 'uploadDate' in item:
                    SubElement(rss_item, 'pubDate').text = str(item['uploadDate'])
                
                total_items += 1

        except Exception as e:
            print(f"Error procesando la fuente {url}: {e}")

    # Guardar el XML resultante
    xml_str = minidom.parseString(tostring(rss)).toprettyxml(indent="  ")
    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)
        
    print(f"XML generado con éxito. Total de elementos: {total_items}")

if __name__ == "__main__":
    main()
