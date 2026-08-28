import os
import re
from html.parser import HTMLParser
import pytest

def test_frontend_index_html_syntax_and_script_enclosure():
    """Regression test ensuring JavaScript source code is properly enclosed inside <script> tags."""
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    assert os.path.exists(index_path), "frontend/index.html not found!"

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Verify HTML Structure (no unclosed tags)
    class HTMLValidator(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack = []
            self.errors = []
        def handle_starttag(self, tag, attrs):
            if tag not in ['input', 'img', 'br', 'hr', 'meta', 'link']:
                self.stack.append(tag)
        def handle_endtag(self, tag):
            if tag not in ['input', 'img', 'br', 'hr', 'meta', 'link']:
                if self.stack and self.stack[-1] == tag:
                    self.stack.pop()
                else:
                    self.errors.append(f"Mismatched tag </{tag}>, top: {self.stack[-1] if self.stack else None}")

    validator = HTMLValidator()
    validator.feed(content)
    assert len(validator.errors) == 0, f"HTML tag mismatch errors: {validator.errors}"
    assert len(validator.stack) == 0, f"Unclosed HTML tags remaining: {validator.stack}"

    # 2. Extract content OUTSIDE of <script>...</script> blocks
    non_script_content = re.sub(r'<script.*?>.*?</script>', '', content, flags=re.DOTALL)

    # 3. Forbidden JS source patterns that MUST NOT appear outside <script> tags
    forbidden_patterns = [
        "function fetchConsensusAudit",
        "function renderConsensusTable",
        "function renderRoleAuditTable",
        "function fetchRoleAudit",
        "async function fetchStateStatus",
        "${p.web_name}",
        "${p.expected_minutes}",
        "${p.total_xp}",
        "document.getElementById",
        "window.addEventListener"
    ]

    for pattern in forbidden_patterns:
        assert pattern not in non_script_content, f"CRITICAL FRONTEND REGRESSION: Raw JavaScript code '{pattern}' found rendered outside <script> tags!"

def test_script_tag_counts_and_boundaries():
    """Verify script tags opening and closing match exactly."""
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    open_scripts = content.count("<script>") + content.count("<script ")
    close_scripts = content.count("</script>")
    assert open_scripts == close_scripts, f"Script tag count mismatch: {open_scripts} opening vs {close_scripts} closing script tags!"
