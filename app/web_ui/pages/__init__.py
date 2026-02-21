"""Web UI ページモジュール。"""
from app.web_ui.pages.dashboard import render_dashboard
from app.web_ui.pages.results import render_results
from app.web_ui.pages.run_page import render_run_page
from app.web_ui.pages.settings import render_settings

__all__ = ["render_dashboard", "render_settings", "render_run_page", "render_results"]
