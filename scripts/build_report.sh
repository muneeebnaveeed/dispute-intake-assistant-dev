#!/bin/sh
# docs/report.md → docs/report.pdf: pandoc renders HTML, headless Chrome prints it to PDF.
# Needs pandoc and Google Chrome/Chromium on the host (no LaTeX install required).
set -e
cd "$(dirname "$0")/.."
CHROME="${CHROME:-$(command -v google-chrome || command -v chromium || echo /opt/google/chrome/chrome)}"
pandoc docs/report.md --standalone --embed-resources --css docs/report.css \
    --metadata lang=en -o docs/report.html
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
    --user-data-dir="$(mktemp -d)" --print-to-pdf=docs/report.pdf "file://$PWD/docs/report.html"
rm docs/report.html
echo "wrote docs/report.pdf"
