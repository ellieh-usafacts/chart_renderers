#!/usr/bin/env python3
"""Generate langsmith_chart_renderer.html from chart.html + the Aeonik woff2.

A LangSmith custom renderer is a single pasted HTML file, so the chart card's
markup and font have to be baked in. This inlines the font into chart.html's
$font_data slot, embeds the result in renderer_shell.html as a JS string, and
leaves $wrapper_data / $chart_data / $flourish_api_key for the renderer to fill
in at runtime from the run's chart_json.

Usage: python3 build_renderer.py
"""

import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CHART_TEMPLATE = ROOT / "chart.html"
FONT = ROOT / "aeonik-medium.woff2"
SHELL = ROOT / "renderer_shell.html"
OUT = ROOT / "langsmith_chart_renderer.html"

MARKER = '"__CHART_TEMPLATE__"'
# Filled here, at build time.
BUILD_TIME_VARS = ["font_data"]
# Left in the template for renderer_shell.html to fill per run.
RUNTIME_VARS = ["wrapper_data", "chart_data", "flourish_api_key"]

BANNER = (
    "<!-- GENERATED FILE — do not edit by hand.\n"
    "     Built from chart.html + aeonik-medium.woff2 + renderer_shell.html\n"
    "     by build_renderer.py. Edit those and re-run: python3 build_renderer.py -->"
)


def die(message):
    sys.exit("build_renderer: " + message)


def main():
    for path in (CHART_TEMPLATE, FONT, SHELL):
        if not path.exists():
            die("missing input {}".format(path.name))

    template = CHART_TEMPLATE.read_text(encoding="utf-8")
    shell = SHELL.read_text(encoding="utf-8")

    for name in BUILD_TIME_VARS + RUNTIME_VARS:
        if not re.search(r"\$" + name + r"\b", template):
            die("chart.html is missing the ${} placeholder".format(name))
    if MARKER not in shell:
        die("renderer_shell.html is missing the {} marker".format(MARKER))

    font_b64 = base64.b64encode(FONT.read_bytes()).decode("ascii")

    # Function replacement so nothing in the substituted value is treated as a
    # capture reference, and so the injected value is never rescanned.
    filled = re.sub(r"\$font_data\b", lambda m: font_b64, template)

    # json.dumps escapes quotes, backslashes and newlines into a valid JS string
    # literal; escaping "</" keeps the embedded markup from closing the shell's
    # own <script> block.
    literal = json.dumps(filled).replace("</", "<\\/")

    rendered = shell.replace(MARKER, literal)

    # A literal closing script tag anywhere in the output ends the shell's script
    # element early — even inside a JS comment or string.
    closer = "</" + "script>"
    if rendered.count(closer) != 1:
        die("expected exactly 1 literal {} in the output, found {} — check "
            "renderer_shell.html and the \"</\" escaping".format(closer, rendered.count(closer)))

    lines = rendered.split("\n")
    lines.insert(1, BANNER)
    rendered = "\n".join(lines)

    OUT.write_text(rendered, encoding="utf-8")
    print("wrote {} ({:,} bytes; font {:,} B -> {:,} B base64)".format(
        OUT.name, len(rendered.encode("utf-8")), FONT.stat().st_size, len(font_b64)))


if __name__ == "__main__":
    main()
