"""Manages temporary files generated during the pipeline."""

import os
import sys
import shutil

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

TMP_DIR = ".tmp"


def cleanup(keep_output=True):
    if os.path.exists(TMP_DIR):
        total_size = 0
        file_count = 0
        for root, dirs, files in os.walk(TMP_DIR):
            for f in files:
                fp = os.path.join(root, f)
                total_size += os.path.getsize(fp)
                file_count += 1

        size_mb = total_size / (1024 * 1024)

        shutil.rmtree(TMP_DIR)
        print(f"✅ Cleaned up {file_count} files ({size_mb:.1f} MB) from {TMP_DIR}/")
    else:
        print("ℹ️  No temporary files to clean up")


def cleanup_media_only():
    media_dir = os.path.join(TMP_DIR, "media")
    if os.path.exists(media_dir):
        count = len(os.listdir(media_dir))
        shutil.rmtree(media_dir)
        print(f"✅ Cleaned up {count} media files from {media_dir}/")
    else:
        print("ℹ️  No media files to clean up")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"

    if arg == "media":
        cleanup_media_only()
    else:
        cleanup()
