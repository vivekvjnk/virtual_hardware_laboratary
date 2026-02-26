from collections.abc import Sequence
from textwrap import shorten
from typing import TYPE_CHECKING, Literal, Self

from pydantic import Field

from openhands.sdk import get_logger
from openhands.sdk.llm import TextContent
from openhands.tools.cat_on_steroids.pdf_to_dict import page_dict_to_string
from openhands.tools.cat_on_steroids.sanitize_utf8 import _SanitizingModelMixin


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import ConversationState

from openhands.sdk.tool import (
    Action,
    Observation,
    ToolAnnotations,
    ToolDefinition,
)


logger = get_logger(__name__)


class CatOnSteroidsAction(Action):
    """
    Action to view document metadata or perform structured search (COS/FOS).
    """

    doc_path: str = Field(description="Absolute path to the PDF document.")
    # --- Search Parameters (FOS) ---
    search_pattern: str | None = Field(
        default=None,
        description="The keyword or regex pattern to search for in file contents. **NOTE: search is CASE SENSITIVE**",
    )
    search_level: Literal["surface", "deep"] = Field(
        default="surface",
        description=(
            "surface: Returns only metadata (page, section, count) for an overview. All matches are returned."
            "deep: Returns the complete content (dictionary format) of the top N results."
        ),
    )
    pages: str = Field(
        default="",
        description=(
            "String specifying which pages to retrieve from the parsed document. "
            "The **entire** specification string must be enclosed in single quotes (`'...'`). "
            'Use double quotes (`"..."`) for any strings *inside* list structures.\n'
            "Supported formats include:\n"
            "- Single page: `'3'`\n"
            "- List of pages: `'[1, 3, 5]'`\n"
            "- Page range: `'2-5'`\n"
            "- Mixed input (Recommended for ranges in a list): `'[\"1-3\", 5, 7]'`\n"
            "If left empty, no specific page filtering is applied."
        ),
    )

    n_results: int = Field(
        default=10,
        description='Number of search results to return in "deep" search level. Use -1 for all results.',
    )


class CatOnSteroidsObservation(_SanitizingModelMixin, Observation):
    """
    Observation containing structured document information or search results.
    """

    total_results: int = 0
    metadata_summary: list[dict] = Field(default_factory=list)  # For Level 1 output
    content_results: list[dict] = Field(default_factory=list)  # For Level 2 output
    page_results: list[dict] = Field(default_factory=list)  # For retrieving pages
    doc_metadata: dict = Field(default_factory=dict)  # For COS (viewing) output

    @property
    def to_llm_content(self) -> Sequence[TextContent]:
        # --- Handle Search Results (FOS) ---
        if self.total_results > 0:
            # Level 1 Summary
            if self.metadata_summary:
                first_20_res = format_cos_search_output(
                    pages=self.metadata_summary[:40]
                )  # only return first 40 occurrences of the search result
                # more = ""
                # if len(self.metadata_summary) > 40:
                #     truncated_results_count = len(self.metadata_summary)-40
                #     more = f"\n... and more...\ntruncated {truncated_results_count} results ..."
                # meta_search_results = f"{first_20_res}{more}"
                meta_search_results = first_20_res
                return [TextContent(text=meta_search_results)]

            # Level 2 Content
            elif self.content_results:
                # Format the list of dictionaries into a clean, LLM-digestible string
                formatted_results = "\n\n--- <Page Break> ---\n\n".join(
                    page_dict_to_string(r) for r in self.content_results
                )
                ret = (
                    f"Found {self.total_results} results. Returning {len(self.content_results)} complete pages.\n"
                    f"Content:\n{formatted_results}"
                )
                return [TextContent(text=ret)]
            elif self.page_results:
                # Format the list of dictionaries into a clean, LLM-digestible string
                formatted_results = "\n\n--- <Page Break> ---\n\n".join(
                    page_dict_to_string(r) for r in self.page_results
                )
                ret = (
                    f"Returning {len(self.page_results)} complete pages.\n"
                    f"Content:\n{formatted_results}"
                )
                return [TextContent(text=ret)]

        # --- Handle Document Metadata (COS View) ---
        elif self.doc_metadata:
            # Simple metadata view (e.g., Table of Contents)
            formatted_meta = format_toc(metadata=self.doc_metadata, level=-1)
            return [TextContent(text=formatted_meta)]

        return [
            TextContent(text="COS tool executed, but no relevant data was returned.")
        ]

    @property
    def to_condensed_llm_content(self) -> Sequence[TextContent]:
        logger.debug(
            "to_condensed_llm_message called: total_results=%s, metadata_summary_len=%s, content_results_len=%s, page_results_len=%s, doc_metadata_present=%s",
            self.total_results,
            len(self.metadata_summary),
            len(self.content_results),
            len(self.page_results),
            bool(self.doc_metadata),
        )

        # --- Handle Search Results (FOS) ---
        if self.total_results > 0:
            logger.debug("Branch: total_results > 0")

            # Level 1 Summary
            if self.metadata_summary:
                logger.debug(
                    "Branch: metadata_summary present (total metadata entries=%d). Returning condensed top entries.",
                    len(self.metadata_summary),
                )

                first_20_res = format_cos_search_output(
                    pages=self.metadata_summary[:20]
                )  # only return first 20 occurrences of the search result
                meta_search_results = first_20_res
                logger.debug(
                    "Returning %d metadata summary entries (condensed to %d).",
                    len(self.metadata_summary),
                    len(self.metadata_summary[:20]),
                )
                return [TextContent(text=meta_search_results)]

            # Level 2 Content
            elif self.content_results:
                logger.debug(
                    "Branch: content_results present (total_results=%d, content_results_len=%d). Preparing full content pages.",
                    self.total_results,
                    len(self.content_results),
                )
                # Format the list of dictionaries into a clean, LLM-digestible string
                formatted_results = "\n\n--- <Page Break> ---\n\n".join(
                    page_dict_to_string(r) for r in self.content_results
                )
                ret = (
                    f"Found {self.total_results} results. Returning {len(self.content_results)} complete pages.\n"
                    f"Content:\n{formatted_results}"
                )
                logger.debug(
                    "Returning Level 2 content with %d pages.",
                    len(self.content_results),
                )
                return [TextContent(text=ret)]
            elif self.page_results:
                logger.debug(
                    "Branch: page_results present (page_results_len=%d). Preparing requested pages.",
                    len(self.page_results),
                )
                # Format the list of dictionaries into a clean, LLM-digestible string
                formatted_results = "\n\n--- <Page Break> ---\n\n".join(
                    page_dict_to_string(r) for r in self.page_results
                )
                ret = (
                    f"Returning {len(self.page_results)} complete pages.\n"
                    f"Content:\n{formatted_results}"
                )
                logger.debug(
                    "Returning page retrieval content with %d pages.",
                    len(self.page_results),
                )
                return [TextContent(text=ret)]

        # --- Handle Document Metadata (COS View) ---
        elif self.doc_metadata:
            logger.debug("Branch: doc_metadata present. Formatting TOC with level=2.")
            # Simple metadata view (e.g., Table of Contents)
            formatted_meta = format_toc(metadata=self.doc_metadata, level=2)
            logger.debug(
                "Returning formatted TOC (doc_metadata keys=%s).",
                list(self.doc_metadata.keys()),
            )
            return [TextContent(text=formatted_meta)]

        logger.debug("No relevant data returned from COS tool.")
        return [
            TextContent(text="COS tool executed, but no relevant data was returned.")
        ]


def format_toc(metadata: dict, level: int | None = None) -> str:
    """
    Convert document metadata into a structured, LLM-optimized Table of Contents (TOC).

    Args:
        metadata (dict): Document metadata containing 'total_pages' and 'sections'.
        level (int | None): Maximum depth of TOC to include.
                            If None or -1, includes all levels.

    Returns:
        str: Formatted TOC text with truncation info if applicable.
    """
    total_pages = metadata.get("total_pages", "Unknown")
    sections = metadata.get("sections", [])
    if not sections:
        return "No section metadata available."

    lines = [
        "Document Metadata",
        "-" * 19,
        f"Total Pages: {total_pages}",
        "",
        "Table of Contents",
        "=================",
    ]

    max_level = None if level in (None, -1) else int(level)

    # Group sections by hierarchy for efficient truncation detection
    grouped = {}
    for idx, (sec_level, title, page) in enumerate(sections):
        grouped.setdefault(sec_level, []).append((idx, title, page))

    # Helper to count deeper subsections for a given section
    def count_subsections(start_idx: int, parent_level: int) -> int:
        count = 0
        for i in range(start_idx + 1, len(sections)):
            lvl, _, _ = sections[i]
            if lvl <= parent_level:
                break
            count += 1
        return count

    # Iterate through TOC and build formatted output
    for idx, (sec_level, title, page) in enumerate(sections):
        if max_level is not None and sec_level > max_level:
            continue

        indent = "    " * (sec_level - 1)
        lines.append(f"{indent}{title}  (p.{page})")

        # If we are truncating deeper levels, summarize them
        if max_level is not None and sec_level == max_level:
            sub_count = count_subsections(idx, sec_level)
            if sub_count > 0:
                lines.append(f"{indent}    ... {sub_count} subsections truncated")

    return "\n".join(lines)


def format_cos_search_output(
    pages: list[dict], content_preview_chars: int = 120
) -> str:
    """
    Format a list of COS (CatOnSteroids) page items into a structured,
    human-readable output with hierarchical TOC information and
    truncated content previews.

    Args:
        pages (list[dict]): List of dictionaries with keys:
            - page_number (int)
            - sections (list[list[int, str, int]])
            - content (str)
        content_preview_chars (int): Number of characters to show in content preview.

    Returns:
        str: Nicely formatted string summary.
    """
    lines = []

    for page in pages:
        page_num = page.get("page_number", "Unknown")
        # Note: The key for sections in the function body is "toc_details",
        # but the docstring says "sections". Using "toc_details" to match the body.
        sections = page.get("toc_details", [])

        # --- START FIX: Robust Content Sanitization ---
        raw_content = page.get("page_content")

        # 1. Ensure it's a string, not bytes, and handle None
        content = ""
        if isinstance(raw_content, bytes):
            # Decode using a lenient codec that can handle 0x89 (like latin-1),
            # then normalize to clean UTF-8.
            content = (
                raw_content.decode("latin-1", errors="replace")
                .encode("utf-8", errors="replace")
                .decode("utf-8")
            )
        elif isinstance(raw_content, str):
            # If it's already a string, normalize it to strip invalid characters
            content = raw_content.encode("utf-8", errors="ignore").decode("utf-8")

        content = content.strip()
        # --- END FIX ---

        lines.append(f"\n**Page {page_num}**")

        if sections:
            prev_level = 0
            for idx, (level, title, pnum) in enumerate(sections):
                indent = "    " * (level - 1)
                lines.append(f"{indent}- {title}  (p.{pnum})")

                next_idx = idx + 1
                if next_idx < len(sections):
                    # Safely access the next level
                    try:
                        next_level = sections[next_idx][0]
                        if next_level > level:
                            # Count only immediate deeper levels (optional refinement)
                            deeper = sum(
                                1 for lvl, _, _ in sections[next_idx:] if lvl > level
                            )
                            lines.append(
                                f"{indent}    ... {deeper} subsections truncated"
                            )
                    except IndexError:
                        # Should not happen if next_idx is checked, but for safety
                        pass

        else:
            lines.append("  - [No section hierarchy found]")

        # Add truncated content preview
        preview_input = content.replace("\n", " ")

        # Ensure 'shorten' is robust (it generally is, but we clean the input anyway)
        preview = shorten(preview_input, width=content_preview_chars, placeholder="...")
        lines.append(f"   Preview: {preview}")

    lines.append(
        "\n*To see full content, call `CatOnSteroidsAction` with `search_level=2`.*"
    )

    return "\n".join(lines)


TOOL_DESCRIPTION_V0 = """Powerful tool for navigating and searching large engineering or scientific reference documents (PDFs, datasheets, textbooks, research reports, etc.). 
Designed as an intelligent extension of the Unix `cat` command.

* Converts documents into structured, metadata-rich pages for reliable AI consumption.
* **VIEW MODE:** Retrieve overall document structure (Table of Contents, page count, metadata).
* **SEARCH MODE:** Find keywords or regex patterns and return structured page-level data.
* **PAGE RETRIEVAL:** Directly fetch specific pages or ranges without performing a search. 
    * Accepts single pages (e.g., 5), lists (e.g., [1, 3, 7]), or ranges (e.g., '2-5'). 
    * Mixed inputs are supported, such as ['1-3', 5, 8].
    * Ignored if a search_pattern is provided.
* **Search Levels:**
    * Level 1 (default): Returns a concise summary of page and section metadata where matches occur — ideal for quick scoping.
    * Level 2: Returns the full, rich dictionary data for each matched page — ideal for reasoning or downstream AI processing.
* Use this tool to efficiently extract precise information (e.g., register definitions, thermal limits, or circuit parameters) without scanning entire documents manually.
"""

TOOL_DESCRIPTION = """Powerful tool for navigating and searching large engineering or scientific reference documents (PDFs, datasheets, textbooks, research reports, etc.). 
Designed as an intelligent extension of the Unix `cat` command.
* Converts documents into structured, metadata-rich pages for reliable AI consumption.
* **VIEW MODE:** Retrieve overall document structure (Table of Contents, page count, metadata).
* **SEARCH MODE:** Find keywords or regex patterns and return structured page-level data. **Search is CASE SENSITIVE**
* **PAGE RETRIEVAL:** Directly fetch specific pages or ranges without performing a search. 
    * Accepts single pages (e.g., 5), lists (e.g., [1, 3, 7]), or ranges (e.g., '2-5'). 
    * Mixed inputs are supported, such as ['1-3', 5, 8].
    * Ignored if a search_pattern is provided.
* **Search Levels:**
    * surface (default): Returns a concise summary of page and section metadata where matches occur — ideal for quick scoping.
    * deep: Returns the full, rich dictionary data for each matched page — ideal for reasoning or downstream AI processing.
* Use this tool to efficiently extract precise information (e.g., register definitions, thermal limits, or circuit parameters) without scanning entire documents manually.

**CRITICAL PAGE LIMIT RESTRICTIONS:**
!! NEVER request results that span more than 10 pages in a single invocation. This causes context overload and system failure.
* **PAGE RETRIEVAL MODE:** Request maximum 10 pages total (e.g., pages [1,2,3,4,5,6,7,8,9,10] or range '1-10' is acceptable; '1-15' or [1,5,8,12,15,18,20,22,25,30] is NOT).
* **SEARCH LEVEL:** If search results exceed 10 pages:
    - Use "surface" level first to scope matches
    - Narrow your search pattern to be more specific
    - Split into multiple targeted queries focusing on different sections/keywords
    - Retrieve only the most relevant 10 pages maximum per call
* **Best Practice:** Always start with VIEW MODE or "surface" level search to understand document structure, then make focused queries for specific pages.
* **If you need information across >10 pages:** Make multiple sequential tool calls, each retrieving ≤10 pages.
"""


class CatOnSteroidsTool(ToolDefinition[CatOnSteroidsAction, CatOnSteroidsObservation]):
    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence[Self]:
        from openhands.tools.cat_on_steroids.impl import CatOnSteroidsExecutor

        executor = CatOnSteroidsExecutor()
        return [
            cls(
                name="CatOnSteroids",
                description=TOOL_DESCRIPTION,
                action_type=CatOnSteroidsAction,
                observation_type=CatOnSteroidsObservation,
                executor=executor,
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
        ]
