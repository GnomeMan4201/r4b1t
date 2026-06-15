#!/usr/bin/env python3
import re
import argparse
from bs4 import BeautifulSoup

def extract_urls(html_path: str, output_path: str):
    unique_urls = set()
    print(f"Parsing {html_path}...")
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'html.parser')
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href'].strip()
        if href.startswith('http://') or href.startswith('https://'):
            unique_urls.add(href)
    embedded_matches = re.findall(r'(https?://[^\s"\'<>\\]+)', html_content)
    for match in embedded_matches:
        unique_urls.add(match)
    sorted_urls = sorted(list(unique_urls))
    with open(output_path, 'w', encoding='utf-8') as f:
        for url in sorted_urls:
            f.write(url + '\n')
    print(f"Successfully extracted {len(sorted_urls)} unique URLs.")
    print(f"Output saved to → {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="index.html")
    parser.add_argument("--output", default="urls.txt")
    args = parser.parse_args()
    extract_urls(args.input, args.output)
