import json
import os
import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from tools import search_urls, extract_urls_text


load_dotenv()


# =========================================================
# MODEL SETUP
# =========================================================

llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
    temperature=0,
    max_retries=5,
)


# =========================================================
# SEARCH AGENT
# =========================================================


def run_search_agent(topic: str) -> str:
    urls = search_urls(topic, limit=5)

    if not urls:
        return "No relevant URLs found."

    return "\n".join(
        f"{index}. {url}"
        for index, url in enumerate(urls, start=1)
    )


# =========================================================
# READER AGENT
# =========================================================

reader_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a careful research reader. Summarize only the supplied "
            "webpage text. Do not invent facts, do not add new URLs, and "
            "return valid JSON only.",
        ),
        (
            "human",
            """Question: {topic}

Below are source texts identified by source number.
For every source, write 2 or 3 short factual sentences containing only the most useful information related to the question.

Return ONLY valid JSON in this format:
{{
  "1": "2-3 short factual sentences for source 1",
  "2": "2-3 short factual sentences for source 2"
}}

Include one key for every source number provided. Do not include URLs in the JSON summaries.

Sources:
{sources}
""",
        ),
    ]
)

reader_chain = reader_prompt | llm.bind(max_tokens=500) | StrOutputParser()


def _fallback_summary(content: str) -> str:
    clean = re.sub(r"\s+", " ", content).strip()

    if not clean:
        return "No readable content was available from this source."

    sentences = re.split(r"(?<=[.!?])\s+", clean)
    selected = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ][:3]

    return " ".join(selected)[:600]


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s*```$", "", cleaned)

    return cleaned.strip()


def run_reader_agent(topic: str, search_results: str) -> str:
    urls = re.findall(r"https?://\S+", search_results)
    urls = [url.rstrip(").,;]") for url in urls][:5]

    if not urls:
        return "No URLs were available for the Reader Agent."

    scraped = extract_urls_text(urls)
    source_blocks = []

    for index, content in enumerate(scraped, start=1):
        source_blocks.append(f"SOURCE {index}:\n{content}")

    raw_summary = reader_chain.invoke(
        {
            "topic": topic,
            "sources": "\n\n".join(source_blocks),
        }
    )

    cleaned = _strip_code_fence(raw_summary)

    try:
        summaries = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        summaries = {}

    output = []

    for index, (url, content) in enumerate(
        zip(urls, scraped),
        start=1,
    ):
        summary = summaries.get(str(index))

        if not isinstance(summary, str) or not summary.strip():
            summary = _fallback_summary(content)

        # This exact format is intentionally kept in sync with frontend/app.js.
        output.append(
            f"{index}. URL: {url}\n"
            f"   {summary.strip()}"
        )

    return "\n\n".join(output)


# =========================================================
# WRITER CHAIN
# =========================================================

writer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an expert professional research writer.

Write a clear, evidence-based, well-structured research report using only the supplied research material.

The report must follow this exact order:
# Introduction
# Key Findings
## 1. Descriptive finding title
## 2. Descriptive finding title
## 3. Descriptive finding title
# Conclusion
# Sources

Requirements:
- Start with Introduction.
- Include at least three distinct, well-explained findings.
- Give every finding a short descriptive heading and explain it in one or two paragraphs.
- Use evidence from the supplied source summaries and refer to source numbers naturally when useful.
- The Conclusion must directly answer the research question.
- The Sources section must list every supplied URL in numbered form.
- Do not invent facts or URLs.

Formatting rules:
- Never create Markdown tables.
- Never use pipe characters for tables.
- Never create horizontal separator lines or decorative rows of hyphens, underscores, equals signs, or asterisks.
- Do not use asterisks for bold or italic formatting.
- Do not create comparison tables; explain comparisons in paragraphs or numbered findings.
- Number finding headings sequentially: 1, 2, 3, 4, and so on.
- Keep the report professional, readable, and substantial.
""",
        ),
        (
            "human",
            """Research Topic:
{topic}

Research Material:
{research}

Write the final report now. Follow the required structure exactly and include all supplied source URLs at the end.
""",
        ),
    ]
)

writer_chain = writer_prompt | llm.bind(max_tokens=1500) | StrOutputParser()


_SECTION_HEADINGS = {
    "introduction": "# Introduction",
    "key findings": "# Key Findings",
    "conclusion": "# Conclusion",
    "sources": "# Sources",
    "references": "# Sources",
}


def clean_report_format(report: str) -> str:
    """Normalize the writer output without damaging valid report content or URLs."""
    if not report:
        return ""

    report = report.replace("\r\n", "\n").replace("\r", "\n")
    cleaned_lines = []
    current_section = ""

    for raw_line in report.split("\n"):
        line = raw_line.strip()

        if not line:
            cleaned_lines.append("")
            continue

        # Remove fenced-code markers if the model adds them.
        if line.startswith("```"):
            continue

        # Remove standalone decorative / horizontal separator rows.
        if re.fullmatch(r"[-_=*~:]{3,}", line):
            continue

        # Remove Markdown table separator rows such as | --- | :---: |.
        if re.fullmatch(
            r"\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?",
            line,
        ):
            continue

        # Convert unexpected table rows into readable plain text instead of
        # leaving table borders in the report.
        if line.count("|") >= 2:
            cells = [
                cell.strip()
                for cell in line.strip("|").split("|")
                if cell.strip()
            ]
            if cells:
                line = "; ".join(cells)
            else:
                continue

        # Remove Markdown bold / italic markers while preserving their text.
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        line = re.sub(r"__(.*?)__", r"\1", line)
        line = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", line)

        # Normalize required section headings even if the model omitted '#'.
        heading_key = re.sub(r"^#+\s*", "", line).rstrip(":").strip().lower()
        if heading_key in _SECTION_HEADINGS:
            normalized = _SECTION_HEADINGS[heading_key]
            current_section = heading_key
            cleaned_lines.append(normalized)
            continue

        # Normalize numbered finding titles into H2 headings.
        if current_section == "key findings":
            finding_match = re.match(
                r"^(?:#+\s*)?(?:finding\s*)?(\d+)[.):\-]?\s+(.+)$",
                line,
                flags=re.IGNORECASE,
            )
            if finding_match and len(line) <= 180:
                number = finding_match.group(1)
                title = finding_match.group(2).strip()
                cleaned_lines.append(f"## {number}. {title}")
                continue

        cleaned_lines.append(line)

    report = "\n".join(cleaned_lines)
    report = re.sub(r"\n{3,}", "\n\n", report)

    return report.strip()


def generate_report(topic: str, research: str) -> str:
    report = writer_chain.invoke(
        {
            "topic": topic,
            "research": research,
        }
    )

    return clean_report_format(report)


# =========================================================
# CRITIC CHAIN
# =========================================================

critic_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a professional research report evaluator.

Evaluate the report fairly using this 10-point rubric:
- Relevance to the research question: 2 points
- Quality and clarity of key findings: 2 points
- Use of supplied evidence and sources: 2 points
- Organization and readability: 2 points
- Completeness of Introduction, Conclusion, and Sources: 2 points

Do not reward unsupported claims and do not penalize a clean article-style report for not using tables. Be honest and specific.
""",
        ),
        (
            "human",
            """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
...
""",
        ),
    ]
)

critic_chain = critic_prompt | llm.bind(max_tokens=500) | StrOutputParser()
