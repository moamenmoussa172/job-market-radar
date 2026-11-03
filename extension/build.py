"""Package the Radarak Apply extension.

    python extension/build.py

writes extension/dist/radarak-apply-<version>.zip (upload this to the Chrome Web Store, Edge Add-ons and
Firefox Add-ons: the same zip works in all three) and site/extension/radarak-apply.zip (the download link
on radarak.online/extension/).
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ["manifest.json", "popup.html", "popup.css", "popup.js", "src/common.js", "src/radarak.js", "src/fill.js",
         "icons/icon-16.png", "icons/icon-32.png", "icons/icon-48.png", "icons/icon-128.png"]


def build() -> list[Path]:
    version = json.loads((HERE / "manifest.json").read_text())["version"]
    outs = [HERE / "dist" / f"radarak-apply-{version}.zip", HERE.parent / "site" / "extension" / "radarak-apply.zip"]
    for out in outs:
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in FILES:
                info = zipfile.ZipInfo(f, date_time=(2026, 1, 1, 0, 0, 0))   # same bytes every build
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, (HERE / f).read_bytes())
    return outs


if __name__ == "__main__":
    for p in build():
        print(p)
