import codecs
import re
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit


MAX_PAGE_SIZE = 5 * 1024 * 1024
REQUEST_TIMEOUT = 15
READ_CHUNK_SIZE = 64 * 1024


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.text_parts = []
        self.links = []
        self._in_title = False
        self._skip_depth = 0
        self._anchor_href = None
        self._anchor_parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attributes = dict(attrs)
        if tag in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "a" and attributes.get("href"):
            self._anchor_href = attributes["href"]
            self._anchor_parts = []
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "tr"):
            self.text_parts.append(" ")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style", "noscript", "svg") and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._anchor_href is not None:
            label = " ".join(" ".join(self._anchor_parts).split())
            self.links.append((self._anchor_href, label))
            self._anchor_href = None
            self._anchor_parts = []
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "tr"):
            self.text_parts.append(" ")

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        if self._skip_depth:
            return
        self.text_parts.append(data)
        if self._anchor_href is not None:
            self._anchor_parts.append(data)

    @property
    def title(self):
        return " ".join(" ".join(self.title_parts).split()) or "(no title)"

    @property
    def text(self):
        return re.sub(r"\s+", " ", " ".join(self.text_parts)).strip()


def crawl(url):
    url = url.strip()
    try:
        parts = urlsplit(url)
    except ValueError as error:
        print(f"Invalid URL: {error}")
        return
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        print("Invalid URL. Use an http:// or https:// link.")
        return

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "HackerTool-Pacho/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            content_type = response.headers.get_content_type()
            if content_type not in ("text/html", "application/xhtml+xml"):
                print(f"Unsupported content type: {content_type}")
                return
            content = bytearray()
            while True:
                chunk = response.read(READ_CHUNK_SIZE)
                if not chunk:
                    break
                content.extend(chunk)
                if len(content) > MAX_PAGE_SIZE:
                    print(f"Page exceeds the {MAX_PAGE_SIZE // (1024 * 1024)} MB limit.")
                    return
            raw_html = bytes(content)
            charset = response.headers.get_content_charset() or "utf-8"
            final_url = response.geturl()
    except (OSError, urllib.error.URLError, ValueError) as error:
        print(f"Could not fetch page: {error}")
        return

    try:
        codecs.lookup(charset)
    except LookupError:
        print(f"Unsupported page character encoding: {charset}")
        return
    html = raw_html.decode(charset, errors="replace")
    parser = _PageParser()
    parser.feed(html)

    host = re.sub(r"[^A-Za-z0-9.-]+", "_", urlsplit(final_url).hostname or "page")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path.cwd() / f"pacho_{host}_{timestamp}.html"
    try:
        duplicate_index = 1
        while True:
            try:
                with output_path.open("xb") as output:
                    output.write(raw_html)
                break
            except FileExistsError:
                output_path = (
                    Path.cwd()
                    / f"pacho_{host}_{timestamp}_{duplicate_index}.html"
                )
                duplicate_index += 1
    except OSError as error:
        print(f"Could not save HTML file: {error}")
        return

    print(f"Title: {parser.title}")
    print(f"URL: {final_url}")
    print(f"Text: {parser.text or '(no text found)'}")
    print("Links:")
    if parser.links:
        for href, label in parser.links:
            print(f"  {urljoin(final_url, href)}" + (f" - {label}" if label else ""))
    else:
        print("  (no links found)")
    print(f"Saved HTML: {output_path}")
