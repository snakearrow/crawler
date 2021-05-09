from flask import Flask, render_template, request
import os
from datetime import datetime
from timeit import default_timer as timer
from urllib.parse import urlparse
from ast import literal_eval


app = Flask(__name__)

index = []

MAX_RESULTS_SAME_PAGE = 3

class IndexEntry:
    
    _title = None
    _url = None
    _ts = None
    _rating = 0.0
    
    def __init__(self, title, url, ts, keywords):
        self._title = title
        self._url = url
        self._ts = ts
        self._keywords = keywords
        
    def __str__(self):
        return f"IndexEntry title='{self._title}'   url='{self._url}'"
    
def init_index():
    global index
    start = timer()
    
    root = "index"
    dirlist = [ item for item in os.listdir(root) if os.path.isdir(os.path.join(root, item)) ]
    for d in dirlist:
        index_file = root + "/" + d + "/index.txt"
        if not os.path.exists(index_file):
            continue
        
        with open(index_file, "r") as fp:
            data = fp.readlines()
            for line in data:
                try:
                    s = line.split(":::")
                    ts = str(datetime.fromtimestamp(float(s[2])))
                    keywords = literal_eval(s[3])
                    entry = IndexEntry(s[0], s[1], ts, keywords)
                    index.append(entry)
                except Exception as e:
                    print(f"Error in {index_file}")
    
    stop = timer()
    print(f"Indexed {len(index)} entries in {stop - start} sec.")
    
def any_in(needle, stack):
    for n in needle:
        for s in stack:
            if n in s:
                return True


def count_in(needle, stack):
    counter = 0
    for n in needle:
        for s in stack:
            if n in s:
                counter += 1 
    return counter
    
def all_in(needle, stack):
    n = count_in(needle, stack)
    print(f"needle: {needle} , stack: {stack}, n: {n}")
    return n >= len(needle)
    
def search_index(keywords: str):
    global index
    result = []
    
    keywords = [x.lower().strip() for x in keywords]
    
    for entry in index:
        # extract base url
        rating = 0.0
        
        url = entry._url
       
        domain = urlparse(url).netloc
        in_domain = False
        if any_in(keywords, [domain]):
            rating += 4.0
            in_domain = True
            
        if any_in(keywords, [url]) and not in_domain:
            rating += 2.5
            
        if any_in(keywords, [entry._title.lower().split()]):
            rating += 2.0
            rating += count_in(keywords, [entry._title.lower().split()])
            
        if any_in(keywords, entry._keywords):
            rating += count_in(keywords, entry._keywords)
            
        if all_in(keywords, entry._keywords) and len(keywords) > 1:
            print(f"here +5: {entry._title}")
            rating += 5.0
            
        if all_in(keywords, [entry._title.lower().split()]) and len(keywords) > 1:
            print("here +5 again")
            rating += 5.0
            
        if len(domain) >= 30:
            rating -= 3.0
        elif len(domain) >= 20:
            rating -= 2.0
        elif len(domain) >= 10:
            rating -= 0.5
            
        if len(url) >= 80:
            rating -= 3.0
        elif len(url) >= 60:
            rating -= 1.0
            
        if rating > 10.0:
            rating = 10.0
        elif rating < 0.0:
            rating = 0.0
        
        entry._rating = rating
            
        if rating >= 1.0:
            result.append(entry)
            
    if len(result) == 0:
        return result
          
    # sort by rating
    max_results = 100
    sorted_result = []
    while len(result) > 0:
        max_rated = result[0]
        i = 0
        max_rated_idx = 0
        for entry in result:
            if entry._rating > max_rated._rating:
                max_rated = entry
                max_rated_idx = i
            i += 1
        sorted_result.append(max_rated)
        del result[max_rated_idx]
    
    result = sorted_result[:max_results]
    
    # filter duplicate domains
    domains = {}
    filtered_results = []
    for entry in result:
        domain = urlparse(entry._url).netloc
        if domain in domains:
            domains[domain] += 1
            if domains[domain] < MAX_RESULTS_SAME_PAGE:
                filtered_results.append(entry)
        else:
            domains[domain] = 0
            filtered_results.append(entry)
    return filtered_results
    
@app.route('/')
def render():
    return render_template('index.html')
    
@app.route('/', methods=['POST','GET'])
def search():
    data = None
    if request.method == 'POST':
        keyword = request.form['text']
        print(f"Searching {keyword}")
        data = search_index(keyword.split())
        print(f"Found {len(data)} results")
        
    return render_template('index.html', data=data, keyword=keyword, n_results=len(data))

if __name__=='__main__':
    init_index()
    app.run()
