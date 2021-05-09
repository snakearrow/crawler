import sys
import signal
from Crawler import Crawler


def exit_handler(sig, frame):
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: main.py [root-url]")
        sys.exit(1)
        
    signal.signal(signal.SIGINT, exit_handler)
    crawler = Crawler()
    crawler.crawl(sys.argv[1])
    
