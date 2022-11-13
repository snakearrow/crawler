# Web Page Crawler

Crawls web pages and saves the URL and a description in an elasticsearch database. Additionally provides a web frontend to search for homepages, URLs and keywords.

Built with
<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original-wordmark.svg" width=64 height=64/><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/flask/flask-original-wordmark.svg" width=64 height=64/> and Elasticsearch
          


Usage:
- run local elasticsearch instance on `localhost:9000`
- run frontend server: `python3 server.py`
- run crawler: `python3 main.py [root-url]`
