import urllib.request, urllib.error, urllib.parse
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import random
import unicodedata
import re
import sys
import signal
import os
import time
import html

from keyword_filter import get_keywords
from url_filter import is_url_filtered
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
        self._url_list = []
        self._title_list = []
        self._max_stay_on_site = 100
        self._current_on_site = 0
        self._previous_domain = None
        self._max_urls_in_list = 1000
        self._indexer = Indexer("localhost", 9200)
        
    def crawl(self, root_url: str, depth=0):
        self._url_list.append(root_url)
        current_idx = 0
        
        while current_idx < len(self._url_list):
            url = self._url_list[current_idx]
            print(80*"-")
            log.info(f"Processing {url}")
            current_idx += 1
            
            if is_url_filtered(url):
                log.info("URL is filtered, skipping")
                continue
                
            if len(url) >= self._max_url_length:
                log.info(f"URL is too long (max_length={self._max_url_length}), skipping")
                continue
        
            try:
                if not self.is_html(url):
                    log.info("URL is not HTML, skipping")
                    continue
                
                req = Request(url, headers=self._header)
                response = urlopen(req, timeout=3)
                content = response.read().decode(errors='ignore')
            except Exception as e:
                log.error(e)
                log.info("An error occurred while opening URL, skipping")
                continue
        
            # detect if url is an entirely new domain and reset counter
            if self.get_domain(url) != self._previous_domain:
                self._current_on_site = 0
            else:
                self._current_on_site += 1
            
            self._previous_domain = self.get_domain(url)
        
            # get title and check whether it's latin
            title = self.get_title(content)
            if title:
                title = title.strip()
                if self.is_latin(title):
                    keywords = get_keywords(content)
                    self._indexer.save(url, title, keywords)
                else:
                    log.info(f"Skipping because: Title not latin ('{title}')")
                    continue
    
            # extract links from html
            soup = BeautifulSoup(content, features="lxml")
            to_crawl = []
            cnt = 0
            for link in soup.findAll('a'):
                l = link.get('href')
                if l and (l.startswith("http") or l[0] == '/'):
                    if l[0] == '/':
                        l = urljoin(url, l)
                        
                    # discard too many links on same domain to prevent cycles
                    if self._current_on_site <= self._max_stay_on_site:
                        if not self._indexer.url_already_indexed(l) and l not in self._url_list:
                            self._url_list.append(l)
                            cnt += 1
                    # but make sure to append 'foreign' URLs in every case
                    if self.get_domain(url) != self.get_domain(l):
                        self._url_list.append(l)
                        cnt += 1
                
            log.info(f"URLs found: {len(self._url_list)} ({cnt} new)")
        
            # check whether to clean URL list so it doesn't get too big
            if len(self._url_list) >= self._max_urls_in_list:
                self.purge_url_list(self.get_domain(url))
                log.info("Purged URL list")
                current_idx = 0

        
    @staticmethod
    def get_domain(url: str, include_http=True):
        res = urlparse(url)
        if not include_http:
            return res.netloc
        return res.scheme + "://" + res.netloc
        
    def purge_url_list(self, current_domain: str):
        # cleans the URL list by randomly selecting N elements and filtering domains
        urls = []
        for url in self._url_list:
            if self.get_domain(url) == current_domain:
                continue
            urls.append(url)
            
        if len(urls) > self._max_urls_in_list:
            self._url_list = random.sample(urls, self._max_urls_in_list)
        else:
            self._url_list = urls
        
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
    def is_latin(s: str):
        s = re.sub(u"\u2013", "-", s)
        for c in s:
            if c.isalpha():
                if not "LATIN" in unicodedata.name(c):
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
