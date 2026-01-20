import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
from urllib.parse import urljoin, urlparse

# ---------------- CONFIG ---------------- #

COMMON_SITEMAP_PATHS = [
    "sitemap.xml",
    "sitemap_index.xml",
    "sitemap1.xml",
    "page-sitemap.xml",
    "post-sitemap.xml",
    "blog-sitemap.xml"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

# ---------------- HELPERS ---------------- #

def normalize_domain(domain):
    domain = domain.strip().lower()
    domain = domain.replace("https://", "").replace("http://", "")
    return domain.rstrip("/")

def safe_get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        return r.text
    except Exception as e:
        st.warning(f"❌ Failed to fetch: {url}")
        return None

# ---------------- SCRAPING ---------------- #

def fetch_title_desc(url):
    html = safe_get(url)
    if not html:
        return url, "Description unavailable."

    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title else url
    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc = desc_tag["content"].strip() if desc_tag else "No meta description found."

    return title, desc

def fetch_intro_text(url):
    html = safe_get(url)
    if not html:
        return "No introduction available."

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all("p")

    intro = ""
    for p in paragraphs:
        text = p.get_text().strip()
        if len(text) > 60:
            intro += text + "\n\n"
        if len(intro.split()) > 120:
            break

    return intro.strip() if intro else "No introduction available."

# ---------------- SITEMAP ---------------- #

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

    except Exception:
        pass

    return []

def find_sitemap(domain):
    base = f"https://{domain}"
    for path in COMMON_SITEMAP_PATHS:
        sitemap_url = f"{base}/{path}"
        urls = get_urls_from_sitemap(sitemap_url)
        if urls:
            st.success(f"✅ Sitemap found: {sitemap_url}")
            return urls

    st.warning("⚠️ No sitemap found.")
    return []

# ---------------- FALLBACK CRAWL ---------------- #

def crawl_homepage(domain):
    base_url = f"https://{domain}"
    html = safe_get(base_url)

    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)

        if urlparse(full_url).netloc == domain:
            links.add(full_url)

    return list(links)

# ---------------- MAIN GENERATOR ---------------- #

def generate_llms(domain):
    content = []
    domain_clean = domain.replace("www.", "")

    content.append(f"# {domain_clean.capitalize()}\n")

    intro = fetch_intro_text(f"https://{domain}")
    content.append(intro + "\n")

    urls = find_sitemap(domain)

    if not urls:
        st.info("🔁 Falling back to homepage crawling...")
        urls = crawl_homepage(domain)

    if not urls:
        content.append(
            "\n⚠️ This website blocks bots or loads content via JavaScript.\n"
            "No crawlable URLs were found.\n"
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

        st.text_area("Generated LLMs.txt", output, height=420)

        st.download_button(
            "📥 Download LLMs.txt",
            data=output,
            file_name="llms.txt",
            mime="text/plain"
        )

        st.success("✅ LLMs.txt generated successfully")

    else:
        st.error("❗ Please enter a valid domain.")
