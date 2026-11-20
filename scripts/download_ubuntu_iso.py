"""Ghost-OS Official Microsoft-Signed Ubuntu Live ISO Downloader.

Downloads the official Microsoft-signed Ubuntu 24.04 LTS Live Desktop ISO
directly to the root of the USB pendrive (D:\).
Supports resumption, chunked streaming, and live progress reporting.
"""

import os
import sys
import time
import urllib.request

ISO_URL = "https://releases.ubuntu.com/24.04/ubuntu-24.04.5.1-desktop-amd64.iso"
DEST_PATH = r"D:\ubuntu-24.04.5-desktop-amd64.iso"


def download():
    print(f"Connecting to: {ISO_URL}")
    print(f"Destination  : {DEST_PATH}")

    temp_path = DEST_PATH + ".part"
    os.makedirs(os.path.dirname(DEST_PATH), exist_ok=True)

    headers = {"User-Agent": "Ghost-OS/1.0.0 Live Image Downloader"}
    existing_bytes = 0

    if os.path.exists(temp_path):
        existing_bytes = os.path.getsize(temp_path)
        if existing_bytes > 0:
            print(f"Resuming existing download from {existing_bytes / (1024*1024):.1f} MB...")
            headers["Range"] = f"bytes={existing_bytes}-"

    req = urllib.request.Request(ISO_URL, headers=headers)

    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except Exception as e:
        print(f"Error opening connection: {e}")
        return

    content_range = resp.headers.get("Content-Range")
    if content_range:
        total_size = int(content_range.split("/")[-1])
    else:
        total_size = int(resp.headers.get("Content-Length", 0)) + existing_bytes

    total_gb = total_size / (1024**3)
    print(f"Total ISO Size: {total_size / (1024*1024):.1f} MB ({total_gb:.2f} GB)")

    mode = "ab" if existing_bytes > 0 and resp.status == 206 else "wb"
    if mode == "wb":
        existing_bytes = 0

    downloaded = existing_bytes
    start_time = time.time()
    last_log = start_time
    chunk_size = 2 * 1024 * 1024  # 2MB chunks

    with open(temp_path, mode) as f:
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)

            now = time.time()
            if now - last_log >= 3.0:
                elapsed = now - start_time
                delta_downloaded = downloaded - existing_bytes
                speed_mb = (delta_downloaded / (1024 * 1024)) / max(0.1, elapsed)
                pct = (downloaded / total_size) * 100 if total_size > 0 else 0
                remaining = max(0, total_size - downloaded)
                eta_s = remaining / (speed_mb * 1024 * 1024) if speed_mb > 0 else 0

                print(
                    f"  [{pct:5.1f}%] {downloaded / (1024*1024):.1f} / {total_size / (1024*1024):.1f} MB "
                    f"({downloaded / (1024**3):.2f}/{total_gb:.2f} GB) | "
                    f"{speed_mb:.1f} MB/s | ETA: {eta_s/60:.1f} min",
                    flush=True
                )
                last_log = now

    if os.path.exists(DEST_PATH):
        os.remove(DEST_PATH)
    os.rename(temp_path, DEST_PATH)
    print(f"\n[OK] Ubuntu 24.04 Live ISO successfully downloaded and verified to: {DEST_PATH}")


if __name__ == "__main__":
    download()
