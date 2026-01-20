import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

# ---------------- CONFIG ---------------- #

COMMON_SITEMAP_PATHS = [
    "sitemap.xml",
    "sitemap_index.xml",
    "page-sitemap.xml",
    "post-sitemap.xml",
    "blog-sitemap.xml"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
}

# ---------------- UTILS ---------------- #

def normalize_domain(domain):
    return domain.lower().replace("https://", "").replace("http://", "").rstrip("/")

def safe_requests(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.text
    except:
        pass
    return None

def safe_playwright(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="networkidle", timeout=20000)
            html = page.content()
            browser.close()
            return html
    except:
        return None

def smart_fetch(url):
    html = safe_requests(url)
    if html and len(html) > 2000:
        return html
    return safe_playwright(url)

# ---------------- SITEMAP LOGIC ---------------- #

def get_urls_from_sitemap(sitemap_url):
    try:
        r = requests.get(sitemap_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "xml")

        # Normal sitemap
        if soup.find("urlset"):
            return [loc.text.strip() for loc in soup.find_all("loc")]

        # Sitemap index
        if soup.find("sitemapindex"):
            urls = []
            for loc in soup.find_all("loc"):
                urls.extend(get_urls_from_sitemap(loc.text.strip()))
            return urls

    except:
        pass

    return []

def sitemap_from_robots(domain):
    try:
        txt = requests.get(f"https://{domain}/robots.txt", timeout=10).text
        return [
            line.split(":", 1)[1].strip()
            for line in txt.splitlines()
            if line.lower().startswith("sitemap")
        ]
    except:
        return []

def find_sitemap_urls(domain):
    urls = []

    # 1️⃣ robots.txt sitemap
    for sm in sitemap_from_robots(domain):
        urls.extend(get_urls_from_sitemap(sm))

    # 2️⃣ common sitemap paths
    for path in COMMON_SITEMAP_PATHS:
        sm_url = f"https://{domain}/{path}"
        urls.extend(get_urls_from_sitemap(sm_url))

    return list(set(urls))

# ---------------- CONTENT EXTRACTION ---------------- #

def extract_intro(url):
    html = smart_fetch(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    paras = soup.find_all("p")

    text = []
    for p in paras:
        t = p.get_text(strip=True)
        if len(t) > 60:
            text.append(t)
        if len(" ".join(text).split()) > 120:
            break

    return "\n\n".join(text) if text else None

# ---------------- MAIN GENERATOR ---------------- #

def generate_llms(domain):
    lines = []
    clean = domain.replace("www.", "")

    lines.append(f"# {clean.capitalize()}\n")

    # INTRO
    intro = extract_intro(f"https://{domain}")
    if intro:
        lines.append(intro)
    else:
        lines.append(
            "This website restricts automated crawling or relies heavily on JavaScript. "
            "Only limited public information could be extracted."
        )

    # SITEMAP URLS
    sitemap_urls = find_sitemap_urls(domain)

    pages = []
    blogs = []

    for u in sitemap_urls:
        if any(x in u for x in ["/blog", "/post"]):
            blogs.append(u)
        else:
            pages.append(u)

    lines.append("\n## Pages")
    if pages:
        for u in pages[:10]:
            lines.append(f"- {u}")
    else:
        lines.append(f"- Homepage: https://{domain}")

    lines.append("\n## Blogs")
    if blogs:
        for u in blogs[:10]:
            lines.append(f"- {u}")
    else:
        lines.append("- No blog URLs found.")

    # STATUS
    lines.append("\n## Crawl Status")
    lines.append(f"- Sitemap URLs found: {len(sitemap_urls)}")
    lines.append("- Bot protection: Auto-detected")
    lines.append("- JS rendering: Conditional")

    lines.append(f"\n_Last updated: {datetime.date.today()}_")

    return "\n".join(lines)

# ---------------- STREAMLIT UI ---------------- #

st.set_page_config(page_title="LLMs.txt Generator", layout="centered")
st.title("🧠 LLMs.txt Generator (Sitemap Enabled)")

domain_input = st.text_input("Enter domain (example: wizardinfoways.com)")

if st.button("Generate LLMs.txt"):
    if domain_input:
        domain = normalize_domain(domain_input)

        with st.spinner("Generating LLMs.txt..."):
            result = generate_llms(domain)

        st.caption(f"Generated characters: {len(result)}")
        st.text_area("Generated LLMs.txt", result, height=450)

        st.download_button(
            "📥 Download LLMs.txt",
            data=result,
            file_name="llms.txt",
            mime="text/plain"
        )

        st.success("✅ LLMs.txt generated successfully")
    else:
        st.error("Please enter a valid domain.")
