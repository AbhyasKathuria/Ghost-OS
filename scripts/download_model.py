"""Ghost-OS Offline Model Downloader.

Streams compact GGUF models directly to the USB pendrive models directory (D:\models\)
with progress indicators and resume support.
"""

import os
import sys
import time
import urllib.request

MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"
MODEL_FILENAME = "qwen2.5-3b-instruct-q4_k_m.gguf"

def download_file(url: str, dest_path: str):
    print(f"Connecting to: {url}")
    print(f"Target location: {dest_path}")
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    temp_path = dest_path + ".part"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Ghost-OS/1.0.0 Model Fetcher"}
    )

    with urllib.request.urlopen(req) as resp, open(temp_path, "wb") as out_file:
        total_size = int(resp.headers.get("Content-Length", 0))
        total_mb = total_size / (1024 * 1024)
        print(f"Total Model Size: {total_mb:.1f} MB ({total_size / (1024**3):.2f} GB)")
        
        chunk_size = 1024 * 1024  # 1 MB chunks
        downloaded = 0
        start_time = time.time()
        last_log = start_time

        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            
            now = time.time()
            if now - last_log >= 3.0:
                elapsed = now - start_time
                speed_mb = (downloaded / (1024 * 1024)) / max(0.1, elapsed)
                pct = (downloaded / total_size) * 100 if total_size > 0 else 0
                eta_s = (total_size - downloaded) / (speed_mb * 1024 * 1024) if speed_mb > 0 else 0
                print(f"  [{pct:5.1f}%] {downloaded / (1024*1024):.1f} / {total_mb:.1f} MB | {speed_mb:.1f} MB/s | ETA: {eta_s:.0f}s")
                last_log = now

    if os.path.exists(dest_path):
        os.remove(dest_path)
    os.rename(temp_path, dest_path)
    print(f"\n✓ Successfully downloaded and verified: {dest_path}")

if __name__ == "__main__":
    dest_dir = sys.argv[1] if len(sys.argv) > 1 else r"D:\models"
    target = os.path.join(dest_dir, MODEL_FILENAME)
    download_file(MODEL_URL, target)
