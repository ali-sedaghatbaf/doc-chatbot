import ast
import base64
import os
import re
from difflib import SequenceMatcher
from hashlib import md5
from typing import List

import pandas as pd
import pymupdf as fitz
from bs4 import BeautifulSoup
from klarna_wiki_api.sessions import KlarnaWikiSession
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sklearn.feature_extraction.text import TfidfVectorizer


def encode_md5(text):
    return md5(text.encode("utf-8")).hexdigest()


def calculate_tfidf_matrix(corpus, words):

    vectorizer = TfidfVectorizer(vocabulary=set(words), lowercase=False)
    tfidf_matrix = vectorizer.fit_transform(corpus)

    # Convert the result to a DataFrame for better readability
    df = pd.DataFrame(
        tfidf_matrix.toarray(), columns=vectorizer.get_feature_names_out()
    )
    return df.to_dict(orient="records")


def highlight_text_in_pdf(pdf_path, output_path, page_number, rect):

    doc = fitz.open(pdf_path)

    page = doc[page_number]

    page.add_highlight_annot(fitz.Rect(*rect))

    doc.save(output_path)
    doc.close()


def pdf_to_image(pdf_path: str) -> List[bytes]:
    images = []
    with fitz.open(pdf_path) as doc:
        for page_ind, page in enumerate(doc):
            pix = page.get_pixmap()
            png_data = pix.tobytes("png")

            images.append(png_data)

    return images


def webpage_to_image(url: str, width: int = 1920) -> List[bytes]:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    with webdriver.Chrome(options=chrome_options) as driver:
        driver.get(url)

        # Set window width
        driver.set_window_size(width, 1080)

        # Get page dimensions
        total_height = driver.execute_script("return document.body.scrollHeight")

        # Take full page screenshot
        driver.set_window_size(width, total_height)
        screenshot = driver.get_screenshot_as_png()

        return [screenshot]


def image_to_base64(image_data: bytes) -> str:
    return base64.b64encode(image_data).decode("utf-8")


def wiki_page_to_image(
    url: str, width: int = 1920, max_height: int = 15000
) -> List[bytes]:
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--window-size={width},1080")

    with KlarnaWikiSession(
        username=os.environ["KLARNA_WIKI_USERNAME"],
        password=os.environ["KLARNA_WIKI_PASSWORD"],
        use_production=False,
        use_bot_login=True,
    ) as session:
        cookies = session.get_cookies()

        # Initialize driver
        driver = webdriver.Chrome(options=chrome_options)

        # Add authentication cookies

        for cookie in cookies:
            driver.add_cookie(
                {"name": cookie.name, "value": cookie.value, "domain": cookie.domain}
            )

        # Navigate to the page
        driver.get(url)

        # Wait for content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "main-content"))
        )

        # Get page dimensions
        total_height = min(
            driver.execute_script("return document.body.scrollHeight"), max_height
        )

        # Set final window size
        driver.set_window_size(width, total_height)

        # Wait for any dynamic content
        driver.implicitly_wait(2)

        # Take screenshot
        screenshot = driver.get_screenshot_as_png()
        with open("screenshot.png", "wb") as f:
            f.write(screenshot)
        return [screenshot]


def get_xpath(element) -> str:
    """Helper function to get xpath of an element"""
    components = []
    child = element
    for parent in element.parents:
        siblings = parent.find_all(child.name, recursive=False)
        components.append(
            child.name
            if siblings == [child]
            else f"{child.name}[{siblings.index(child) + 1}]"
        )
        child = parent
    components.reverse()
    return "/" + "/".join(components)


def search_text_in_pdf(pdf_path, search_text):
    window_size = max(len(search_text), 200)
    clean_markdown = re.sub(r"[#`*_\[\](){}|<>\n]+", " ", search_text).strip()

    doc = fitz.open(pdf_path)
    best_match = None
    best_score = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        current_text = page.get_text()

        # Add text from next page if available
        next_page_text = ""
        if page_num < len(doc) - 1:
            next_page = doc[page_num + 1]
            next_page_text = next_page.get_text()
            current_text += " " + next_page_text

        words = current_text.split()
        for i in range(len(words) - window_size):
            window_text = " ".join(words[i : i + window_size])
            score = SequenceMatcher(None, clean_markdown, window_text).ratio()

            if score > best_score:
                # Find first and last words of the matching window
                first_word = words[i]
                last_word = words[i + window_size - 1]

                # Check if text spans across pages
                first_page_results = page.search_for(first_word)
                if first_page_results:
                    start_rect = first_page_results[0]
                    # If last word is on same page
                    last_word_current = page.search_for(last_word)
                    if last_word_current:
                        end_rect = last_word_current[-1]
                        best_match = {
                            "start": (page_num, start_rect.x0, start_rect.y0),
                            "end": (page_num, end_rect.x1, end_rect.y1),
                        }
                    # If last word is on next page
                    elif page_num < len(doc) - 1:
                        next_page = doc[page_num + 1]
                        last_word_next = next_page.search_for(last_word)
                        if last_word_next:
                            end_rect = last_word_next[-1]
                            best_match = {
                                "start": (page_num, start_rect.x0, start_rect.y0),
                                "end": (page_num + 1, end_rect.x1, end_rect.y1),
                            }
                best_score = score

    doc.close()
    return best_match


def search_text_in_webpage(url, search_text):
    clean_markdown = re.sub(r"[#`*_\[\](){}|<>\n]+", " ", search_text).strip()

    # Setup Selenium
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    best_match = None

    # Get all text elements
    text_elements = driver.find_elements(
        By.XPATH, "//*[not(self::script)][not(self::style)]/text()[normalize-space()]"
    )

    for element in text_elements:
        text = element.text.strip()
        if not text:
            continue

        score = SequenceMatcher(None, clean_markdown, text).ratio()

        if score > best_match["score"]:
            # Get element location and size
            location = element.location
            size = element.size

            best_match = {
                "start": (0, location["x"], location["y"]),
                "end": (
                    0,
                    location["x"] + size["width"],
                    location["y"] + size["height"],
                ),
            }

    driver.quit()
    return best_match


def parse_function(input_str):
    # Regular expression to capture the function name and arguments
    pattern = r"(\w+)(?:\((.*)\))?"

    match = re.match(pattern, input_str)
    if match:
        function_name = match.group(1)  # Extract the function name
        raw_arguments = match.group(2)  # Extract the arguments as a string
        # If there are arguments, attempt to parse them
        arguments = []
        if raw_arguments:
            try:
                # Use ast.literal_eval to safely evaluate and convert the arguments
                parsed_args = ast.literal_eval(
                    f"({raw_arguments})"
                )  # Wrap in tuple parentheses
                # Ensure it's always treated as a tuple even with a single argument
                arguments = (
                    list(parsed_args)
                    if isinstance(parsed_args, tuple)
                    else [parsed_args]
                )
            except (ValueError, SyntaxError):
                # In case of failure to parse, return the raw argument string
                arguments = [raw_arguments.strip()]

        return {"function_name": function_name, "arguments": arguments}
    else:
        return None


def json_to_md(data, level=0):
    """
    Convert JSON/dict data to markdown format.

    Args:
        data: JSON/dict data to convert
        level: Current indentation level (default: 0)

    Returns:
        str: Markdown formatted string
    """
    indent = "  " * level
    md = ""

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                md += f"{indent}- **{key}:**\n{json_to_md(value, level + 1)}"
            else:
                md += f"{indent}- **{key}:** {value}\n"

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                md += f"{indent}- \n{json_to_md(item, level + 1)}"
            else:
                md += f"{indent}- {item}\n"

    else:
        md += f"{indent}{data}\n"

    return md


def html_to_md(html_content: str) -> str:
    """
    Convert HTML content to Markdown format.

    Args:
        html_content: HTML string to convert

    Returns:
        str: Markdown formatted string
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Handle headings
    for i in range(6, 0, -1):
        for heading in soup.find_all(f"h{i}"):
            heading.replace_with(f"{'#' * i} {heading.get_text()}\n")

    # Handle links
    for link in soup.find_all("a"):
        href = link.get("href", "")
        text = link.get_text()
        link.replace_with(f"[{text}]({href})")

    # Handle images
    for img in soup.find_all("img"):
        alt = img.get("alt", "")
        src = img.get("src", "")
        img.replace_with(f"![{alt}]({src})")

    # Handle lists
    for ul in soup.find_all("ul"):
        for li in ul.find_all("li"):
            li.replace_with(f"- {li.get_text()}\n")

    for ol in soup.find_all("ol"):
        for i, li in enumerate(ol.find_all("li"), 1):
            li.replace_with(f"{i}. {li.get_text()}\n")

    # Handle emphasis
    for strong in soup.find_all(["strong", "b"]):
        strong.replace_with(f"**{strong.get_text()}**")

    for em in soup.find_all(["em", "i"]):
        em.replace_with(f"*{em.get_text()}*")

    # Handle code blocks
    for pre in soup.find_all("pre"):
        code = pre.find("code")
        if code:
            lang = (
                code.get("class", [""])[0].replace("language-", "")
                if code.get("class")
                else ""
            )
            pre.replace_with(f"```{lang}\n{code.get_text()}\n```\n")

    # Handle inline code
    for code in soup.find_all("code"):
        if code.parent.name != "pre":
            code.replace_with(f"`{code.get_text()}`")

    # Handle blockquotes
    for quote in soup.find_all("blockquote"):
        lines = quote.get_text().strip().split("\n")
        quote.replace_with("> " + "\n> ".join(lines) + "\n")

    # Handle tables
    for table in soup.find_all("table"):
        md_table = []
        # Headers
        headers = []
        for th in table.find_all("th"):
            headers.append(th.get_text().strip())
        if headers:
            md_table.append("| " + " | ".join(headers) + " |")
            md_table.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Rows
        for tr in table.find_all("tr"):
            cells = []
            for td in tr.find_all("td"):
                cells.append(td.get_text().strip())
            if cells:
                md_table.append("| " + " | ".join(cells) + " |")

        table.replace_with("\n".join(md_table) + "\n")

    # Get the text and clean it up
    text = soup.get_text()

    # Clean up extra whitespace
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r" +", " ", text)

    return text.strip()


def compare_header_levels(header1: str, header2: str) -> int:
    """
    Compare the levels of two markdown headers.
    Returns:
        -1 if header1 is higher level than header2
         0 if headers are same level
         1 if header1 is lower level than header2

    Examples:
        >>> compare_header_levels("# Header", "## Subheader")
        -1
        >>> compare_header_levels("### Section", "### Another Section")
        0
        >>> compare_header_levels("#### Subsection", "## Section")
        1
    """
    # Count leading '#' characters to determine level
    level1 = len(header1) - len(header1.lstrip("#"))
    level2 = len(header2) - len(header2.lstrip("#"))

    if level1 < level2:
        return -1
    elif level1 > level2:
        return 1
    else:
        return 0


# Alternative version that returns the actual levels:
def get_header_levels(header1: str, header2: str) -> tuple[int, int]:
    """
    Get the levels of two markdown headers.
    Returns tuple of (header1_level, header2_level)

    Examples:
        >>> get_header_levels("# Header", "## Subheader")
        (1, 2)
        >>> get_header_levels("### Section", "### Another Section")
        (3, 3)
    """
    level1 = len(header1) - len(header1.lstrip("#"))
    level2 = len(header2) - len(header2.lstrip("#"))
    return level1, level2
