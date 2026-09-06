import os
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.tools import tool
from tavily import TavilyClient


load_dotenv()


SOCIAL_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "youtu.be",
}


def _get_tavily_client() -> TavilyClient:
    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        raise RuntimeError(
            "TAVILY_API_KEY is missing from the .env file."
        )

    return TavilyClient(api_key=api_key)


def _normalize_domain(url: str) -> str:
    domain = urlparse(url).netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def _clean_text(text: str, limit: int = 2000) -> str:
    if not text:
        return "No readable text was found on this page."

    # Remove Markdown images while keeping ordinary link labels readable.
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove leftover HTML and excessive Markdown decoration.
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[*_#]{2,}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return "No readable text was found on this page."

    return text[:limit]


def search_urls(query: str, limit: int = 5) -> list[str]:
    """Return relevant URLs from different domains, preferring readable websites."""
    tavily = _get_tavily_client()
    response = tavily.search(query=query, max_results=15)

    preferred = []
    fallback = []
    seen_domains = set()

    for result in response.get("results", []):
        url = (result.get("url") or "").strip()

        if not url:
            continue

        domain = _normalize_domain(url)

        if not domain or domain in seen_domains:
            continue

        seen_domains.add(domain)

        if domain in SOCIAL_DOMAINS:
            fallback.append(url)
        else:
            preferred.append(url)

    urls = preferred[:limit]

    if len(urls) < limit:
        urls.extend(fallback[: limit - len(urls)])

    return urls[:limit]


@tool
def web_search(query: str) -> str:
    """Use Tavily to find five relevant URLs from different websites."""
    urls = search_urls(query, limit=5)

    if not urls:
        return "No relevant URLs found."

    return "\n".join(
        f"{index}. {url}"
        for index, url in enumerate(urls, start=1)
    )


def scrape_url_text(url: str) -> str:
    """Scrape and return clean readable text from one URL."""
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "noscript",
                "form",
                "button",
                "svg",
            ]
        ):
            tag.decompose()

        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.body
            or soup
        )

        text = main_content.get_text(separator=" ", strip=True)
        return _clean_text(text)

    except Exception as exc:
        return f"Could not read this source: {exc}"


def extract_urls_text(urls: list[str]) -> list[str]:
    """Extract readable content from multiple URLs with HTTP fallback."""
    if not urls:
        return []

    extracted_by_url = {}

    try:
        tavily = _get_tavily_client()
        response = tavily.extract(
            urls=urls,
            extract_depth="basic",
        )

        for result in response.get("results", []):
            result_url = (result.get("url") or "").strip()
            raw_content = (result.get("raw_content") or "").strip()

            if result_url and raw_content:
                extracted_by_url[result_url] = _clean_text(raw_content)

    except Exception as exc:
        print(f"[ResearchMind] Tavily Extract fallback: {exc}")

    contents = []

    for url in urls:
        content = extracted_by_url.get(url)

        if not content:
            content = scrape_url_text(url)

        contents.append(content)

    return contents


@tool
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a given URL."""
    return scrape_url_text(url)
