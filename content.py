from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

import time

def get_udemy_course_content(course_url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # run in background
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # Path to your chromedriver executable
    # service = Service('/path/to/chromedriver')  # <-- CHANGE THIS!

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(course_url)
    time.sleep(3)  # wait for page to load

    # Get course title
    try:
        course_title = driver.find_element(By.CSS_SELECTOR, "h1[data-purpose='lead-title']").text
    except:
        course_title = "N/A"

    # Get course description
    try:
        description = driver.find_element(By.CSS_SELECTOR, "div[data-purpose='safely-set-inner-html:course-landing-page/description']").text
    except:
        description = "N/A"

    sections = driver.find_elements(By.CSS_SELECTOR, "div.section--section--BukKG")
    curriculum = []
    for section in sections:
        try:
            section_title = section.find_element(By.TAG_NAME, "h3").text
        except:
            section_title = "Section"

        lectures = []
        for li in section.find_elements(By.CSS_SELECTOR, "li.lecture-item"):
            lectures.append(li.text)
        curriculum.append({
            "section": section_title,
            "lectures": lectures
        })

    driver.quit()

    return {
        "title": course_title,
        "description": description,
        "curriculum": curriculum
    }

if __name__ == "__main__":
    # Replace with your target course URL
    url = "https://www.udemy.com/course/sdet-interview-preparation/"
    content = get_udemy_course_content(url)
    print("Title:", content["title"])
    print("Description:", content["description"])
    print("Curriculum:")
    for section in content["curriculum"]:
        print(f'- {section["section"]}:')
        for lecture in section["lectures"]:
            print(f'  - {lecture}')