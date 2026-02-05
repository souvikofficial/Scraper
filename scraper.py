import random
import time
import re
import json
from typing import Callable, Iterable, Optional, Tuple
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


  
# HTML FETCHING
def fetch_html(
    url,
    use_selenium=False,
    user_agents=None,
    infinite_scroll=False,
    load_more_selector=None,
    use_tor=False,
    timeout=20,
    retries=2,
    backoff=1.5,
):
    """
    Fetch fully rendered HTML from a page.
    Supports routing through Tor SOCKS5 proxy if use_tor=True.
    """
    headers = {"User-Agent": random.choice(user_agents or ["Mozilla/5.0"])}

    if use_selenium:
        options = Options()
        options.add_argument("--headless=new")  # Use new headless mode to reduce logs
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument(f"--user-agent={headers['User-Agent']}")
        if use_tor:
            # Route Chrome through Tor proxy at 127.0.0.1:9050 (default Tor SOCKS5)
            options.add_argument('--proxy-server=socks5://127.0.0.1:9050')
        driver = webdriver.Chrome(options=options)
        try:
            print(f"Navigating to URL in Selenium: {url}")  # Debug log for URL loading
            driver.get(url)
        except Exception as e:
            print(f"Exception loading URL in Selenium: {e}")
            driver.quit()
            raise

        if infinite_scroll:
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

        if load_more_selector:
            from selenium.webdriver.common.by import By
            while True:
                try:
                    button = driver.find_element(By.CSS_SELECTOR, load_more_selector)
                    if button.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(1)
                        button.click()
                        time.sleep(2)
                    else:
                        break
                except:
                    break

        html = driver.page_source
        driver.quit()
        return html

    else:
        proxies = None
        if use_tor:
            proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            }
        session = requests.Session()
        last_err = None
        for attempt in range(retries + 1):
            try:
                res = session.get(url, headers=headers, timeout=timeout, proxies=proxies)
                res.raise_for_status()
                return res.text
            except requests.RequestException as e:
                last_err = e
                if attempt >= retries:
                    break
                time.sleep(backoff ** attempt)
        if last_err:
            raise last_err
        return ""


  
# AUTO-DETECT COMMON FIELDS
def auto_detect_common_fields(html):
    soup = BeautifulSoup(html, 'html.parser')

    def get_selector(elem):
        path = []
        while elem and elem.name != '[document]':
            sel = elem.name
            if 'class' in elem.attrs:
                sel += '.' + '.'.join(elem.attrs['class'])
            path.insert(0, sel)
            elem = elem.parent
        return ' > '.join(path)

    fields = {}
    title_elem = soup.find(['h1', 'h2', 'h3'])
    if title_elem:
        fields["title"] = get_selector(title_elem)

    price_elem = soup.find(string=re.compile(r'[\$£€]\s*\d+'))
    if price_elem:
        fields["price"] = get_selector(price_elem.parent)

    link_elem = soup.find('a', href=True)
    if link_elem:
        fields["link"] = get_selector(link_elem)

    img_elem = soup.find('img', src=True)
    if img_elem:
        fields["image_url"] = get_selector(img_elem)

    return fields


  
# AUTO-DISCOVER MODE
def auto_discover_items(html):
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.select("table tr")
    if len(rows) > 1:
        headers = [th.get_text(strip=True) or f"col_{i}" for i, th in enumerate(rows[0].select("th"))]
        return [dict(zip(headers, [td.get_text(strip=True) for td in tr.select("td")])) for tr in rows[1:]]

    items = []
    for block in soup.find_all(["li", "article", "div"], recursive=True):
        text = block.get_text(strip=True)
        if text and len(text) > 5:
            entry = {"content": text}
            img = block.find('img', src=True)
            if img:
                entry["image_url"] = img["src"]
            link = block.find('a', href=True)
            if link:
                entry["link"] = link["href"]
            items.append(entry)
    return items


  
# MANUAL FIELDS MODE
def parse_with_fields(html, fields):
    if not fields:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    base_elems = soup.select(list(fields.values())[0])
    results = []

    elems_by_field = {fname: soup.select(selector) for fname, selector in fields.items()}

    for idx in range(len(base_elems)):
        record = {}
        for fname, selector in fields.items():
            elems = elems_by_field.get(fname, [])
            if idx < len(elems):
                elem = elems[idx]
                if fname == 'link' and elem.has_attr('href'):
                    record[fname] = elem['href']
                elif fname == 'image_url' and elem.has_attr('src'):
                    record[fname] = elem['src']
                else:
                    record[fname] = elem.get_text(strip=True)
            else:
                record[fname] = None
        results.append(record)
    return results


  
# MAIN SCRAPER
def scrape_site(base_url, fields=None, next_selector=None, use_selenium=False,
                scrape_all=False, max_pages=1, auto_mode=False,
                infinite_scroll=False, load_more_selector=None, use_tor=False,
                delay_range: Tuple[float, float] = (1, 2),
                progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
                normalize_urls: bool = True,
                request_timeout: int = 20,
                request_retries: int = 2,
                request_backoff: float = 1.5):

    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Mozilla/5.0 (X11; Linux x86_64)"
    ]
    all_data, seen_urls = [], set()
    page_url = base_url
    page_count = 0

    while True:
        page_count += 1
        if not scrape_all and page_count > max_pages:
            break

        html = fetch_html(
            page_url,
            use_selenium,
            ua_list,
            infinite_scroll,
            load_more_selector,
            use_tor=use_tor,
            timeout=request_timeout,
            retries=request_retries,
            backoff=request_backoff,
        )
        items = auto_discover_items(html) if auto_mode else parse_with_fields(html, fields)
        if not items:
            break

        for item in items:
            item["source_url"] = page_url
            if normalize_urls:
                if "link" in item and item["link"]:
                    item["link"] = urljoin(page_url, item["link"])
                if "image_url" in item and item["image_url"]:
                    item["image_url"] = urljoin(page_url, item["image_url"])
        all_data.extend(items)

        if progress_callback:
            total = None if scrape_all else max_pages
            progress_callback(page_count, total)

        soup = BeautifulSoup(html, 'html.parser')
        if not next_selector:
            for sel in ["a.next", "a[rel='next']", "li.next a", ".pagination-next a", "a.next.page-numbers"]:
                if soup.select_one(sel):
                    next_selector = sel
                    break

        if next_selector:
            if use_selenium:
                from selenium.webdriver.common.by import By
                driver_opts = Options()
                driver_opts.add_argument("--headless=new")
                driver_opts.add_argument("--disable-gpu")
                driver_opts.add_argument("--no-sandbox")
                driver = webdriver.Chrome(options=driver_opts)
                try:
                    driver.get(page_url)
                    next_el = driver.find_element(By.CSS_SELECTOR, next_selector)
                    href = next_el.get_attribute("href")
                    if href:
                        page_url = urljoin(page_url, href)
                    else:
                        next_el.click()
                        time.sleep(2)
                        page_url = driver.current_url
                except:
                    driver.quit()
                    break
                driver.quit()
            else:
                next_btn = soup.select_one(next_selector)
                if next_btn and next_btn.get("href"):
                    next_url = urljoin(page_url, next_btn["href"])
                    if next_url in seen_urls:
                        break
                    seen_urls.add(next_url)
                    page_url = next_url
                else:
                    break
        else:
            break

        if delay_range and delay_range[1] > 0:
            time.sleep(random.uniform(delay_range[0], delay_range[1]))

    return clean_data(all_data)


  
# DATA CLEAN & SAVE
def clean_data(data):
    seen, cleaned = set(), []
    for row in data:
        t = tuple(sorted(row.items()))
        if t not in seen:
            seen.add(t)
            cleaned.append({k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return cleaned

def save_data(data, filename_base, formats: Optional[Iterable[str]] = None):
    if not data:
        return []
    formats = {f.lower() for f in (formats or ["csv", "xlsx", "json"])}
    saved = []
    df = None
    if "csv" in formats or "xlsx" in formats:
        df = pd.DataFrame(data)
    if "csv" in formats:
        df.to_csv(filename_base + ".csv", index=False)
        saved.append(filename_base + ".csv")
    if "xlsx" in formats:
        df.to_excel(filename_base + ".xlsx", index=False)
        saved.append(filename_base + ".xlsx")
    if "json" in formats:
        with open(filename_base + ".json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        saved.append(filename_base + ".json")
    return saved
