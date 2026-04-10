# VERSION: 1.2
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
                    self.current_item = "name"
                elif "/details.php" in link or "/torrent/" in link:
                    self.current_res["desc_link"] = self.url + link if link.startswith("/") else link
                    self.current_item = "name"

        # Columna 2: Tamaño
        elif self.td_counter == 2:
            if tag == "td":
                self.current_item = "size"

        # Columna 4: Seeds
        elif self.td_counter == 4:
            if tag == "span" and attr.get("class") == "sr-seed":
                self.current_item = "seeds"
            elif tag == "td":  
                self.current_item = "seeds"

        # Columna 5: Leechers
        elif self.td_counter == 5:
            if tag == "span" and attr.get("class") == "sr-leech":
                self.current_item = "leech"
            elif tag == "td":  
                self.current_item = "leech"

    def handle_data(self, data):
        if self.in_row and self.current_item:
            data = data.strip()
            if not data:
                return

            if self.current_item == "name":
                self.current_res["name"] = self.current_res.get("name", "") + data
            elif self.current_item == "size":
                self.current_res["size"] = data
                self.current_item = None
            elif self.current_item == "seeds":
                self.current_res["seeds"] = data.replace(",", "").replace(".", "")
                self.current_item = None
            elif self.current_item == "leech":
                self.current_res["leech"] = data.replace(",", "").replace(".", "")
                self.current_item = None

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_row:
            self.in_row = False
            if "link" in self.current_res and "name" in self.current_res:
                prettyPrinter(self.current_res)
            self.current_res = {}
        elif tag == "a" and self.current_item == "name":
            self.current_item = None


class uindex(object):
    url = "https://uindex.org"
    name = "Uindex"
    
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
        what = urllib.parse.unquote(what)
        query = what.replace(" ", "+")
        categ = self.supported_categories.get(cat, "0")
        search_url = f"{self.url}/search.php?search={query}&c={categ}"

        try:
            html = retrieve_url(search_url)
            parser = UindexParser(self.url)
            parser.feed(html)
            parser.close()
        except Exception:
            pass