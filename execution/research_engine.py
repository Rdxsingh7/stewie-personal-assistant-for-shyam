"""
Stewie Research Engine — Web search in-depth topic research.

Searches the web, extracts content from top results, and uses
the LLM to compile structured research findings.
"""

from __future__ import annotations

from typing import Any, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger


# ═══════════════════════════════════════════
# WEB SEARCH
# ═══════════════════════════════════════════


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for a query using DuckDuckGo.

    Args:
        query: Search query string.
        max_results: Maximum number of results.

    Returns:
        List of {title, url, snippet} dicts.
    """
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddg:
            for r in ddg.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    }
                )

        logger.info(f"Web search for '{query}': {len(results)} results")
        return results

    except ImportError:
        logger.error("duckduckgo-search not installed.")
        raise
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        raise


# ═══════════════════════════════════════════
# CONTENT EXTRACTION
# ═══════════════════════════════════════════


def _extract_page_content(url: str, max_chars: int = 5000) -> str:
    """
    Fetch a webpage and extract its main text content.

    Args:
        url: URL to fetch.
        max_chars: Maximum characters to extract.

    Returns:
        Extracted text content.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove scripts, styles, and navigation elements
        for element in soup(
            ["script", "style", "nav", "header", "footer", "aside"]
        ):
            element.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        return clean_text[:max_chars]

    except Exception as e:
        logger.warning(f"Failed to extract content from {url}: {e}")
        return ""


# ═══════════════════════════════════════════
# DEEP RESEARCH
# ═══════════════════════════════════════════


async def research_topic(
    topic: str,
    depth: str = "detailed",
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
) -> dict[str, Any]:
    """
    Conduct in-depth research on a topic.

    Process:
    1. Search the web for the topic
    2. Extract content from top results
    3. Use LLM to synthesize findings into a structured summary

    Args:
        topic: The topic to research.
        depth: 'brief', 'detailed', or 'comprehensive'.
        api_key: OpenAI API key.
        model: LLM model to use.

    Returns:
        Dict with 'topic', 'summary', 'key_points', 'sources'.
    """
    logger.info(f"Starting research on: '{topic}' (depth={depth})")

    # Determine number of sources based on depth
    source_counts = {"brief": 3, "detailed": 5, "comprehensive": 8}
    num_sources = source_counts.get(depth, 5)

    # Step 1: Search
    search_results = await web_search(topic, max_results=num_sources)

    if not search_results:
        return {
            "topic": topic,
            "summary": f"No search results found for '{topic}'.",
            "key_points": [],
            "sources": [],
        }

    # Step 2: Extract content from each source
    extracted_content = []
    sources_list = []

    for result in search_results:
        url = result["url"]
        if url:
            content = _extract_page_content(url)
            if content:
                extracted_content.append(
                    {
                        "title": result["title"],
                        "url": url,
                        "content": content,
                    }
                )
                sources_list.append(
                    {"title": result["title"], "url": url}
                )

    logger.info(
        f"Extracted content from {len(extracted_content)}/{len(search_results)} sources"
    )

    # Step 3: Synthesize with LLM
    try:
        from openai import AsyncOpenAI

        if not api_key:
            from config.settings import load_config

            config = load_config()
            api_key = config.openai_api_key

        client = AsyncOpenAI(api_key=api_key)

        # Build the research context
        context_parts = []
        for item in extracted_content:
            context_parts.append(
                f"### Source: {item['title']}\n"
                f"URL: {item['url']}\n"
                f"{item['content'][:2000]}\n"
            )
        research_context = "\n---\n".join(context_parts)

        # Truncate to avoid token limits
        research_context = research_context[:12000]

        depth_instructions = {
            "brief": "Provide a brief 2-3 paragraph overview.",
            "detailed": "Provide a detailed summary with key points, sub-topics, and important details.",
            "comprehensive": "Provide a comprehensive analysis covering all major aspects, with sections, sub-sections, and detailed explanations.",
        }

        prompt = f"""Research the topic: "{topic}"

Based on the following sources, compile a {depth} research summary.

{depth_instructions.get(depth, depth_instructions['detailed'])}

Structure your response as:
1. SUMMARY: A cohesive overview
2. KEY POINTS: Bullet points of the most important findings
3. DETAILS: Expanded information organized by sub-topic

Sources:
{research_context}"""

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant. Produce well-structured, "
                        "factual summaries based on the provided sources. "
                        "Be thorough but concise."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.3,
        )

        research_text = response.choices[0].message.content

        # Parse key points from the response
        key_points = _extract_key_points(research_text)

        result = {
            "topic": topic,
            "summary": research_text,
            "key_points": key_points,
            "sources": sources_list,
            "depth": depth,
            "source_count": len(sources_list),
        }

        logger.info(
            f"Research complete: {len(key_points)} key points from "
            f"{len(sources_list)} sources"
        )
        return result

    except Exception as e:
        logger.error(f"Research synthesis failed: {e}")
        # Return raw snippets as fallback
        return {
            "topic": topic,
            "summary": "\n\n".join(
                f"**{r['title']}**: {r['snippet']}"
                for r in search_results
            ),
            "key_points": [r["snippet"] for r in search_results],
            "sources": sources_list,
        }


def _extract_key_points(text: str) -> list[str]:
    """Extract bullet points from research text."""
    points = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith(("- ", "• ", "* ", "→ ")):
            points.append(line.lstrip("-•*→ ").strip())
        elif line.startswith(tuple(f"{i}." for i in range(1, 20))):
            # Numbered points
            point = line.split(".", 1)[1].strip() if "." in line else line
            points.append(point)
    return points[:15]  # Cap at 15 key points
