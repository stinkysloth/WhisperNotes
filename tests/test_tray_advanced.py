#!/usr/bin/env python3
"""
Pytest unit test for advanced tray menu wiring in WhisperNotes.
Ensures all advanced configuration actions are present and trigger the correct callbacks.
"""
import sys
import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
import importlib

@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    yield app

@pytest.fixture
def tray_manager(app):
    tray_mod = importlib.import_module("tray")
    # Create mocks for all callbacks
    on_record = MagicMock(name="on_record")
    on_journal = MagicMock(name="on_journal")
    on_quit = MagicMock(name="on_quit")
    on_edit_prompt = MagicMock(name="on_edit_prompt")
    on_set_journal_dir = MagicMock(name="on_set_journal_dir")
    on_configure_templates = MagicMock(name="on_configure_templates")
    tm = tray_mod.TrayManager(
        app=app,
        parent=None,
        on_record=on_record,
        on_journal=on_journal,
        on_quit=on_quit,
        on_edit_prompt=on_edit_prompt,
        on_set_journal_dir=on_set_journal_dir,
        on_configure_templates=on_configure_templates
    )
    return tm, on_record, on_journal, on_quit, on_edit_prompt, on_set_journal_dir, on_configure_templates

def get_menu_actions(menu):
    """Recursively collect all actions and submenus from a QMenu."""
    actions = []
    for action in menu.actions():
        if action.menu():
            actions.append((action.text(), get_menu_actions(action.menu())))
        else:
            actions.append(action.text())
    return actions

def test_tray_menu_structure(tray_manager):
    tm, *_ = tray_manager
    menu = tm.tray_icon.contextMenu()
    actions = get_menu_actions(menu)
    # Should include Record, Journal, Settings && Configuration (submenu), Quit
    assert any("Record" in str(a) for a in actions)
    assert any("Journal" in str(a) for a in actions)
    # Find settings submenu
    settings = [a for a in actions if isinstance(a, tuple) and "Settings" in a[0]]
    assert settings, "Settings submenu missing"
    settings_items = settings[0][1]
    assert any("Edit Summary Prompt" in str(i) for i in settings_items)
    assert any("Set Journal Directory" in str(i) for i in settings_items)
    assert any("Configure Templates" in str(i) for i in settings_items)
    assert any("Quit" in str(a) for a in actions)

def test_tray_menu_callbacks(tray_manager, qtbot):
    tm, on_record, on_journal, on_quit, on_edit_prompt, on_set_journal_dir, on_configure_templates = tray_manager
    menu = tm.tray_icon.contextMenu()
    # Find and trigger each action
    for action in menu.actions():
        if action.text() == "Record":
            action.trigger()
            on_record.assert_called_once()
        elif action.text() == "Journal":
            action.trigger()
            on_journal.assert_called_once()
        elif action.text() == "Quit":
            action.trigger()
            on_quit.assert_called_once()
        elif action.menu() and "Settings" in action.text():
            # Drill into settings submenu
            for subaction in action.menu().actions():
                if "Edit Summary Prompt" in subaction.text():
                    subaction.trigger()
                    on_edit_prompt.assert_called_once()
                elif "Set Journal Directory" in subaction.text():
                    subaction.trigger()
                    on_set_journal_dir.assert_called_once()
                elif "Configure Templates" in subaction.text():
                    subaction.trigger()
                    on_configure_templates.assert_called_once()
