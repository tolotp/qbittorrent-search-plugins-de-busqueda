# VERSION: 1.0
# AUTHORS: tolotp

import urllib.parse
from html.parser import HTMLParser
from helpers import retrieve_url
from novaprinter import prettyPrinter

class UindexParser(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.current_res = {}
        self.current_item = None
        self.in_row = False
        self.td_counter = -1

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)

        if tag == "tr":
            self.in_row = True
            self.td_counter = -1
            self.current_res = {
                "engine_url": self.url,
                "seeds": "-1", 
                "leech": "-1",
                "size": "0 MB"
            }

        if not self.in_row:
            return

        if tag == "td":
            self.td_counter += 1

        # Columna 1: Enlace Magnet y Nombre
        if self.td_counter == 1:
            if tag == "a" and "href" in attr:
                link = attr["href"]
                if link.startswith("magnet:"):
                    self.current_res["link"] = link
                elif "/details.php" in link:
                    self.current_res["desc_link"] = self.url + link if link.startswith("/") else link
                    self.current_item = "name"

        # Columna 2: Tamaño
        if self.td_counter == 2 and tag == "td":
            self.current_item = "size"

        # Columna 3: Semillas (Seeders)
        if self.td_counter == 3 and tag == "span" and attr.get("class") == "g":
            self.current_item = "seeds"

        # Columna 4: Leechers
        if self.td_counter == 4 and tag == "span" and attr.get("class") == "b":
            self.current_item = "leech"

    def handle_data(self, data):
        if self.current_item and self.in_row:
            data = data.strip()
            if data:
                if self.current_item == "name":
                    self.current_res["name"] = self.current_res.get("name", "") + data
                elif self.current_item == "size":
                    self.current_res["size"] = data
                elif self.current_item in ["seeds", "leech"]:
                    self.current_res[self.current_item] = data.replace(",", "")

    def handle_endtag(self, tag):
        if tag in ["a", "td", "span"]:
            self.current_item = None
            
        if tag == "tr" and self.in_row:
            self.in_row = False
            if "link" in self.current_res and "name" in self.current_res:
                prettyPrinter(self.current_res)
            self.current_res = {}


class uindex(object):
    url = "https://uindex.org"
    name = "Uindex"
    
    # Se ajustó "all" para que envíe el 0 como requiere la web
    supported_categories = {
        "all": "0",
        "movies": "1",
        "tv": "2",
        "games": "3",
        "music": "4",
        "software": "5",
        "anime": "7"
    }

    def search(self, what: str, cat="all"):
        # 1. Decodificar el texto que envía qBittorrent (quita los %20)
        what = urllib.parse.unquote(what)
        
        # 2. Reemplazar los espacios normales por el signo '+'
        query = what.replace(" ", "+")
        
        # 3. Obtener la categoría (por defecto "0" si no se encuentra)
        categ = self.supported_categories.get(cat, "0")
        
        # 4. Construir la URL exacta: /search.php?search=palabra+palabra&c=numero
        search_url = f"{self.url}/search.php?search={query}&c={categ}"

        try:
            html = retrieve_url(search_url)
            parser = UindexParser(self.url)
            parser.feed(html)
            parser.close()
            
        except Exception as e:
            print(f"Error en la búsqueda de Uindex: {e}")

    def download_torrent(self, info):
        print(f"{info} {info}")