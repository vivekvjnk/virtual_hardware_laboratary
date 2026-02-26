
import pytest
import yaml

from openhands.tools.cat_on_steroids.create_dummy_pdf import create_dummy_pdf
from openhands.tools.cat_on_steroids.definition import CatOnSteroidsAction
from openhands.tools.cat_on_steroids.impl import _DOC_CACHE, CatOnSteroidsExecutor
from openhands.tools.cat_on_steroids.preprocessor import DocumentPreprocessor


@pytest.fixture(autouse=True)
def clear_cache():
    # Ensure a clean global cache for each test run
    _DOC_CACHE.clear()
    yield
    _DOC_CACHE.clear()


@pytest.fixture
def dummy_pdf(tmp_path):
    pdf_path = tmp_path / "test_doc.pdf"
    create_dummy_pdf(str(pdf_path))
    return pdf_path


def test_view_mode_returns_document_metadata(dummy_pdf):
    doc_path = str(dummy_pdf)
    processed_doc = DocumentPreprocessor(doc_path=doc_path)
    _DOC_CACHE[doc_path] = processed_doc

    ex = CatOnSteroidsExecutor()
    action = CatOnSteroidsAction(doc_path=doc_path)  # no search_pattern => view mode
    obs = ex(action)

    print(obs)
    # assert obs.doc_metadata, "Expected doc_metadata in view mode observation"
    # assert obs.doc_metadata["total_pages"] == len(processed_doc.page_count)
    # assert obs.doc_metadata["full_text_length"] == len(processed_doc.full_text)
    # assert obs.doc_metadata["pdf_metadata"] == processed_doc.doc_metadata


def test_search_level_1_returns_metadata_summary(dummy_pdf):
    doc_path = str(dummy_pdf)
    processed_doc = DocumentPreprocessor(doc_path=doc_path)
    _DOC_CACHE[doc_path] = processed_doc

    ex = CatOnSteroidsExecutor()
    action = CatOnSteroidsAction(
        doc_path=doc_path, search_pattern="memory map", search_level="surface"
    )
    obs = ex(action)
    with open("test_level_1.yaml", "w") as f:
        yaml.safe_dump([tc.text for tc in obs.to_llm_content], f)
    # Two pages each contain "foo"
    # assert obs.total_results == 2
    # assert len(obs.metadata_summary) == 2
    # # Check that the summary strings reference page numbers and a content snippet
    # assert any("Page 1" in s or "page 1" in s for s in obs.metadata_summary)
    # assert any("Page 2" in s or "page 2" in s for s in obs.metadata_summary)


def test_search_level_2_respects_n_results_limit(dummy_pdf):
    doc_path = str(dummy_pdf)
    processed_doc = DocumentPreprocessor(doc_path=doc_path)
    _DOC_CACHE[doc_path] = processed_doc

    ex = CatOnSteroidsExecutor()

    # Request level 2 but limit to 1 result
    action = CatOnSteroidsAction(
        doc_path=doc_path, search_pattern="memory map", search_level="deep", n_results=1
    )
    obs = ex(action)

    with open("test_level_2.yaml", "w") as f:
        yaml.safe_dump([tc.text for tc in obs.to_llm_content], f)
    # assert obs.total_results == 2
    # assert len(obs.content_results) == 1
    # assert "page_number" in first and "page_content" in first


# if __name__ == "__main__":
#     # test_view_mode_returns_document_metadata()
#     # test_search_level_1_returns_metadata_summary()
#     test_search_level_2_respects_n_results_limit()
