import requests
from bs4 import BeautifulSoup
from spellchecker import SpellChecker
import csv
import re

def sanitize_filename(name: str) -> str:
    """Clean title text so it can be safely used as filename"""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

def extract_visible_text(soup):
    """Extract visible text from HTML (ignores scripts, styles, etc.)"""
    for script in soup(["script", "style", "noscript"]):
        script.decompose()
    return " ".join(soup.stripped_strings)

def safe_suggestions(spell, word):
    """Return suggestions safely (avoid join errors)"""
    try:
        candidates = spell.candidates(word)
        if candidates:
            return ", ".join(str(c) for c in candidates)
        return "No suggestions"
    except:
        return "No suggestions"

def check_spelling(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"❌ Failed to access {url}, status code: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        page_title = soup.title.string.strip() if soup.title else "No_Title"
        safe_title = sanitize_filename(page_title)
        output_file = f"spell_check_{safe_title}.csv"

        spell = SpellChecker()
        results = []

        # 1. Visible text
        visible_text = extract_visible_text(soup)
        words = re.findall(r"\b[a-zA-Z]+\b", visible_text)
        for word in spell.unknown(words):
            results.append([page_title, "Visible Text", word, safe_suggestions(spell, word)])

        # 2. Placeholders
        for inp in soup.find_all("input", placeholder=True):
            text = inp.get("placeholder")
            for word in spell.unknown(re.findall(r"\b[a-zA-Z]+\b", text)):
                results.append([page_title, "Placeholder", word, safe_suggestions(spell, word)])

        # 3. Alt texts
        for img in soup.find_all("img", alt=True):
            text = img.get("alt")
            for word in spell.unknown(re.findall(r"\b[a-zA-Z]+\b", text)):
                results.append([page_title, "Alt Text", word, safe_suggestions(spell, word)])

        # 4. Title attributes
        for tag in soup.find_all(title=True):
            text = tag.get("title")
            for word in spell.unknown(re.findall(r"\b[a-zA-Z]+\b", text)):
                results.append([page_title, "Title Attribute", word, safe_suggestions(spell, word)])

        # 5. Button & Link text
        for btn in soup.find_all(["button", "a"]):
            text = btn.get_text(strip=True)
            for word in spell.unknown(re.findall(r"\b[a-zA-Z]+\b", text)):
                results.append([page_title, "Button/Link Text", word, safe_suggestions(spell, word)])

        # Save results to CSV
        with open(output_file, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Page Name", "Section", "Misspelled Word", "Suggestions"])
            writer.writerows(results)

        print(f"✅ Spell check report saved to {output_file}")

    except Exception as e:
        print(f"❌ Error while processing {url}: {e}")

if __name__ == "__main__":
    url = "https://squareboat:squareboat@squareboat2.squareboat.info/crewmate/hire-reactjs-developers"
    check_spelling(url)
