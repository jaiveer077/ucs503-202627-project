"""
Re-scans every already-uploaded photo for faces and stores the result.

Why this exists: photos uploaded while face detection was broken (or not
installed yet) were saved with NO face data, so searches can never find
them. Run this once, after face detection works, to fix those photos
without re-uploading anything.

Usage (from the backend folder, with your venv activated):
    python rescan_photos.py
"""

import os

import app  # reuses the same MongoDB connection + settings as the server
import face_matching

if not face_matching.FACE_MATCHING_AVAILABLE:
    raise SystemExit("face_recognition isn't installed in this environment - nothing to scan with.")

total = scanned_ok = with_faces = failed = missing_file = 0

for photo in app.photos.find({}):
    total += 1
    path = os.path.join(app.UPLOAD_ROOT, str(photo["event_id"]), photo["filename"])

    if not os.path.exists(path):
        missing_file += 1
        app.photos.update_one({"_id": photo["_id"]}, {"$set": {
            "scan_status": "missing", "has_face": False, "encodings": []}})
        print(f"  [missing file] {photo['filename']}")
        continue

    try:
        encodings = face_matching.encode_faces_in_image(path)
    except Exception as exc:
        failed += 1
        app.photos.update_one({"_id": photo["_id"]}, {"$set": {
            "scan_status": "failed", "has_face": False, "encodings": []}})
        print(f"  [scan failed]  {photo['filename']}: {exc}")
        continue

    app.photos.update_one(
        {"_id": photo["_id"]},
        {"$set": {"encodings": encodings, "has_face": len(encodings) > 0,
                  "scan_status": "complete"}},
    )
    scanned_ok += 1
    if encodings:
        with_faces += 1
    print(f"  [ok] {photo['filename']}: {len(encodings)} face(s)")

for event in app.events.find({}, {"_id": 1}):
    event_photos = list(app.photos.find({"event_id": event["_id"]},
                                        {"scan_status": 1, "encodings": 1}))
    app.events.update_one({"_id": event["_id"]}, {"$set": {
        "photo_count": len(event_photos),
        "scanned_count": sum(p.get("scan_status") == "complete" for p in event_photos),
        "scan_failure_count": sum(p.get("scan_status") in {"failed", "missing"} for p in event_photos),
        "face_count": sum(len(p.get("encodings", [])) for p in event_photos
                          if p.get("scan_status") == "complete"),
    }})

print()
print(f"Photos in database:        {total}")
print(f"Scanned successfully:      {scanned_ok}")
print(f"  ...of which had faces:   {with_faces}")
print(f"  ...of which had none:    {scanned_ok - with_faces}")
print(f"Scan failed:               {failed}")
print(f"Image file missing:        {missing_file}")
