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

MAX_DEPTH = 100
MAX_URL_LENGTH = 200
HEADER = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}

already_visited = []
newly_visited = [] # newly visited in this session
last_titles = []
counter = 0
abort = False

stay_on_site = True

def write_newly_visited():
    global newly_visited
    with open("already_visited.txt", "a") as fp:
        for link in newly_visited:
            fp.write(link+"\n")
            
    n = len(newly_visited)
    newly_visited = []
    return n

def exit_handler(sig, frame):
    global already_visited
    global abort
    
    abort = True
    
    write_newly_visited()
    print(f"Already indexed {len(already_visited)} URLs")
    
    sys.exit(0)

def is_english(s):
    s = re.sub(u"\u2013", "-", s)
    charset = "abcdefghijklmnopqrstuvwxyz1234567890äüöß?!\"§$%&/()=#+*_-€@|;:.,^°~][}{ "
    for c in s:
        if c.lower() not in charset:
            print(f"character not known: {c.lower()} {ord(c.lower())}")
            return False
            
    return True
        
def get_title(data: str):
    global last_titles
    start = data.find("<title>")
    if start == -1:
        return None
        
    end = data.find("</title>")
    title = data[start+7:end]
    title = title.strip()
    title = html.unescape(title)
    if len(title) <= 3:
        return None
        
    count = 0
    for t in last_titles:
        sim = SequenceMatcher(None, t, title).ratio()
        if sim >= 0.75:
            count += 1
            
    if count >= 5:
        print(f"Discarding '{title}' because it's soo similar")
        return None
        
    last_titles.append(title)
    if len(last_titles) > 10:
        del last_titles[0]
        
    return title

def get_domain(url: str):
    return urlparse(url).netloc

def crawl(url: str, depth = 0, force = False):
    global already_visited
    global counter
    global abort
    
    if abort:
        return
        
    if depth > MAX_DEPTH:
        return
        
    url = url.rstrip()
    
    if url in already_visited or len(url) > MAX_URL_LENGTH or len(url) <= 3:
        if not force:
            return
        
    # exclude f*cking google
    if "google." in url or "googleapis." in url:
        return
        
    # exclude instagram & facebook
    if "facebook.com" in url or "instagram.com" in url or "twitter.com" in url:
        return
        
    # exclude linkedin & co
    if "linkedin.com" in url or "xing.com" in url:
        return
        
    # others excludes
    if "pubads." in url or "doubleclick.net" in url or "web.archive.org" in url or "apps.apple.com" in url:
        return
        
    if "uselang=" in url:
        return
        
    print(80*'-')
    print(f"Crawling {url} (depth={depth})")
    with open("last_visited.txt", "w") as fp:
        fp.write(url+"\n")
    
    already_visited.append(url)
    newly_visited.append(url)
    
    try:
        if not is_html(url):
            return
            
        req = Request(url, headers=HEADER)
        response = urlopen(req, timeout=3)
        content = response.read().decode(errors='ignore')
    except Exception as e:
        print(e)
        return
        
    title = get_title(content)
    if title:
        title = title.strip()
        if is_english(title):
            print(f"Title: {title}")
            keywords = get_keywords(content)
            save(url, title, keywords)
        else:
            print(f"NOT ENGLISH: {title}")
    
    soup = BeautifulSoup(content, features="lxml")
    to_crawl = []
    for link in soup.findAll('a'):
        l = link.get('href')
        if l and (l.startswith("http") or l[0] == '/'):
            if l[0] == '/':
                l = urljoin(url, l)
                
            counter += 1
            if counter % 20 == 0:
                write_newly_visited()
                counter = 0
                
            # stay on site first, then crawl external links
            domain = get_domain(url)
            new_domain = get_domain(l)
            if domain == new_domain:
                crawl(l, depth+1)
            else:
                to_crawl.append(l)
                
    for l in to_crawl:
        crawl(l, depth+1)

def save(url, title, keywords):
    start_letter = title[0]
    index_folder = "index/" + start_letter    
    # create index folder if it doesn't exist
    if not os.path.exists(index_folder):
        if not os.path.exists("index"):
            os.mkdir("index")
        os.mkdir(index_folder)
        
    index_file = index_folder + "/index.txt"
    ts = time.time()
    title = title.replace('\n', '').replace('\r', '')
    with open(index_file, "a") as fp:
        fp.write(f"{title}:::{url}:::{ts}:::{keywords}\n")
        
def get_file_type(url):
    try:
        resp = urlopen(Request(url, method="HEAD", headers=HEADER), timeout=3)
        header = resp.info()
        file_type = header['Content-Type']
        return str(file_type)
    except Exception as e:
        if "405" in str(e):
            return "text/html"
            
        print(e)
        return None
    
def is_html(url):
    file_type = get_file_type(url)
    if not file_type:
        return False
    if "text/html" in file_type:
        return True
    return False
    
def get_last_visited():
    if not os.path.exists("last_visited.txt"):
        return None
        
    with open("last_visited.txt", "r") as fp:
        return fp.readline().rstrip()
        
def init_already_visited():
    global already_visited
    if not os.path.exists("already_visited.txt"):
        return
    
    with open("already_visited.txt", "r") as fp:
        lines = fp.readlines()
        for url in lines:
            already_visited.append(url.rstrip())
        
        print(f"Already visited {len(lines)} URLs")
        return len(lines)
        
if __name__ == "__main__":
    force = False
    root_url = sys.argv[1]
    if len(sys.argv) == 3 and sys.argv[2] == "--force":
        force = True
        
    print(f"Using root URL {root_url}, force={force}")
    signal.signal(signal.SIGINT, exit_handler)
    sys.setrecursionlimit(1000000)
    n = init_already_visited()
    last_url = get_last_visited()
    
    if force:
        crawl(root_url, force=True)
    
    elif root_url not in already_visited:
        # start a new session with a fresh URL
        crawl(root_url)
        
    elif last_url:
        # continue from where we left off
        print(f"Last URL: {last_url}")
        if last_url in already_visited:
            already_visited.remove(last_url)
            
        crawl(last_url)
    elif n > 0:
        last_url = already_visited[-1]
        print(f"Last URL: {last_url}")
        if last_url in already_visited:
            already_visited.remove(last_url)
        # continue from where we left off
        crawl(last_url)
    else:
        # new session
        crawl(root_url)
        
