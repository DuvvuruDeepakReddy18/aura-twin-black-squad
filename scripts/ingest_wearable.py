"""Download only the public research signals used by AURA; verify publisher hashes.

Raw CSVs stay in ignored work/. Never interpret Dexcom export identity/header rows.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import json
import shutil
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://physionet.org/files/big-ideas-glycemic-wearable/1.1.3/"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(name, raw, expected=None):
    path = raw / name
    # v1.1.3 changed food logs only. The official public v1.1.2 S3 mirror is
    # usable for signals only when bytes match v1.1.3 publisher checksums exactly.
    url = ("https://physionet-open.s3.amazonaws.com/big-ideas-glycemic-wearable/1.1.2/"+name
           if "/" in name else BASE+name)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and (expected is None or sha(path) == expected):
        return {"file": name, "sha256": sha(path), "bytes": path.stat().st_size,
                "url": BASE + name, "downloadUrl":url, "publisherHashVerified": expected is not None}
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as response, path.with_suffix(".part").open("wb") as out:
                shutil.copyfileobj(response, out, length=65536)
            path.with_suffix(".part").replace(path)
            digest = sha(path)
            if expected and digest != expected:
                raise ValueError(f"Publisher SHA256 mismatch: {name}")
            return {"file": name, "sha256": digest, "bytes": path.stat().st_size,
                    "url": BASE + name, "downloadUrl":url, "publisherHashVerified": expected is not None}
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default=str(ROOT / "work" / "big-ideas-1.1.3"))
    args = parser.parse_args()
    raw = Path(args.raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    checksum = download("SHA256SUMS.txt", raw)
    hashes = {}
    for line in (raw / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        hashes[name.lstrip("*./")] = digest
    names = ["Demographics.csv", "LICENSE.txt"]
    names += [f"{i:03}/{signal}_{i:03}.csv" for i in range(1, 17)
              for signal in ["Dexcom", "HR", "IBI"]]
    items = [checksum]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(download, name, raw, hashes.get(name)): name for name in names}
        for future in as_completed(futures):
            item = future.result()
            items.append(item)
            print(f"Verified {item['file']} ({item['bytes']:,} bytes)", flush=True)
    (raw / "download-manifest.json").write_text(json.dumps(
        {"datasetVersion": "1.1.3", "source": BASE, "files": sorted(items, key=lambda item: item["file"])},
        indent=2), encoding="utf-8")
    print("Download complete; all selected signal files verified against publisher SHA256SUMS.", flush=True)


if __name__ == "__main__":
    main()
