
def is_url_filtered(url: str):
    with open("url_filter.txt", "r") as fp:
        filtered_urls = fp.readlines()
        for fu in filtered_urls:
            if fu.strip() in url:
                return True
    return False
        
        
if __name__ == "__main__":
    filtered = is_url_filtered("https://store.apple.com/test")
    print(filtered)
