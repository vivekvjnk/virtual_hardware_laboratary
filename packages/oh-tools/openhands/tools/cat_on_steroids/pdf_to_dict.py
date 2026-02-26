import bisect
import json
import os
import sys
from pathlib import Path
from pprint import pformat
from typing import Any

from openhands.tools.cat_on_steroids.sanitize_utf8 import sanitize_utf8


def get_toc_for_page(toc_list: list, page_number: int) -> list:
    """
    Finds TOC sections for a specific page, or the last active section
    if the page has no new entries.

    Args:
        toc_list: The Table of Contents, formatted as a list of lists:
                  [[level, title, page], ...]
        page_number: The integer page number to look up.

    Returns:
        A list of TOC entries (list of lists) relevant to the given page.
    """
    result_entries = []
    last_valid_path = []

    if not toc_list:
        max_level = 10
    else:
        max_level = max(entry[0] for entry in toc_list)

    current_path = [None] * max_level

    for entry in toc_list:
        level, title, page = entry
        if page > page_number:
            return result_entries or last_valid_path

        current_level_index = level - 1
        current_path[current_level_index] = entry
        for i in range(current_level_index + 1, max_level):
            current_path[i] = None

        this_entry_full_path = [x for x in current_path[:level] if x]
        last_valid_path = this_entry_full_path

        if page == page_number:
            for ancestor in this_entry_full_path:
                if ancestor not in result_entries:
                    result_entries.append(ancestor)

    return result_entries if result_entries else last_valid_path


def ensure_pymupdf():
    """Ensures PyMuPDF (fitz) is installed and importable."""
    try:
        import fitz  # noqa
    except Exception:
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "pymupdf"]
        )
    import fitz

    return fitz


def find_pdf_file(
    search_root: Path, patterns: list[str] | None = None
) -> Path | None:
    """
    Searches recursively for a PDF file using provided glob patterns.
    Falls back to any PDF if none matches the given patterns.

    Args:
        search_root: Root directory to begin the search.
        patterns: List of glob patterns (e.g. ["*STM32*F405*.pdf", "*reference*.pdf"]).
                  If None, defaults to ["*STM32*F405*.pdf"] for backward-compatible behavior.

    Returns:
        Path to the found PDF or None if not found.
    """
    if patterns is None:
        patterns = ["*STM32*F405*.pdf"]
    # Accept a single string pattern as well
    if isinstance(patterns, str):
        patterns = [patterns]

    candidates = []
    for pat in patterns:
        if Path(patterns[0]).is_absolute() and Path(patterns[0]).is_file():
            return Path(patterns[0])
        else:
            candidates.extend(search_root.rglob(pat))

    if not candidates:
        # fallback to any PDF in the tree
        candidates = list(search_root.rglob("*.pdf"))

    # make deterministic and remove duplicates
    unique_sorted = sorted({p for p in candidates}, key=lambda p: str(p))
    return unique_sorted[0] if unique_sorted else None


def load_document(pdf_path: Path, fitz_module) -> Any:
    """
    Opens a PDF document using PyMuPDF and retrieves its metadata.

    Args:
        pdf_path: Path to the PDF file.
        fitz_module: Imported PyMuPDF module.

    Returns:
        A tuple: (document_object, metadata_dict)
    """
    doc = fitz_module.open(str(pdf_path))
    return doc, doc.metadata


def extract_page_data(doc) -> list[dict[str, Any]]:
    """
    Extracts plain text, structured blocks, and metadata for each page.

    Args:
        doc: PyMuPDF Document object.

    Returns:
        List of dictionaries containing page details.
    """
    # def sanitize_utf8(text: str) -> str:
    #     """
    #     Ensures text contains only valid UTF-8 characters.
    #     Replaces invalid characters with a placeholder.
    #     """
    #     if isinstance(text, bytes):
    #         # If we receive bytes, decode with error handling
    #         return text.decode('utf-8', errors='replace')

    #     # If it's already a string, encode and decode to catch any issues
    #     try:
    #         # This will catch any surrogate pairs or invalid Unicode
    #         text.encode('utf-8')
    #         return text
    #     except UnicodeEncodeError:
    #         # Replace invalid characters with the Unicode replacement character
    #         return text.encode('utf-8', errors='replace').decode('utf-8')

    pages = []
    full_text = ""
    for i in range(doc.page_count):
        page = doc.load_page(i)
        page_number = i + 1
        rect = page.rect
        page_meta = {
            "width": rect.width,
            "height": rect.height,
            "rotation": page.rotation,
            "number": i + 1,
        }

        # Extract and sanitize page content
        page_content_raw = page.get_text("text")
        page_content = sanitize_utf8(page_content_raw)

        marker = f"\n\n<<PAGE_BREAK:{page_number}>>\n\n"
        start_index = len(full_text)
        full_text += marker + page_content
        end_index = len(full_text)

        page_dict_text = page.get_text("dict")
        pages.append(
            {
                "page_number": page_number,
                "page_indices": {"start_index": start_index, "end_index": end_index},
                "page_meta": page_meta,
                "page_content": page_content,
                "page_blocks": page_dict_text,
                "toc_details": None,
            }
        )
    return pages, full_text


def map_toc_to_pages(pages: list[dict[str, Any]], toc: list[list[Any]]) -> None:
    """
    Maps TOC entries to their respective pages using `get_toc_for_page`.

    Args:
        pages: List of page dictionaries.
        toc: Table of Contents entries (list of [level, title, page]).
    """
    for page in pages:
        page["toc_details"] = get_toc_for_page(toc, page["page_number"])


def sample_page_mapping(
    pages: list[dict[str, Any]], start: int = 1, end: int = 5
) -> None:
    """
    Prints TOC mappings and text snippets for sample pages.

    Args:
        pages: List of page dictionaries.
        start: Starting page number (1-based).
        end: Ending page number (inclusive).
    """
    for p in pages[start - 1 : min(end, len(pages))]:
        print(f"Page {p['page_number']:3d}: Section={repr(p['toc_details'])}")
        snippet = (p["page_content"] or "").strip().splitlines()
        if snippet:
            print("  Text snippet:", repr(snippet[0][:200]))
        else:
            print("  [no text on this page]")


def save_page_index_json(
    doc_metadata: dict[str, Any],
    pages: list[dict[str, Any]],
    toc: list[list[Any]],
    full_text: str,
    pdf_filename: str,
) -> Path:
    """
    Saves extracted PDF summary (metadata + TOC + page info) to JSON.

    Args:
        doc_metadata: Document metadata dictionary.
        pages: List of page dictionaries.
        toc: List of TOC entries.
        full_text: Full text extracted from the PDF.
        pdf_filename: The original filename of the PDF to derive the output JSON filename.

    Returns:
        Path to the saved JSON file.
    """
    storage_dir = Path("processed_pdfs_data")
    storage_dir.mkdir(exist_ok=True)  # Create the directory if it doesn't exist

    json_filename = f"{Path(pdf_filename).stem}.json"
    out_path = storage_dir / json_filename

    out = {
        "full_text": full_text,
        "document_metadata": doc_metadata,
        "page_count": len(pages),
        "toc": toc,
        "pages": [
            {
                "page_number": p["page_number"],
                "page_indices": p["page_indices"],
                "page_meta": p["page_meta"],
                "toc_details": p["toc_details"],
                "page_content": (p["page_content"] or ""),
            }
            for p in pages
        ],
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return out_path.resolve()


def process_pdf_reference_manual(patterns):
    """
    Main orchestrator function that:
    - Finds PDF in the working directory tree
    - Extracts metadata, TOC, and page details
    - Maps TOC sections to individual pages
    - Saves summary JSON to disk
    """
    fitz = ensure_pymupdf()

    nb_root = Path.cwd()
    pdf_path = find_pdf_file(search_root=nb_root, patterns=patterns)

    if not pdf_path:
        raise FileNotFoundError("No PDF found.")

    os.chdir(pdf_path.parent)
    print(f"Changed cwd to: {pdf_path.parent}")
    print(f"Using PDF: {pdf_path.name}")

    doc, doc_metadata = load_document(pdf_path, fitz)
    print(f"Document pages: {doc.page_count}")
    print("Document metadata sample:", {k: v for k, v in doc_metadata.items() if v})

    toc = doc.get_toc()
    print(f"TOC entries: {len(toc)} (each entry: [level, title, page])")

    pages, full_text = extract_page_data(doc)
    map_toc_to_pages(pages, toc)

    print("\nSample page-to-TOC mapping (first 6 pages):")
    sample_page_mapping(pages, 1, 6)

    out_path = save_page_index_json(doc_metadata, pages, toc, full_text, pdf_path.name)
    print(f"\nSaved summary JSON to: {out_path}")
    return {
        "metadata": doc_metadata,
        "toc": toc,
        "pages": pages,
        "full_text": full_text,
        "page_count": len(pages),
    }


def page_dict_to_string(page_dict: dict, mode: str = "prompt") -> str:
    """
    Converts a page dictionary into a formatted string suitable for
    either human inspection ('pretty') or LLM input ('prompt').

    The page dictionary represents a single page extracted from a
    larger PDF document, where all page texts are concatenated into
    one long string called 'full_text'. The 'page_indices' field
    defines the substring boundaries for this page within 'full_text'.

    Args:
        page_dict (dict): Dictionary with the following keys:
            - page_number (int): The 1-based page number.
            - page_indices (dict): {"start_index": int, "end_index": int}
              denoting substring positions of this page's text within 'full_text'.
            - page_meta (dict): Basic page metadata (width, height, rotation, etc.).
            - toc_details (list): List of hierarchical TOC entries (each [level, title, page]).
            - page_content (str): Extracted text of the page.
        mode (str):
            'pretty' → Developer/debug format using pprint.
            'prompt' → Compact, LLM-friendly textual format.

    Returns:
        str: A string representation of the page dictionary.
    """
    if mode == "pretty":
        # Developer/debug mode: structured but verbose Pythonic format.
        return pformat(page_dict, width=100, compact=False)

    elif mode == "prompt":
        # Extract fields with safety defaults
        page_number = page_dict.get("page_number", "?")
        page_indices = page_dict.get("page_indices", {})
        meta = page_dict.get("page_meta", {})
        toc = page_dict.get("toc_details", [])
        text = (page_dict.get("page_content") or "").strip()

        # Extract start and end indices from the index dictionary
        start_idx = page_indices.get("start_index", "?")
        end_idx = page_indices.get("end_index", "?")

        # Build hierarchical section title path, if TOC is available
        toc_titles = " -> ".join([t[1] for t in toc if len(t) > 1]) if toc else "N/A"

        # Construct the formatted LLM-friendly text
        return (
            f"Page {page_number}\n"
            f"Text Span in full_text: start={start_idx}, end={end_idx}\n"
            f"Section Path: {toc_titles}\n"
            f"--- PAGE CONTENT START ---\n"
            f"{text}\n"
            f"--- PAGE CONTENT END ---"
            # f"Dimensions: {meta.get('width')}x{meta.get('height')} | Rotation: {meta.get('rotation')}\n"
        )

    else:
        raise ValueError("mode must be either 'pretty' or 'prompt'")


def map_string_index_to_page(match, pages):
    page, index = find_interval(pages=pages, x=match.start())
    # check if match indices are inside the page or not
    if match.end() <= page["page_indices"]["end_index"]:
        return [page]
    elif match.end() <= pages[index + 1]["page_indices"]["end_index"]:
        return [page, pages[index + 1]]
    else:
        print("Search pattern spans more than 2 pages!! Returning first page..")
        return [page]


def find_interval(pages, x):
    """
    Given a sorted, non-overlapping list of intervals,
    find the interval that contains x.
    """
    # Extract the start boundaries
    starts = [iv["page_indices"]["start_index"] for iv in pages]
    # print(f"starts list: {starts}\nmatch.start: {x}")
    # Locate the insertion point for x in the starts list
    i = bisect.bisect_right(starts, x) - 1
    # print(f"Page indices: {pages[i]}")
    if (
        i >= 0
        and pages[i]["page_indices"]["start_index"]
        <= x
        <= pages[i]["page_indices"]["end_index"]
    ):
        return pages[i], i
    return None


if __name__ == "__main__":
    process_pdf_reference_manual()
