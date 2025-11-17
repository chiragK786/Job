import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def download_file(url, folder, prefix):
    """Helper function to download any file from a URL"""
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        os.makedirs(folder, exist_ok=True)
        filename = os.path.basename(urlparse(url).path) or f"{prefix}.bin"

        filepath = os.path.join(folder, filename)

        with open(filepath, "wb") as f:
            f.write(response.content)

        print(f"✅ Saved {url} -> {filepath}")
    except Exception as e:
        print(f"❌ Could not download {url}: {e}")


def scrape_website(url):
    try:
        # Send HTTP request
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Website title
        title = soup.title.string if soup.title else "No title found"

        # Meta description
        description = soup.find("meta", attrs={"name": "description"})
        description = description["content"] if description else "No description found"

        # Meta keywords
        keywords = soup.find("meta", attrs={"name": "keywords"})
        keywords = keywords["content"] if keywords else "No keywords found"

        # All links
        links = [urljoin(url, a["href"]) for a in soup.find_all("a", href=True)]

        # All headings
        headings = {f"H{i}": [h.get_text(strip=True) for h in soup.find_all(f"h{i}")]
                    for i in range(1, 7)}

        # Print results
        print("🔹 Website Title:", title)
        print("🔹 Description:", description)
        print("🔹 Keywords:", keywords)
        print("🔹 Total Links Found:", len(links))
        print("🔹 Sample Links:", links[:10])
        print("🔹 Headings:", headings)

        # ---------- Download Files ----------
        # 1. Images
        print("\n📥 Downloading Images...")
        for img in soup.find_all("img", src=True):
            img_url = urljoin(url, img["src"])
            download_file(img_url, "downloaded_images", "image")

        # 2. PDFs
        print("\n📥 Downloading PDFs...")
        for link in links:
            if link.lower().endswith(".pdf"):
                download_file(link, "downloaded_pdfs", "file")

        # 3. CSS files
        print("\n📥 Downloading CSS files...")
        for css in soup.find_all("link", rel="stylesheet"):
            css_url = urljoin(url, css["href"])
            download_file(css_url, "downloaded_css", "style")

        # 4. JS files
        print("\n📥 Downloading JS files...")
        for script in soup.find_all("script", src=True):
            js_url = urljoin(url, script["src"])
            download_file(js_url, "downloaded_js", "script")

    except Exception as e:
        print("❌ Error:", e)


# Example usage
scrape_website("https://www.squareboat.com")
