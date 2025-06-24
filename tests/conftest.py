import pytest
from PySide6.QtWidgets import QApplication
import sys

@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
