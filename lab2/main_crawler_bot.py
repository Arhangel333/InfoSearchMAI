"""
sitemap_parser.py

Рекурсивно обходит sitemap (индекс → вложенные urlset'ы),
собирает все <loc> и пишет в файл, пока не наберёт лимит.
"""

import sys
import yaml
import time
import gzip
import io
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import requests
from pymongo import MongoClient


truework = 0

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


stats = {
    "files_ok": 0,
    "files_failed": 0,
    "urls_collected": 0,
}



HEADERS = {
    "User-Agent": "MaiSitemapParser/1.0 (+https://github.com/yourname; contact@example.com)",
    "Accept": "application/xml, text/xml, */*",
}


def fetch(url: str, timeout: int = 30) -> bytes | None:
    """Скачивает URL, распаковывая gzip."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        content = r.content

        
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)

        return content
    except requests.RequestException as e:
        print(f"  [error] {url}: {e}", file=sys.stderr)
        stats["files_failed"] += 1
        return None


def parse_sitemap(content: bytes) -> tuple[list[str], list[str]]:
    """
    Парсит XML.
    Возвращает (urls, sub_sitemaps):
      urls — ссылки на страницы (<loc> внутри <url>)
      sub_sitemaps — ссылки на вложенные sitemap (<loc> внутри <sitemap>)
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"  [parse error] {e}", file=sys.stderr)
        return [], []

    tag = root.tag.split("}")[-1]   

    urls = []
    sub_sitemaps = []

    if tag == "urlset":
        for loc in root.findall(".//sm:url/sm:loc", NS):
            if loc.text:
                urls.append(loc.text.strip())

    elif tag == "sitemapindex":
        for loc in root.findall(".//sm:sitemap/sm:loc", NS):
            if loc.text:
                sub_sitemaps.append(loc.text.strip())

    else:
        print(f"  [warn] неизвестный корень: {tag}", file=sys.stderr)

    return urls, sub_sitemaps


def crawl_sitemap(start_url: str,
                  out_file,
                  db,
                  limit: int = 1_000_000,
                  delay: float = 0.3,
                  max_depth: int = 10) -> None:
    """
    Рекурсивно обходит sitemap, начиная с start_url.
    Пишет все найденные страницы в out_file.
    Останавливается при достижении limit.
    """
    
    queue = [(start_url, 0)]
    seen_sitemaps = set()   

    while queue:
        if stats["urls_collected"] >= limit:
            print(f"\nДостигнут лимит: {limit}")
            return

        url, depth = queue.pop(0)

        if url in seen_sitemaps:
            continue
        if depth > max_depth:
            print(f"  [skip] превышена глубина: {url}", file=sys.stderr)
            continue

        seen_sitemaps.add(url)
        print(f"[{stats['files_ok'] + stats['files_failed'] + 1}] "
              f"depth={depth} → {url}")

        content = fetch(url)
        if content is None:
            continue

        stats["files_ok"] += 1
        urls, sub_sitemaps = parse_sitemap(content)

        
        for page_url in urls:
            if stats["urls_collected"] >= limit:
                return
            if truework:
                db.documents.insert_one({"url": page_url})
            out_file.write(page_url + "\n")
            stats["urls_collected"] += 1

            if stats["urls_collected"] % 10_000 == 0:
                print(f"  ... собрано {stats['urls_collected']} URL")
                out_file.flush()

        print(f"  страниц: {len(urls)}, вложенных sitemap: {len(sub_sitemaps)}, "
              f"всего собрано: {stats['urls_collected']}")

        
        for sub in sub_sitemaps:
            if sub not in seen_sitemaps:
                queue.append((sub, depth + 1))

        time.sleep(delay)   


def main():
    if len(sys.argv) < 2:
        print("Usage: python <programm> <input.yaml> ")
        print("Example:")
        print("  python response_bot.py config.yaml")   
        sys.exit(1)

    file = sys.argv[1]

    with open(file, "r") as f:
        yam = yaml.safe_load(f)
        
    client = MongoClient(yam["db"]["client"])
    db = client["crawler"]

    domen = yam["logic"]["domen"]
    start_url = yam["logic"]["target"]
    out_path = yam["logic"]["output_file1"]
    try:
        limit = int(yam["logic"]["limit1"])
    except:
        limit = 1_000_000

    print(f"Start:  {start_url}")
    print(f"Output: {out_path}")
    print(f"Limit:  {limit}")
    print()

    t0 = time.time()
    
    
    


    with open(out_path, "w", encoding="utf-8") as out:
        crawl_sitemap(start_url, out, db, limit=limit)

    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print(f"Готово за {elapsed:.1f} сек")
    print(f"Файлов обработано: {stats['files_ok']} (ошибок: {stats['files_failed']})")
    print(f"URL собрано:       {stats['urls_collected']}")
    print(f"Записано в:        {out_path}")


if __name__ == "__main__":
    main()