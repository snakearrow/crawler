import urllib.request, urllib.error, urllib.parse
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import re
import sys
import signal
import os
import time
import html

from keyword_filter import get_keywords
from Indexer import Indexer
from Log import log


class Crawler:

    _header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}

    def __init__(self):
        self._max_url_length = 100
        self._max_depth = 5
        self._current_depth = 0
        self._url_list = [] # TODO: init from elastic ?
        self._title_list = []
        self._indexer = Indexer("localhost", 9200)
        
    def crawl(self, root_url: str, depth=0):
        try:
            if not self.is_html(root_url):
                return
            
            req = Request(root_url, headers=self._header)
            response = urlopen(req, timeout=3)
            content = response.read().decode(errors='ignore')
        except Exception as e:
            log.error(e)
            return
        
        title = self.get_title(content)
        if title:
            title = title.strip()
            if self.is_english(title):
                keywords = get_keywords(content)
                self._indexer.save(root_url, title, keywords)
            else:
                log.info(f"NOT ENGLISH: {title}")
    
        soup = BeautifulSoup(content, features="lxml")
        to_crawl = []
        for link in soup.findAll('a'):
            l = link.get('href')
            if l and (l.startswith("http") or l[0] == '/'):
                if l[0] == '/':
                    l = urljoin(root_url, l)
                    
                if not self._indexer.url_already_indexed(l) and l not in self._url_list:
                    self._url_list.append(l)
                
        log.info(f"URLs found: {len(self._url_list)}")
        self._current_depth += 1
        if self._current_depth >= self._max_depth:
            self._current_depth -= 1
            return
        
        for url in self._url_list:
            self.crawl(url, self._current_depth)
        
    def get_urls(self, document: str):
        pass
        
    def get_title(self, document: str):
        start = document.find("<title>")
        if start == -1:
            return None
        
        end = document.find("</title>")
        title = html.unescape(document[start+7:end].strip())
        if len(title) <= 3:
            return None
        
        # check if we have seen this title already multiple times
        count = 0
        for t in self._title_list:
            sim = SequenceMatcher(None, t, title).ratio()
            if sim >= 0.75:
                count += 1
                
            if count >= 5:
                log.warning(f"Discarding '{title}' because it's soo similar")
                return None
            
        self._title_list.append(title)
        if len(self._title_list) > 10:
            del self._title_list[0]
            
        return title
        
    def is_html(self, url: str):
        file_type = self.get_file_type(url)
        if not file_type:
            return False
        if "text/html" in file_type:
            return True
        return False
        
    @staticmethod
    def is_english(s: str):
        s = re.sub(u"\u2013", "-", s)
        charset = "abcdefghijklmnopqrstuvwxyz1234567890äüöß?!\"§$%&/()=#+*_-€@|;:.,^°~][}{ "
        for c in s:
            if c.lower() not in charset:
                log.debug(f"character not known: {c.lower()} {ord(c.lower())}")
                return False
            
        return True
        
    def get_file_type(self, url: str):
        try:
            resp = urlopen(Request(url, method="HEAD", headers=self._header), timeout=3)
            header = resp.info()
            file_type = header['Content-Type']
            return str(file_type)
        except Exception as e:
            if "405" in str(e):
                return "text/html"
            log.warning(e)
            return None


if __name__ == "__main__":
    c = Crawler()
    c.crawl("https://www.test.de")
