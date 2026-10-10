from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGES = sorted(Path("app/pages").glob("*.py"))


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.stem)
def test_page_runs_without_exception(page: Path) -> None:
    at = AppTest.from_file(str(page.resolve()), default_timeout=90).run()
    assert not at.exception
