"""Step 1: download the raw data files.

Run from the coolgap folder:
    python -m src.load_data

Each file is saved in data/raw/ exactly as the source gave it. Raw files are
never edited. A log (data/raw/download_log.json) records the link, the date,
and the file size for every download, so the sources can be checked later.

If a download fails, the script stops with an error. It never swaps in a
different dataset and never makes up data.
"""
import json
import re
import sys
from datetime import date

import requests

from src import config


def download_one(key: str, force: bool = False) -> dict:
    """Download one dataset named in config.SOURCES and return a log entry."""
    source = config.SOURCES[key]
    path = config.RAW_DIR / source["file"]

    if path.exists() and not force:
        print(f"  already have {source['file']}, skipping")
        return {}

    print(f"  downloading {key} ...")
    if "keep_rows_starting_with" in source:
        return download_filtered(key, source, path)

    response = requests.get(source["url"], timeout=120)
    response.raise_for_status()  # stop here if the link is broken

    content = response.content
    if len(content) < 200:
        raise RuntimeError(f"{key}: the file is almost empty, something is wrong")

    # Some services answer with an error message or a web page instead of data.
    start = content[:300].decode("utf-8", errors="ignore")
    if '"error"' in start:
        raise RuntimeError(f"{key}: the server returned an error: {start}")
    if start.lstrip().lower().startswith(("<html", "<!doctype")):
        title = re.search(r"<title>(.*?)</title>", start, re.S)
        reason = title.group(1).strip() if title else "unknown reason"
        raise RuntimeError(f"{key}: got a web page instead of data ({reason})")

    # The ArcGIS service can cut a download short. Stop if that happened.
    if b'"exceededTransferLimit":true' in content.replace(b" ", b""):
        raise RuntimeError(f"{key}: the download was cut short by the server")

    path.write_bytes(content)
    return {
        "file": source["file"],
        "publisher": source["publisher"],
        "url": source["url"],
        "downloaded": date.today().isoformat(),
        "bytes": len(content),
    }


def download_filtered(key: str, source: dict, path) -> dict:
    """Download a very large text file but keep only some of its rows.

    The file is read one line at a time, so it never has to fit in memory.
    The first line (column names) is kept, plus every line that starts with
    the given text. Kept lines are written exactly as they arrived.
    """
    prefix = source["keep_rows_starting_with"]
    kept = []
    with requests.get(source["url"], stream=True, timeout=300) as response:
        response.raise_for_status()
        response.encoding = "utf-8"
        for number, line in enumerate(response.iter_lines(decode_unicode=True)):
            if number == 0:
                if not line.startswith("GEO_ID"):
                    raise RuntimeError(f"{key}: the file does not look right: {line[:80]}")
                kept.append(line)
            elif line.startswith(prefix):
                kept.append(line)

    if len(kept) < 2:
        raise RuntimeError(f"{key}: no rows matched {prefix}")

    text = "\n".join(kept) + "\n"
    path.write_text(text, encoding="utf-8")
    return {
        "file": source["file"],
        "publisher": source["publisher"],
        "url": source["url"],
        "downloaded": date.today().isoformat(),
        "bytes": len(text.encode("utf-8")),
        "note": f"Row filter: kept the header and {len(kept) - 1} rows "
                f"starting with {prefix}. Kept rows are unchanged.",
    }


def download_all(force: bool = False) -> None:
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    log_path = config.RAW_DIR / "download_log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}

    failures = []
    for key in config.SOURCES:
        try:
            entry = download_one(key, force=force)
        except Exception as error:  # keep going, but report it loudly below
            failures.append(f"{key}: {error}")
            continue
        if entry:
            log[key] = entry

    log_path.write_text(json.dumps(log, indent=2))
    print(f"Log saved to {log_path}")

    if failures:
        print("STOP: these datasets did NOT download. Nothing was substituted.")
        for line in failures:
            print("  -", line)
        sys.exit(1)
    print("All datasets downloaded.")


if __name__ == "__main__":
    download_all(force="--force" in sys.argv)
