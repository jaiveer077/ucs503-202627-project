"""
Optional Google Cloud Storage upload for event photos.

If the library or bucket credentials are unavailable, photos remain on local
disk. The app serves them through expiring photo links after an authorized
search; it asks is_configured() before trying Google Cloud Storage.
"""

import os
import datetime

from dotenv import load_dotenv

try:
    from google.cloud import storage
    GCS_LIBRARY_AVAILABLE = True
except ImportError:
    GCS_LIBRARY_AVAILABLE = False

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Load .env here too. app.py imports this module BEFORE it calls
# load_dotenv(), so without this the settings below would be read too
# early and a correctly filled-in .env would be silently ignored.
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

_client = None


def _bucket_name():
    return os.environ.get("GCS_BUCKET_NAME") or None


def _credentials_path():
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not path:
        return None
    # Allow a relative path like "gcs-credentials.json" (relative to this
    # folder, not to whatever directory the server happened to start in).
    return path if os.path.isabs(path) else os.path.join(BACKEND_DIR, path)


def is_configured():
    creds = _credentials_path()
    return (
        GCS_LIBRARY_AVAILABLE
        and _bucket_name() is not None
        and creds is not None
        and os.path.exists(creds)
    )


def _get_client():
    global _client
    if _client is None:
        # The Google library finds the key file through this variable, so
        # point it at the resolved absolute path.
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _credentials_path()
        _client = storage.Client()
    return _client


def upload_photo(local_path, event_id, filename):
    """
    Uploads one file to gs://<bucket>/<event_id>/<filename>. Returns its
    storage URL (which is never sent to unauthenticated users). Raises on failure - callers catch this and fall back to
    local storage rather than losing the upload.
    """
    bucket = _get_client().bucket(_bucket_name())
    blob = bucket.blob(f"{event_id}/{filename}")
    blob.upload_from_filename(local_path)
    # Keep the bucket private; downloads use short-lived signed URLs.
    return blob.public_url


def signed_download_url(event_id, filename, download=False):
    """Issue a short-lived URL for a private cloud photo."""
    blob = _get_client().bucket(_bucket_name()).blob(f"{event_id}/{filename}")
    options = {"response_disposition": "attachment"} if download else {}
    return blob.generate_signed_url(version="v4", expiration=datetime.timedelta(minutes=60), method="GET", **options)


def delete_photo(event_id, filename):
    """Removes one photo from the bucket. Raises on failure."""
    _get_client().bucket(_bucket_name()).blob(f"{event_id}/{filename}").delete()
