import ast
import json
import re

from openhands.sdk.tool import ToolExecutor
from openhands.tools.cat_on_steroids.definition import (
    CatOnSteroidsAction,
    CatOnSteroidsObservation,
)
from openhands.tools.cat_on_steroids.preprocessor import (
    DocumentPreprocessor,
    PageDict,
)  # Assuming a path


# Dictionary to cache parsed documents (performance optimization)
_DOC_CACHE: dict[str, DocumentPreprocessor] = {}


class CatOnSteroidsExecutor(
    ToolExecutor[CatOnSteroidsAction, CatOnSteroidsObservation]
):
    def _get_preprocessor(self, doc_path: str) -> DocumentPreprocessor:
        """Handles document loading and caching."""
        if doc_path not in _DOC_CACHE:
            _DOC_CACHE[doc_path] = DocumentPreprocessor(doc_path)
        return _DOC_CACHE[doc_path]

    def _run_search(
        self, preprocessor: DocumentPreprocessor, pattern: str
    ) -> list[PageDict]:
        """Core FOS logic: case-sensitive regex-only search.
        If the provided pattern contains no regex-special characters, treat it
        as a simple word/phrase and automatically escape it and add word
        boundaries so common simple searches behave as expected.
        """

        # Characters that indicate the user likely provided a regex
        _REGEX_SPECIALS = set(r".^$*+?{}[]\|()")

        # If there are no regex-special characters, escape and wrap with \b
        if not any(ch in _REGEX_SPECIALS for ch in pattern):
            pattern = r"\b" + re.escape(pattern) + r"\b"

        # Compile as case-sensitive regex (no re.IGNORECASE)
        try:
            prog = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        full_text = preprocessor.full_text
        matches: list[PageDict] = []
        matched_pages: set[int] = set()

        for match in prog.finditer(full_text):
            # Map the match back to the structured PageDict.
            # Keep original behavior of map_index_to_page; it may accept a match object.
            page_dict = preprocessor.map_index_to_page(match)[0]

            # Ensure each page is included only once
            if page_dict["page_number"] not in matched_pages:
                matches.append(page_dict)
                matched_pages.add(page_dict["page_number"])

        return matches

    def _retrieve_pages(
        self, preprocessor: DocumentPreprocessor, pages: str
    ) -> list[PageDict]:
        """
        Retrieve one or more pages (by number or range) from the parsed document.

        Args:
            preprocessor (DocumentPreprocessor): The preprocessed document object.
            pages (str): A string representing pages or ranges.
                Examples:
                    "5"              -> [5]
                    "1,3,5"          -> [1, 3, 5]
                    "2-4"            -> [2, 3, 4]
                    "1-3,5,7-8"      -> [1, 2, 3, 5, 7, 8]
                    '["1-10"]'       -> [1,2,...,10]   (JSON-like quoted range)
                    "[1,2,3]"        -> [1,2,3]        (JSON-like numbers)

        Returns:
            list[dict]: List of page contents for all requested pages.
        """

        def expand_page_spec(spec: str) -> list[int]:
            """Expand a single page, page range, or comma-separated list into a list of ints.
            Also supports JSON-like list strings such as '["1-10"]' or '[1,2,3]'.
            """
            spec = spec.strip()
            if not spec:
                return []

            # Handle bracketed JSON/CSV-like lists: '["1-10"]', "[1,2,3]"
            if spec.startswith("[") and spec.endswith("]"):
                parsed = None
                try:
                    parsed = json.loads(spec)
                except Exception:
                    # Fallback to ast.literal_eval for cases like "['1-10']"
                    try:
                        parsed = ast.literal_eval(spec)
                    except Exception as e:
                        # If neither json.loads nor ast.literal_eval works, raise error.
                        raise ValueError(f"Invalid list format: {spec}") from e

                if isinstance(parsed, list):
                    results: list[int] = []
                    for item in parsed:
                        # recurse for each element (handles numbers, ranges, quoted strings)
                        results.extend(expand_page_spec(str(item)))
                    return results
                else:
                    # Not a list after parsing; fall back to processing the string form
                    spec = str(parsed).strip()

            # Strip surrounding quotes if present: '"5"' or "'5'"
            if (spec.startswith('"') and spec.endswith('"')) or (
                spec.startswith("'") and spec.endswith("'")
            ):
                spec = spec[1:-1].strip()

            if not spec:
                return []

            # --- FIX: Handle Comma-Separated List (e.g., '1-3,5,7-8') ---
            if "," in spec:
                results: list[int] = []
                # Split by comma and recursively call the function for each item
                for item in spec.split(","):
                    results.extend(expand_page_spec(item.strip()))
                return results
            # --- END FIX ---

            # Handle range with optional spaces like "1-10" or "1 - 10"
            if "-" in spec:
                # Use regex to split by '-' with optional surrounding spaces
                parts = re.split(r"\s*-\s*", spec, maxsplit=1)
                if len(parts) != 2 or not parts[0] or not parts[1]:
                    # This is now only reached if a single segment contains a malformed range
                    raise ValueError(f"Invalid page range: {spec}")
                try:
                    start, end = map(int, parts)
                    if start > end:
                        start, end = end, start  # handle reversed input
                    return list(range(start, end + 1))
                except ValueError:
                    raise ValueError(f"Invalid page range: {spec}")
            else:
                # Handle single page number
                try:
                    return [int(spec)]
                except ValueError:
                    raise ValueError(f"Invalid page number: {spec}")

        # Split comma-separated list, expand each spec, flatten all results
        all_pages = []
        for part in pages.split(","):
            part = part.strip()
            if not part:
                continue
            all_pages.extend(expand_page_spec(part))

        # Deduplicate and sort
        page_numbers = sorted(set(all_pages))

        # Retrieve content
        page_contents: list[PageDict] = [
            preprocessor.get_page(page_number=p) for p in page_numbers
        ]
        return page_contents

    def __call__(self, action: CatOnSteroidsAction, conv) -> CatOnSteroidsObservation:
        try:
            preprocessor = self._get_preprocessor(action.doc_path)
        except Exception as e:
            return CatOnSteroidsObservation(
                total_results=0, metadata_summary=[f"Error loading document: {e}"]
            )
        # --- Page retrieval logic ---
        if action.pages:
            try:
                pages = self._retrieve_pages(
                    preprocessor=preprocessor, pages=action.pages
                )
            except IndexError:
                return CatOnSteroidsObservation(
                    total_results=0,
                    content_results=["Page number doesn't exist in the document"],
                )

            return CatOnSteroidsObservation(
                total_results=len(pages), content_results=pages
            )
        # --- Search Logic (FOS) ---
        elif action.search_pattern:
            all_matches = self._run_search(
                preprocessor=preprocessor, pattern=action.search_pattern
            )

            total_count = len(all_matches)

            # Level 1: Metadata Summary
            if action.search_level == "surface":
                # metadata_summary = [
                #     f"Page {m['page_number']}(section level,title,page number): {m['toc_details']}\nContent:{m["page_content"][:100]}..."
                #     for m in all_matches
                # ]
                return CatOnSteroidsObservation(
                    total_results=total_count, metadata_summary=all_matches
                )

            # Level 2: Complete Content
            elif action.search_level == "deep":
                # Apply N limit (-1 means all)
                limit = action.n_results if action.n_results != -1 else total_count
                content_results = all_matches[:limit]

                return CatOnSteroidsObservation(
                    total_results=total_count, content_results=content_results
                )
            else:
                return CatOnSteroidsObservation(
                    total_results=0, content_results="action.search_level is missing!!"
                )

        # --- Viewing Logic (COS) ---
        else:
            # Assume no search pattern means the user wants the global document metadata (ToC)
            doc_metadata = {
                "total_pages": preprocessor.page_count,
                "sections": preprocessor.toc,
                "full_text_length": len(preprocessor.full_text),
                "pdf_metadata": preprocessor.doc_metadata,
            }
            # For a true COS view, you might want to return the ToC structure explicitly here

            return CatOnSteroidsObservation(doc_metadata=doc_metadata)
