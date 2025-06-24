import pytest
from tray import TrayManager
from PySide6.QtWidgets import QApplication

@pytest.mark.usefixtures("qapp")
def test_tray_manager_initialization(qapp):
    """Test that TrayManager initializes without crashing."""
    tray = None
    try:
        tray = TrayManager(
        app=qapp,
        parent=None,
        on_record=lambda: None,
        on_journal=lambda: None,
        on_quit=lambda: None
    )
    except Exception as e:
        pytest.fail(f"TrayManager initialization raised an exception: {e}")
    finally:
        # Clean up tray icon if possible
        if tray and hasattr(tray, 'tray_icon'):
            tray.tray_icon.hide()
