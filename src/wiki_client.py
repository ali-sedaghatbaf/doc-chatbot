import os
import re

from bs4 import BeautifulSoup
from klarna_wiki_api.sessions import KlarnaWikiSession


class ParseKlarnaWikiSession(KlarnaWikiSession):
    def get_parsed_content(self, page_title: str) -> str | None:
        if not isinstance(page_title, str):
            raise Exception("page_title must be string!")

        params = {
            "action": "parse",
            "page": page_title,
            "format": "json",
            "prop": "text",
        }
        response = self.get(params=params)

        if page_content := response.get("parse", {}).get("text", {}).get("*"):
            return page_content

        return None


def reformat_table(soup, table):

    rows = table.find_all("tr")
    plain_table = []

    # some tables are uneven
    row_len = len(rows[0].find_all("th"))
    for row in rows:
        cells = row.find_all(["th", "td"])
        for i in range(len(cells), row_len):
            cells.append(soup.new_tag("td"))

        plain_table.append([cell.get_text(strip=True) for cell in cells])

    if plain_table:
        # Determine column widths
        col_widths = [
            max(len(row[col]) for row in plain_table)
            for col in range(len(plain_table[0]))
        ]

        # Create format string
        row_format = " | ".join(f"{{:<{w}}}" for w in col_widths)
        separator = "-|-".join("-" * w for w in col_widths)

        # Build the table
        output = []
        output.append(row_format.format(*plain_table[0]))  # Header
        output.append(separator)  # Separator
        for data_row in plain_table[1:]:
            output.append(row_format.format(*data_row))

        # Replace the original table with the reformatted plain text
        formatted_table = "\n".join(output)
        table.replace_with(soup.new_string(formatted_table))


def read_doc(doc_name):
    with ParseKlarnaWikiSession(
        username=os.environ["KLARNA_WIKI_USERNAME"],
        password=os.environ["KLARNA_WIKI_PASSWORD"],
        use_production=False,
        use_bot_login=True,
    ) as session:
        text = session.get_parsed_content(doc_name)
        with open("data.txt", "w") as f:
            f.write(text)
        soup = BeautifulSoup(text, "html.parser")

        # Remove all elements with the class "_warning"
        warning_elements = soup.select('[class*="template__statusbox"]')
        for w_element in warning_elements:
            w_element.decompose()

        # Remove all elements with the class "template_stamp"
        stamp_divs = soup.select('[class*="template__stamp"]')
        for stamp_div in stamp_divs:
            stamp_div.decompose()

        # Remove all evements with the class "thumbinner"
        thumbinners = soup.find_all("div", class_="thumbinner")
        for tb in thumbinners:
            tb.decompose()

        # Remove all infoboxes
        infobox_table = soup.find("table", class_="governingDocumentInfobox")
        if infobox_table:
            infobox_table.decompose()

        # Remove the navigation items
        nav_div = soup.find("div", class_="toc")
        if nav_div:
            nav_div.decompose()

        # Transform html tables to md tables
        wiki_tables = soup.find_all("table")
        for wk_table in wiki_tables:
            reformat_table(soup, wk_table)

        # transform html lists to md lists
        for ul in soup.find_all("ul"):
            for li in ul.find_all("li"):
                li.string = f"- {li.get_text(strip=True)}"
        for ol in soup.find_all("ol"):
            for index, li in enumerate(ol.find_all("li"), start=1):
                li.string = f"{index}. {li.get_text(strip=True)}"

        # Remove the Scope Heading link
        scope_heading_tag = soup.find(
            lambda tag: tag.name == "i" and tag.find("a", string="Scope (Heading)")
        )
        if scope_heading_tag:
            scope_heading_tag.decompose()

        # Transform headlines to md headlines
        headlines = soup.find_all("span", class_="mw-headline")
        for headline in headlines:
            headline.string = "\n\n# " + headline.string + "\n\n"

        # Remove edit links
        text = soup.get_text().replace("[edit | edit source]", "")

        # make sure no consecutive empty lines exist
        text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

        with open("data_striped.txt", "w") as f:
            f.write(text)
        return text
