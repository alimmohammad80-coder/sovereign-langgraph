from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import urlretrieve

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = {
    "ucdp_prio": {
        "url": "https://ucdp.uu.se/downloads/ucdpprio/ucdp-prio-acd-251.csv",
        "filename": "ucdp_prio.csv",
        "version": "25.1",
        "source": "UCDP/PRIO Armed Conflict Dataset",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)

    return h.hexdigest()


manifest = {}

for key, ds in DATASETS.items():

    outfile = RAW_DIR / ds["filename"]

    print(f"Downloading {key}...")
    urlretrieve(ds["url"], outfile)

    manifest[key] = {
        "file": str(outfile),
        "version": ds["version"],
        "source": ds["source"],
        "sha256": sha256(outfile),
    }

    print(f"Saved {outfile}")

manifest_path = RAW_DIR / "manifest.json"

manifest_path.write_text(
    json.dumps(
        manifest,
        indent=2,
    )
)

print()
print("=" * 70)
print("DOWNLOAD COMPLETE")
print("=" * 70)
print(manifest_path)
