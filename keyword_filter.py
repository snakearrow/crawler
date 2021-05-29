import urllib.request, urllib.error, urllib.parse
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import html2text
import re
import unicodedata
from collections import Counter


def get_keywords(content: str, n_keywords: int = 10, min_length: int = 6):
    # try to parse <meta> description tag
    valid_attributes = ["description", "keywords"]
    
    try:
        soup = BeautifulSoup(content, 'html.parser')
        meta_list = soup.find_all("meta")
        for meta in meta_list:
            if "name" in meta.attrs:
                if meta["name"].lower() in valid_attributes:
                    description = meta.attrs["content"]
                    keywords = [unicodedata.normalize("NFKD", x) for x in description.split(" ") if len(x) >= min_length]
    except Exception:
        pass
            
    # parsing <meta> tag not possible, parse entire HTML and get most frequent keywords
    h = html2text.HTML2Text()
    h.ignore_links = True
    try:
        content = h.handle(content).replace("#", "").replace("*", "").replace("\n", " ").replace("{", "").replace("}", "").replace("/", "")
        content = re.sub(" +", ' ', content)
        words = content.split(" ")
        words = [word.lower() for word in words if len(word) >= min_length and "http:" not in word and "https:" not in word]
        occ_counter = Counter(words)
        occurrences = occ_counter.most_common(n_keywords)
        return [unicodedata.normalize("NFKD", x[0]) for x in occurrences]
    except:
        return []
        

if __name__ == "__main__":
    import sys
    req = Request(sys.argv[1])
    response = urlopen(req, timeout=5)
    content = response.read().decode(errors='ignore')
    keywords = get_keywords(content)
    print(keywords)
