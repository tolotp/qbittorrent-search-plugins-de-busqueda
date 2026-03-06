# VERSION: 1.0
# AUTHORS: tolotp

import os
import configparser
import urllib.parse
import re
import datetime
from tempfile import mkstemp
from html.parser import HTMLParser
from urllib import request
from novaprinter import prettyPrinter

# ====================================================================
# SISTEMA DE CONFIGURACIÓN AUTOMÁTICO (.ini)
# ====================================================================
# Detecta la "Carpeta Personal" del usuario en Windows C:\Users\TuNombreDeUsuario o Linux /home/tunombre/
USER_HOME = os.path.expanduser("~")
CONFIG_FILE = os.path.join(USER_HOME, "latteam_config.ini")

def get_cookie():
    # AGREGAMOS interpolation=None PARA QUE LOS '%' DE LA COOKIE NO CRASHEEN EL SCRIPT
    config = configparser.ConfigParser(interpolation=None)
    
    # Si el archivo NO existe, lo creamos con el campo de cookie vacío
    if not os.path.exists(CONFIG_FILE):
        config['login'] = {
            'cookie': ''
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        return ""
    
    # Si el archivo SÍ existe, lo leemos
    config.read(CONFIG_FILE, encoding='utf-8')
    try:
        return config.get('login', 'cookie').strip()
    except (configparser.NoSectionError, configparser.NoOptionError):
        return ""

# Obtenemos la cookie automáticamente
COOKIE = get_cookie()

class LatTeamParser(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.current_res = {}
        self.current_item = None
        self.in_row = False

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)

        if tag == "tr":
            self.in_row = True
            self.current_res = {
                "engine_url": self.url,
                "seeds": "-1", 
                "leech": "-1",
                "size": "0 MB"
            }

        if not self.in_row:
            return

        # 1. Búsqueda de enlaces
        if tag == "a" and "href" in attr:
            link = attr["href"]
            if "/torrents/download/" in link or link.endswith("/download"):
                self.current_res["link"] = link
            elif re.search(r'/torrents/\d+$', link):
                if "desc_link" not in self.current_res:
                    self.current_res["desc_link"] = link
                    self.current_item = "name"

        # 2. Identificación exacta por Clases HTML
        clase = attr.get("class", "")
        if "torrent-search--list__size" in clase:
            self.current_item = "size"
        elif "torrent__seeder-count" in clase:
            self.current_item = "seeds"
        elif "torrent__leecher-count" in clase:
            self.current_item = "leech"
        elif "torrent-search--list__age" in clase:
            self.current_item = "age"

        # 3. Capturar la fecha de publicación y convertirla para qBittorrent
        if tag == "time" and self.current_item == "age":
            if "datetime" in attr:
                date_str = attr["datetime"]
                try:
                    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    self.current_res["pub_date"] = str(int(dt.timestamp()))
                except ValueError:
                    self.current_res["pub_date"] = date_str

    def handle_data(self, data):
        if not self.in_row or not self.current_item:
            return
            
        data = data.replace('\xa0', ' ').replace('&nbsp;', ' ').strip()
        if not data:
            return

        if self.current_item == "name":
            self.current_res["name"] = self.current_res.get("name", "") + data
            
        elif self.current_item == "size":
            if any(x in data.upper() for x in ["B", "IB"]):
                self.current_res["size"] = data
                
        elif self.current_item == "seeds":
            self.current_res["seeds"] = data.replace(',', '')
            self.current_item = None 
            
        elif self.current_item == "leech":
            self.current_res["leech"] = data.replace(',', '')
            self.current_item = None

    def handle_endtag(self, tag):
        if tag == "a" and self.current_item == "name":
            self.current_item = None
        elif tag == "td" and self.current_item in ["size", "age"]:
            self.current_item = None
            
        if tag == "tr" and self.in_row:
            self.in_row = False
            if "link" in self.current_res and "name" in self.current_res:
                prettyPrinter(self.current_res)
            self.current_res = {}


class latteam(object):
    url = "https://lat-team.com/"
    name = "Lat-Team"
    
    # Mapeo de categorías oficiales de qBittorrent
    supported_categories = {
        "all": "",
        "movies": "1",
        "tv": "2",
        "music": "3",
        "games": "4",
        "anime": "5",
        "books": "18"
    }

    def search(self, what: str, cat="all"):
        if not COOKIE:
            print(f"Por favor, configura tu cookie en el archivo: {CONFIG_FILE}")
            return

        what = urllib.parse.unquote(what)
        query = what.replace(" ", "+")
        categ = self.supported_categories.get(cat, "")
        
        search_url = f"{self.url}torrents/?name={query}"
        if categ:
            search_url += f"&categoryIds[0]={categ}"

        try:
            req = request.Request(search_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html",
                "Cookie": COOKIE
            })
            response = request.urlopen(req)
            html = response.read().decode('utf-8', errors='ignore')
            
            parser = LatTeamParser(self.url)
            parser.feed(html)
            parser.close()
            
        except Exception as e:
            print(f"Error en la búsqueda de Lat-Team: {e}")

    def download_torrent(self, url):
        if not COOKIE:
            return

        f, path = mkstemp(".torrent")
        try:
            req = request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cookie": COOKIE
            })
            with request.urlopen(req) as response:
                with open(f, "wb") as file:
                    file.write(response.read())
        except Exception as e:
            print(f"Error downloading torrent: {e}")

        print(f"{path} {url}")