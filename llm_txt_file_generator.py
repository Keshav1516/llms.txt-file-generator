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
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0 Safari/537.36"
    )
}

# ---------------- UTILITIES ---------------- #

def normalize_domain(domain):
    domain = domain.lower().strip()
    domain = domain.replace("https://", "").replace("http://", "")
    return domain.rstrip("/")

def is_bot_blocked(html):
    signals = [
        "cf-challenge",
        "captcha",
        "verify you are human",
        "access denied",
        "cloudflare"
    ]
    return any(signal in html.lower() for signal in signals)

# ---------------- FETCH METHODS ---------------- #

def fetch_requests(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        return r.text
    except:
        return None

def fetch_playwright(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="networkidle", timeout=25000)
            html = page.content()
            browser.close()
            return html
    except:
        return None

def smart_fetch(url):
    html = fetch_requests(url)
    if html and not is_bot_blocked(html) and len(html) > 2000:
        return html

    st.info("🔁 JS rendering enabled (Playwright)...")
    return fetch_playwright(url)

# ---------------- CONTENT EXTRACTION ---------------- #

def fetch_title_desc(url):
    html = smart_fetch(url)
    if not html:
        return url, "Description unavailable."

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title else url

    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc = desc_tag["content"].strip() if desc_tag else "No meta description found."

    return title, desc

def fetch_intro_text(url):
    html = smart_fetch(url)
    if not html:
        return "No introduction available."

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all("p")

    intro = ""
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 60:
            intro += text + "\n\n"
        if len(intro.split()) > 120:
            break

    return intro.strip() if intro else "No introduction available."

# ---------------- SITEMAP HANDLING ---------------- #

def get_urls_from_sitemap(sitemap_url):
    try:
        r = requests.get(sitemap_url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "xml")

        if soup.find("urlset"):
            return [loc.text.strip() for loc in soup.find_all("loc")]

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
            line.split(":")[1].strip()
            for line in txt.splitlines()
            if line.lower().startswith("sitemap")
        ]
    except:
        return []

def find_sitemap(domain):
    base = f"https://{domain}"

    # robots.txt sitemap
    for sm in sitemap_from_robots(domain):
        urls = get_urls_from_sitemap(sm)
        if urls:
            st.success(f"✅ Sitemap found via robots.txt")
            return urls

    # common paths
    for path in COMMON_SITEMAP_PATHS:
        sm_url = f"{base}/{path}"
        urls = get_urls_from_sitemap(sm_url)
        if urls:
            st.success(f"✅ Sitemap found: {sm_url}")
            return urls

    st.warning("⚠️ No sitemap found.")
    return []

# ---------------- FALLBACK CRAWLING ---------------- #

def crawl_homepage(domain):
    base_url = f"https://{domain}"
    html = smart_fetch(base_url)

    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for a in soup.find_all("a", href=True):
        full_url = urljoin(base_url, a["href"])
        if urlparse(full_url).netloc == domain:
            links.add(full_url)

    return list(links)

# ---------------- MAIN GENERATOR ---------------- #

def generate_llms(domain):
    content = []
    domain_name = domain.replace("www.", "")

    content.append(f"# {domain_name.capitalize()}\n")

    intro = fetch_intro_text(f"https://{domain}")
    content.append(intro + "\n")

    urls = find_sitemap(domain)

    if not urls:
        st.info("🔍 Falling back to homepage crawl...")
        urls = crawl_homepage(domain)

    if not urls:
        content.append(
            "⚠️ This website blocks automated crawling or relies heavily on JavaScript.\n"
            "Only limited public information could be extracted.\n"
        )

    pages = [u for u in urls if not any(x in u for x in ["/blog", "/post", "/category"])]
    blogs = [u for u in urls if any(x in u for x in ["/blog", "/post"])]

    content.append("\n## Pages\n")
    if pages:
        for url in pages[:10]:
            title, desc = fetch_title_desc(url)
            content.append(f"- [{title}]({url}): {desc}")
    else:
        content.append("- No pages found.")

    content.append("\n## Blogs\n")
    if blogs:
        for url in blogs[:10]:
            title, desc = fetch_title_desc(url)
            content.append(f"- [{title}]({url}): {desc}")
    else:
        content.append("- No blogs found.")

    content.append(f"\n_Last updated: {datetime.date.today()}_\n")

    return "\n".join(content)

# ---------------- STREAMLIT UI ---------------- #

st.set_page_config(page_title="LLMs.txt Generator", layout="centered")
st.title("🧠 LLMs.txt Generator for SEO")

domain_input = st.text_input("Enter Website Domain (example: servitiumcrm.com)")

if st.button("Generate LLMs.txt"):
    if domain_input:
        domain = normalize_domain(domain_input)

        with st.spinner("Generating LLMs.txt..."):
            output = generate_llms(domain)

        st.text_area("Generated LLMs.txt", output, height=450)

        st.download_button(
            "📥 Download LLMs.txt",
            data=output,
            file_name="llms.txt",
            mime="text/plain"
        )

        st.success("✅ LLMs.txt generated successfully")
    else:
        st.error("❗ Please enter a valid domain.")
