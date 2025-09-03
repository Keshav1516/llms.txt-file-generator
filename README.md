# LLMs.txt Generator for GEO & SEO 🌐
--------------------------------
A **Streamlit web app** that automatically generates an LLMs.txt file for any website. The app fetches the homepage content, pages, and blog posts, then organizes them into a structured format suitable for SEO and content analysis.

## Features
-------------
- Automatically fetches **introductory text** from a website's homepage or About Us section.
- Extracts **page and blog URLs** along with titles and meta descriptions.
- Generates a structured **LLMs.txt** file in the following format:
- Provides a **download button** to save the LLMs.txt file directly.
- Supports websites with or without a sitemap.xml.

## Installation
1. Clone the repository:
```bash
git clone https://github.com/your-username/llms-generator.git
cd llms-generator

## Usage
----------
Run the Streamlit app:
- streamlit run app.py
- Enter the website domain (e.g., paytm.com) in the input box.
- Click Generate LLMs.txt.

Preview the content and click Download to save the file.

## Requirements
-----------------
- Python 3.9+
- Streamlit
- Requests
- BeautifulSoup4
- lxml
