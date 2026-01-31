"""Pagination helpers for Jina reader output."""

from __future__ import annotations

from dataclasses import dataclass

from .tokenizer import count_tokens


@dataclass(frozen=True)
class Page:
    page_num: int
    content: str
    tokens: int


def paginate_content(content: str, tokens_per_page: int) -> list[Page]:
    pages: list[Page] = []
    current_page = 1
    start = 0

    total_tokens = count_tokens(content)
    if total_tokens <= tokens_per_page:
        return [Page(page_num=1, content=content, tokens=total_tokens)]

    while start < len(content):
        left = start
        right = len(content)
        best_end = min(start + 1, len(content))

        while left < right:
            mid = (left + right + 1) // 2
            chunk = content[start:mid]
            tokens = count_tokens(chunk)

            if tokens <= tokens_per_page:
                left = mid
                best_end = mid
            else:
                right = mid - 1

        chunk = content[start:best_end]
        chunk_tokens = count_tokens(chunk)
        natural_end = _find_natural_break_point(chunk, chunk_tokens, tokens_per_page)
        final_end = start + natural_end

        page_content = content[start:final_end]
        pages.append(Page(page_num=current_page, content=page_content, tokens=count_tokens(page_content)))

        start = final_end
        current_page += 1

    return pages


def _find_natural_break_point(text: str, current_tokens: int, target_tokens: int) -> int:
    min_token_ratio = 0.85
    has_reached_minimum = current_tokens >= (target_tokens * min_token_ratio)

    if not has_reached_minimum:
        return len(text)

    paragraph_break = text.rfind("\n\n")
    if paragraph_break > len(text) * 0.9:
        return paragraph_break + 2

    sentence_break = max(
        text.rfind(". "),
        text.rfind("! "),
        text.rfind("? "),
    )
    if sentence_break > len(text) * 0.9:
        return sentence_break + 2

    if paragraph_break > len(text) * 0.85:
        return paragraph_break + 2

    if sentence_break > len(text) * 0.85:
        return sentence_break + 2

    word_break = text.rfind(" ")
    if word_break > len(text) * 0.8:
        return word_break + 1

    return len(text)


def get_page(pages: list[Page], page_num: int) -> Page | None:
    if page_num < 1 or page_num > len(pages):
        return None
    return pages[page_num - 1]
