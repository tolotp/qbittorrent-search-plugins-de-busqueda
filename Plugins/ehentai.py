# VERSION: 1.0
# AUTHORS: tolotp

import urllib.request
import urllib.parse
import json
import ssl
import re
import html
import time
import datetime
from novaprinter import prettyPrinter 

class ehentai(object):
    url = 'https://e-hentai.org'
    name = 'E-Hentai'
    supported_categories = {'all': '0'} 

    def search(self, what, cat='all'):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        query = urllib.parse.unquote(what).strip().replace(' ', '+')
        search_url = f"{self.url}/torrents.php?search={query}"
        
        req = urllib.request.Request(search_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        
        try:
            response = urllib.request.urlopen(req, context=ctx)
            html_content = response.read().decode('utf-8')
        except Exception:
            return

        pattern = re.compile(
            r'<td class="itd"[^>]*>([\d\-:\s]+)</td>\s*'
            r'<td class="itd"><div[^>]*><a href="[^"]*"[^>]*>(.*?)</a></div></td>\s*'
            r'<td class="itd"[^>]*><a href="https://e-hentai\.org/g/(\d+)/([a-f0-9]+)/">\d+</a></td>\s*'
            r'<td class="itd"[^>]*>(.*?)</td>\s*'
            r'<td class="itd"[^>]*>(\d+)</td>\s*'
            r'<td class="itd"[^>]*>(\d+)</td>'
        )
        
        matches = pattern.findall(html_content)
        if not matches:
            prettyPrinter({
                'link': self.url,
                'name': "NO SE ENCONTRARON RESULTADOS / NO RESULTS FOUND",
                'size': '0', 'seeds': '0', 'leech': '0',
                'engine_url': self.url, 'desc_link': self.url
            })
            return
            
        chunk_size = 25
        for i in range(0, len(matches), chunk_size):
            chunk = matches[i:i + chunk_size]
            
            gidlist = []
            for match in chunk:
                gid = int(match[2])
                token = match[3]
                gidlist.append([gid, token])
                
            api_req_data = {
                "method": "gdata",
                "gidlist": gidlist,
                "namespace": 1
            }
            
            api_req = urllib.request.Request(
                "https://api.e-hentai.org/api.php",
                data=json.dumps(api_req_data).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            
            try:
                api_resp = urllib.request.urlopen(api_req, context=ctx)
                api_json = json.loads(api_resp.read().decode('utf-8'))
                gmetadata = api_json.get('gmetadata', [])
            except Exception:
                gmetadata = []

            meta_dict = {str(item.get('gid')): item for item in gmetadata}
            
            for match in chunk:
                try:
                    date_str = match[0].strip()
                    title = html.unescape(match[1])
                    gid = match[2]
                    token = match[3]
                    
                    size = match[4].replace('MiB', 'MB').replace('GiB', 'GB').replace('KiB', 'KB')
                    seeds = match[5]
                    leeches = match[6]
                    
                    pub_date_str = '-1'
                    try:
                        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                        pub_date_str = str(int(dt.timestamp()))
                    except Exception:
                        pass
                    
                    desc_link = f"{self.url}/g/{gid}/{token}/"
                    
                    metadata = meta_dict.get(gid, {})
                    torrents = metadata.get('torrents', [])
                    
                    best_hash = None
                    
                    # buscar el hash cuyo nombre coincide exactamente o termina en .zip
                    for t in torrents:
                        if t.get('name') == title or t.get('name') == f"{title}.zip":
                            best_hash = t.get('hash')
                            break
                    
                    if not best_hash and torrents:
                        best_hash = torrents[0].get('hash')
                    
                    if best_hash:
                        # Usar el first_gid si está presente
                        torrent_gid = metadata.get('first_gid')
                        
                        # Si no tiene first_gid, usamos el gid normal de la búsqueda
                        if not torrent_gid:
                            torrent_gid = gid
                            
                        # Armamos el enlace
                        download_link = f"https://ehtracker.org/get/{torrent_gid}/{best_hash}.torrent"
                    else:
                        continue
                    
                    res = {
                        'name': title,
                        'size': size,
                        'seeds': seeds,
                        'leech': leeches,
                        'engine_url': self.url,
                        'desc_link': desc_link,
                        'link': download_link,
                        'pub_date': pub_date_str
                    }
                    
                    prettyPrinter(res)
                except Exception:
                    continue
                
            # Pequeña pausa para no saturar la API
            if i + chunk_size < len(matches):
                time.sleep(1)