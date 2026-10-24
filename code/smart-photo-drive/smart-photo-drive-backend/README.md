# Smart Photo Drive backend

Flask serves manager and attendee accounts, event management, uploads, face search, and controlled photo delivery. MongoDB stores accounts, events, photo metadata, and face encodings. Original photos are stored on local disk, or optionally in a private Google Cloud Storage bucket.

## Local setup

Use Python 3.12. Copy `.env.example` to `.env`, then set `MONGO_URI` and a long random `JWT_SECRET`. Set `FRONTEND_ORIGIN` if the frontend is not served from `http://localhost:5173`. MongoDB must be reachable when Flask starts because the app creates indexes at startup.

On Linux x86-64, this installation was used for the manual end-to-end run:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install 'setuptools<81' dlib-bin==20.0.1.post1 face_recognition_models==0.3.0
pip install --no-deps face_recognition==1.3.0
python app.py
```

`dlib-bin` supplies a prebuilt dlib binary; `--no-deps` prevents pip from trying to compile the source `dlib` package again. Other platforms may need a suitable prebuilt dlib package or a C++ build environment. On Windows, a conda environment with `conda install -c conda-forge dlib` followed by `pip install -r requirements.txt 'setuptools<81' face_recognition` is an alternative.

Check `http://localhost:5000/api/health`. `face_matching_available` must be `true` for search to work. If you uploaded photos before face matching was available, run `python rescan_photos.py` after installation.

## Workflow

1. Register or sign in as a manager; create an event and upload PNG, JPEG, or WebP files.
2. Upload processing validates each image, detects every face, and stores its 128-number encoding in MongoDB. The manager dashboard shows scanned photo and detected face counts. Invalid files and scan failures are reported.
3. Register or sign in as an attendee; choose an event and submit a reference photo showing exactly one face.
4. The backend compares that face against saved encodings for the event. A face distance of at most 0.6 is treated as a match by default. Set `FACE_MATCH_THRESHOLD` in `.env` to tune this cutoff after reviewing a labeled photo set; a lower value is stricter. Search results contain short-lived photo links, valid for one hour. The match score shown in the UI is derived from distance and is not a calibrated probability.

The public event listing exposes event details but no original photographs. Only a manager can list their event photos. Attendees receive links to matching photos only after a successful search. Direct `/uploads/` access is disabled. Existing Google Cloud Storage buckets must have public access disabled; application code cannot undo public bucket permissions. Keep service account keys outside any public directory.

## API

- `POST /api/manager/register`, `POST /api/manager/login`
- `POST /api/user/register`, `POST /api/user/login`
- `GET /api/events?q=...&page=1&page_size=12` — public event search, with pages of up to 100
- `GET /api/events/<id>` — public event details
- `GET /api/manager/events` — manager's events and private cover links
- `POST /api/manager/events` — create an event
- `POST /api/manager/events/<id>/photos` — manager upload (`photos` multipart field)
- `GET /api/events/<id>/photos` — owning manager only
- `POST /api/user/events/<id>/search` — attendee face search (`reference` multipart field)
- `GET /api/photos/<id>/file?token=...` — short-lived photo link
- `DELETE /api/manager/events/<id>` — remove event and its photos

Requests are limited to 80 MB; individual images are limited to 20 MB and 40 megapixels. The frontend sends uploads in groups of three. Search result links expire, so repeat the search to get fresh links.

## Optional cloud storage

Set `GCS_BUCKET_NAME` and `GOOGLE_APPLICATION_CREDENTIALS` in `.env` and give the service account object read/write permissions on a private bucket. New uploads use that bucket when configured; a failed cloud upload leaves the local copy available and reports the failure. `python migrate_to_gcs.py` moves existing local photos. Cloud downloads use signed URLs. The code keeps local copies of new uploads so a failed cloud request cannot lose the original.
