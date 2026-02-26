from collections import defaultdict
from typing import Any

from openhands.tools.cat_on_steroids.pdf_to_dict import (
    map_string_index_to_page,
    process_pdf_reference_manual,
)


# Define the structured data type
PageDict = dict[str, Any]


# Assume this class handles the PDF reading/parsing and stores the text/dicts
class DocumentPreprocessor:
    def __init__(self, doc_path: str):
        self.doc_path: str = doc_path

        self.processed_data = defaultdict()
        self._load_and_process()

    def _load_and_process(self):
        self.processed_data = process_pdf_reference_manual(patterns=self.doc_path)

    @property
    def full_text(self):
        return self.processed_data["full_text"]

    @property
    def page_count(self):
        return self.processed_data["page_count"]

    @property
    def toc(self):
        return self.processed_data["toc"]

    @property
    def doc_metadata(self):
        return self.processed_data["metadata"]

    def get_page(self, page_number):
        index = page_number - 1
        return self.processed_data["pages"][index]

    # Simple method to find which page dict a text index belongs to (for regex mapping)
    def map_index_to_page(self, match):
        # Implementation to find the PageDict based on its index in the full_text document
        filtered_pages = map_string_index_to_page(
            pages=self.processed_data["pages"], match=match
        )
        return filtered_pages
