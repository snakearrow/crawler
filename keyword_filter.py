import urllib.request, urllib.error, urllib.parse
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
import html2text
import re
from collections import Counter


def get_keywords(content: str, n_keywords: int = 10, min_length: int = 6):
    h = html2text.HTML2Text()
    h.ignore_links = True
    try:
        content = h.handle(content).replace("#", "").replace("*", "").replace("\n", " ").replace("{", "").replace("}", "").replace("/", "")
        content = re.sub(" +", ' ', content)
        words = content.split(" ")
        words = [word.lower() for word in words if len(word) >= min_length and "http:" not in word and "https:" not in word]
        occ_counter = Counter(words)
        occurrences = occ_counter.most_common(n_keywords)
        return [x[0] for x in occurrences]
    except:
        return []
