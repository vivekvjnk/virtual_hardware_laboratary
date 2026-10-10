from evaluator.sanitizer import sanitize_ansi, sanitize_lines


def test_sanitize_ansi_colors():
    raw = "\x1b[31mError:\x1b[0m \x1b[33mWarning in line 12\x1b[39m"
    clean = sanitize_ansi(raw)
    assert clean == "Error: Warning in line 12"


def test_sanitize_ansi_cursor_moves():
    raw = "\x1b[1A\x1b[0KBuilding 1 file(s)...\r\n\x1b[2KDone."
    clean = sanitize_ansi(raw)
    assert "Building 1 file(s)..." in clean
    assert "Done." in clean
    assert "\x1b" not in clean


def test_sanitize_lines():
    lines = [
        "   \x1b[32m✔ Built successfully\x1b[0m   ",
        "",
        "   ",
        "\x1b[31mFailed\x1b[0m\r",
    ]
    cleaned = sanitize_lines(lines)
    assert cleaned == ["✔ Built successfully", "Failed"]
