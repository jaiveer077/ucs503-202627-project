"""
Moves photos that are still on local disk into Google Cloud Storage.

Run this ONCE after Google Cloud is configured (python app.py's /api/health
should show "cloud_storage_configured": true). New uploads already go to
the cloud automatically; this is only for photos uploaded before that.

It's safe to run more than once - photos already in the cloud are skipped,
and the local copy is NEVER deleted (so nothing can be lost).

Usage (backend folder, venv activated):
    python migrate_to_gcs.py
"""

import os

import app
import cloud_storage

if not cloud_storage.is_configured():
    raise SystemExit(
        "Google Cloud isn't configured yet. Check GCS_BUCKET_NAME and "
        "GOOGLE_APPLICATION_CREDENTIALS in .env, and that the key file exists."
    )

moved = skipped = failed = missing = 0

for photo in app.photos.find({}):
    if photo.get("storage_type") == "gcs":
        skipped += 1
        continue

    event_id = str(photo["event_id"])
    path = os.path.join(app.UPLOAD_ROOT, event_id, photo["filename"])
    if not os.path.exists(path):
        missing += 1
        print(f"  [missing file] {photo['filename']}")
        continue

    try:
        url = cloud_storage.upload_photo(path, event_id, photo["filename"])
    except Exception as exc:
        failed += 1
        print(f"  [failed]       {photo['filename']}: {exc}")
        continue

    app.photos.update_one({"_id": photo["_id"]}, {"$set": {"url": url, "storage_type": "gcs"}})
    moved += 1
    print(f"  [moved]        {photo['filename']}")

print()
print(f"Moved to Google Cloud:      {moved}")
print(f"Already in the cloud:       {skipped}")
print(f"Failed:                     {failed}")
print(f"Local file missing:         {missing}")
if failed:
    print("\nIf everything failed with a 403 or 'forbidden' error, the service account")
    print("is missing the 'Storage Object Admin' role on the bucket - see the setup guide.")
