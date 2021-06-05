from flask import Flask, render_template, request
import os
from datetime import datetime
from timeit import default_timer as timer
from urllib.parse import urlparse
from ast import literal_eval
from elasticsearch import Elasticsearch


MAX_RESULTS = 1000

app = Flask(__name__)

class SingleResult:

    def __init__(self, title, url, ts, keywords):
        self._title = title
        self._url = url
        self._ts = ts
        self._keywords = keywords
        
    def __str__(self):
        return f"SingleResult title='{self._title}'   url='{self._url}'"
    
class SearchResult:
    # a search result containing a list of single results, 
    # the time in seconds the search took, 
    # and the keyword that was searched for
    def __init__(self, results, search_time, keyword):
        self._results = results
        self._search_time = search_time
        self._keyword = keyword
        

class Server:
    def __init__(self, hostname: str, port: int, user: str=None, password: str=None, index_name: str="crawler_main"):
        self._index_name = index_name
        if not user or not password:
            url = f"http://{hostname}:{port}"
        elif user and password:
            url = f"http://{user}:{password}@{hostname}:{port}"
        else:
            raise RuntimeException("Please specify user and password for elasticsearch connection")
            
        self._es = Elasticsearch([url])
        if not self._es.indices.exists(index=self._index_name):
            raise RuntimeException(f"Index {index_name} does not exist")
        else:
            print(f"Elastisearch connection (index {index_name}) ok")
        
    def search(self, _keywords: list, language: str = "en"):
        keywords = []
        for word in _keywords:
            keywords.append(word)
            keywords.append('*' + word + '*')
        
        keywords = ' '.join(keywords)
        query = {
	        "query": {
		        "bool": {
			        "must": [
				        {
					        "query_string": {
						        "query": keywords,
						        "fields": [
							        "url^4",
							        "keywords",
							        "title^2"
						        ]
					        }
				        },
				        {
					        "wildcard": {
						        "language": language
					        }
				        }
			        ]
		        }
	        },
	        "sort": {
		        "_script": {
			        "type": "number",
			        "script": "doc['url.keyword'].value.length()",
			        "order": "asc"
		        }
	        }
        }
        res = self._es.search(index=self._index_name, body=query)
        search_time = int(res['took'])
        hits = res['hits']['hits']
        
        result = []
        for hit in hits:
            url = hit['_source']['url']
            title = hit['_source']['title']
            ts = hit['_source']['timestamp']
            kw = hit['_source']['keywords']
            result.append(SingleResult(title, url, ts, kw))
        
        return SearchResult(result, search_time/1000.0, ' '.join(_keywords))
        
        
@app.route('/')
def render():
    return render_template('index.html')
    
@app.route('/', methods=['POST','GET'])
def search():
    result = None
    if request.method == 'POST':
        keyword = request.form['text']
        language = request.form['language']
        if language == "none":
            language = "*"
        result = server.search(keyword.split(), language)
        
    return render_template('index.html', data=result, n_results=len(result._results))

# main application starts here
server = Server("localhost", 9200)
app.run()

