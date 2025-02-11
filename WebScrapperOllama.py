import cloudscraper
from bs4 import BeautifulSoup
import ollama

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from playwright.sync_api import sync_playwright

OLLAMA_API = "http://localhost:11434/api/chat"
model = "llama3.2"

class Website:
    def __init__(self, url):
        """
        Tries to scrape a website using cloudscraper.
        Falls back to Playwright or Selenium if necessary.
        """
        self.url = url
        self.title = "No title found!"
        self.text = ""

        # Use cloudscraper to bypass Cloudflare protection
        scraper = cloudscraper.create_scraper()
        try:
            response = scraper.get(url, timeout=10)
            response.raise_for_status()  # Check for successful response
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            self.title = soup.title.string if soup.title else "No title found!"

            # Remove unnecessary elements
            for irrelevant in soup.body(["script", "style", "img", "input"]):
                irrelevant.decompose()

            self.text = soup.body.get_text(separator="\n", strip=True)

            # If text is empty, fall back to Playwright
            if not self.text.strip():
                print(f"No content extracted from {url}. Falling back to Playwright...")
                self.scrape_with_playwright()

        except (requests.RequestException, Exception) as e:
            print(f"Cloudscraper failed for {url}: {e}")
            self.scrape_with_playwright()

    def scrape_with_playwright(self):
        """
        Uses Playwright to extract JavaScript-rendered content.
        Falls back to Selenium if it fails.
        """
        print(f"Using Playwright to scrape {self.url}...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.url, wait_until="networkidle")

                self.title = page.title() or "No title found!"
                soup = BeautifulSoup(page.content(), 'html.parser')

                # Remove unnecessary elements
                for irrelevant in soup(["script", "style", "img", "input"]):
                    irrelevant.decompose()

                self.text = soup.get_text(separator="\n", strip=True)

                browser.close()

        except Exception as e:
            print(f"Playwright failed for {self.url}: {e}")
            self.scrape_with_selenium()

    def scrape_with_selenium(self):
        """
        Uses Selenium to extract JavaScript-rendered content.
        """
        print(f"Using Selenium to scrape {self.url}...")

        options = Options()
        options.add_argument("--headless")  # Run without opening browser
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            driver.get(self.url)
            driver.implicitly_wait(15)

            self.title = driver.title or "No title found!"
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Remove unnecessary elements
            for irrelevant in soup(["script", "style", "img", "input"]):
                irrelevant.decompose()

            self.text = soup.get_text(separator="\n", strip=True)

        except Exception as e:
            print(f"Failed to scrape {self.url} with Selenium: {e}")
        finally:
            driver.quit()  # Ensure browser is closed

# System prompt for LLM
system_prompt = ("You are an assistant analyzing the contents of a website. "
                 "Provide a short summary, ignoring navigation-related text. "
                 "Format your response in markdown.")

def user_prompt_for(website):
    """
    Creates the user prompt that includes website title and content.
    """
    return f"""You are looking at a website titled **{website.title}**.

The contents of this website are as follows:
{website.text}

Please summarize this website in important and valuable information. If it includes news or announcements, summarize those too.
"""

def messages_for(website):
    """
    Returns the message list for Ollama chat completion.
    """
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_for(website)}
    ]

def summarizer(url, model):
    """
    Fetches the website content and generates a summary using Ollama.
    """
    website = Website(url)
    if website.text:
        response = ollama.chat(model=model, messages=messages_for(website))
        return response['message']['content']
    else:
        return "Failed to fetch website content."

# Test with JavaScript-heavy website
summary = summarizer("https://smest.in/", model)
print(summary)  # Display as Markdown in Jupyter Notebook
