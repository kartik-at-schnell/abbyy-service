import pytest


@pytest.fixture
def sample_document():
    return {"id": 1, "filename": "test.pdf", "status": "NEW"}

