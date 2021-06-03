from elasticsearch import Elasticsearch
from datetime import datetime
import hashlib
from Log import log


class Indexer:

    def __init__(self, hostname: str, port: str, user: str = None, password: str = None, index_name = "crawler_main"):
        self._index_name = index_name
        if not user or not password:
            url = f"http://{hostname}:{port}"
        elif user and password:
            url = f"http://{user}:{password}@{hostname}:{port}"
        else:
            raise RuntimeException("Please specify user and password for elasticsearch connection")
            
        self._es = Elasticsearch([url])
        
        if not self._es.indices.exists(index=self._index_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "url_hash": {
                            "type": "keyword",
                            "index": "true"
                       }
                    }
                }
            }
            self._es.indices.create(index=self._index_name, body=mapping)
            log.info(f"Index {self._index_name} created")
        else:
            res = self._es.cat.count(self._index_name, params={"format": "json"})
            count = res[0]['count']
            log.info(f"Index {self._index_name} already contains {count} entries")
            
    def save(self, url: str, title: str, keywords, language: str):
        # skip already indexed urls
        if self.url_already_indexed(url):
            log.info(f"URL {url} already indexed, skipping")
            return
            
        doc = {
            'url_hash': self.to_md5(url),
            'url': url,
            'title': title,
            'keywords': keywords,
            'language': language,
            'timestamp': datetime.now(),
        }
        res = self._es.index(index=self._index_name, body=doc)
        if res['result'] != "created":
            log.warning(f"Could not index {url}, result was: {res['result']}")
        else:
            log.info(f"Indexed {url}: {title} (language='{language}')")
            
    def url_already_indexed(self, url: str):
        res = self._es.search(index=self._index_name, body={"query": {"constant_score": {"filter": {"term": {"url_hash": self.to_md5(url)}}}}})
        return res['hits']['total']['value'] > 0
            
    def delete_index(self):
        self._es.indices.delete(index=self._index_name)
        log.info(f"Deleted index {self._index_name}")
        
    def to_md5(self, s: str):
        return hashlib.md5(s.encode()).hexdigest()
        

if __name__ == "__main__":
    idx = Indexer("localhost", 9200)
    #idx.save("https://www.test.de", "Tests", "no keywords")
    print(idx.url_already_indexed("https://www.test.de"))
    #idx.delete_index()

