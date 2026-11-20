"""Ghost-OS Portable Zero-Install Embedded Python Downloader.

Downloads and configures the official 11 MB Python Embeddable runtime for Windows x64
directly into tools/python/ on the USB flash drive.

This makes Ghost-OS 100% self-sufficient and autonomous on ANY Windows 10/11 PC,
even if the host computer has zero development tools and no Python installed.
"""

import os
import sys
import urllib.request
import zipfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"
TARGET_DIR = os.path.join(REPO_ROOT, "tools", "python")


def setup_portable_python(dest_dir: str = TARGET_DIR):
    print("==================================================================")
    print("      GHOST-OS PORTABLE EMBEDDED PYTHON STAGING WIZARD            ")
    print("==================================================================")
    print(f"Destination: {dest_dir}")
    os.makedirs(dest_dir, exist_ok=True)

    zip_path = os.path.join(dest_dir, "python-embed.zip")
    print(f"\n[1/3] Downloading official Python 3.12.8 Embeddable (~11 MB)...")
    print(f"URL: {PYTHON_EMBED_URL}")

    req = urllib.request.Request(PYTHON_EMBED_URL, headers={"User-Agent": "Ghost-OS Installer"})
    with urllib.request.urlopen(req, timeout=30) as resp, open(zip_path, "wb") as f_out:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        while chunk := resp.read(65536):
            f_out.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = (downloaded / total) * 100
                print(f"\r  Downloaded: {downloaded / (1024*1024):.1f} / {total / (1024*1024):.1f} MB ({pct:.1f}%)", end="", flush=True)

    print("\n  ✓ Download complete.")

    print("\n[2/3] Extracting embeddable runtime...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)
    os.remove(zip_path)
    print("  ✓ Extracted portable Python binaries.")

    print("\n[3/3] Configuring python312._pth for site-packages and local imports...")
    pth_file = os.path.join(dest_dir, "python312._pth")
    if os.path.exists(pth_file):
        with open(pth_file, "r") as f:
            content = f.read()

        # Enable 'import site' and add relative search paths
        updated = content.replace("#import site", "import site")
        if "..\..\ghost_core" not in updated:
            updated += "\n.\n..\n..\..\ghost_core\n..\..\ghost_vault\n..\..\ghost_ai\nLib\nsite-packages\n"

        with open(pth_file, "w") as f:
            f.write(updated)
        print("  ✓ Configured isolated sys.path.")

    print("\n==================================================================")
    print("  PORTABLE EMBEDDED PYTHON IS NOW READY ON THE USB DRIVE!         ")
    print("==================================================================")
    print(f"Path: {dest_dir}\\python.exe")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DIR
    setup_portable_python(target)
