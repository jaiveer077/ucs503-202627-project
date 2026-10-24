import os
import shutil
import datetime
import uuid
import re
from functools import wraps

import bcrypt
import jwt
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from PIL import Image
from werkzeug.utils import secure_filename

import face_matching
import cloud_storage

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": [origin.strip() for origin in
    os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]}})

MONGO_URI = os.environ.get("MONGO_URI")
JWT_SECRET = os.environ.get("JWT_SECRET")
if not MONGO_URI or not JWT_SECRET:
    raise RuntimeError("Set MONGO_URI and JWT_SECRET in the backend .env before starting the server")
JWT_EXPIRY_HOURS = 12
PHOTO_LINK_EXPIRY_MINUTES = 60
UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_PHOTO_BYTES = 20 * 1024 * 1024
MAX_PHOTO_PIXELS = 40_000_000
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024
os.makedirs(UPLOAD_ROOT, exist_ok=True)

client = MongoClient(MONGO_URI)
db = client["smart_photo_drive"]
users = db["users"]
managers = db["managers"]
events = db["events"]
photos = db["photos"]

users.create_index("email", unique=True)
managers.create_index("email", unique=True)
events.create_index("manager_id")
photos.create_index([("event_id", 1), ("has_face", 1)])


def hash_password(plain: str) -> bytes:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())


def check_password(plain: str, hashed) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed)


def make_token(user_id: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _require_role(required_role, id_attr):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Missing or malformed Authorization header"}), 401
            token = auth_header.split(" ", 1)[1]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Session expired, please log in again"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401

            if payload.get("role") != required_role:
                return jsonify({"error": f"{required_role.capitalize()} account required"}), 403

            setattr(request, id_attr, payload["sub"])
            return f(*args, **kwargs)
        return wrapper
    return decorator


require_manager = _require_role("manager", "manager_id")
require_user = _require_role("user", "user_id")


def photo_access_url(doc):
    token = jwt.encode(
        {"type": "photo", "photo_id": str(doc["_id"]),
         "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=PHOTO_LINK_EXPIRY_MINUTES)},
        JWT_SECRET, algorithm="HS256",
    )
    return f"/api/photos/{doc['_id']}/file?token={token}"


def serialize_event(doc, include_cover=False):
    cover = None
    if include_cover:
        first = photos.find_one({"event_id": doc["_id"]}, {"_id": 1})
        cover = photo_access_url(first) if first else None
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "date": doc.get("date", ""),
        "location": doc.get("location", ""),
        "photoCount": doc.get("photo_count", 0),
        "scannedCount": doc.get("scanned_count"),
        "scanFailureCount": doc.get("scan_failure_count"),
        "faceCount": doc.get("face_count"),
        "cover": cover,
    }


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def image_error(path):
    if os.path.getsize(path) > MAX_PHOTO_BYTES:
        return "image exceeds 20 MB"
    try:
        with Image.open(path) as image:
            if image.width * image.height > MAX_PHOTO_PIXELS:
                return "image exceeds 40 megapixels"
            image.verify()
    except Exception:
        return "invalid image"
    return None


@app.errorhandler(413)
def upload_too_large(_error):
    return jsonify({"error": "Upload exceeds the 80 MB request limit; upload fewer photos at once."}), 413


def register(collection, role):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are all required"}), 400

    try:
        result = collection.insert_one(
            {"name": name, "email": email, "password": hash_password(password)}
        )
    except DuplicateKeyError:
        return jsonify({"error": "An account with that email already exists"}), 409

    token = make_token(result.inserted_id, role)
    return jsonify({"token": token, "name": name, "email": email, "role": role}), 201


def login(collection, role):
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    account = collection.find_one({"email": email})
    if not account or not check_password(password, account["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = make_token(account["_id"], role)
    return jsonify(
        {"token": token, "name": account["name"], "email": account["email"], "role": role}
    ), 200


@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "face_matching_available": face_matching.FACE_MATCHING_AVAILABLE,
            "face_match_threshold": face_matching.MATCH_THRESHOLD,
            "cloud_storage_configured": cloud_storage.is_configured(),
        }
    )


@app.post("/api/user/register")
def user_register():
    return register(users, "user")


@app.post("/api/user/login")
def user_login():
    return login(users, "user")


@app.post("/api/manager/register")
def manager_register():
    return register(managers, "manager")


@app.post("/api/manager/login")
def manager_login():
    return login(managers, "manager")


# ---------------------------------------------------------------------------
# Event management
# ---------------------------------------------------------------------------

@app.get("/api/events")
def list_events():
    query = (request.args.get("q") or "").strip()
    if len(query) > 100:
        return jsonify({"error": "Search query is too long"}), 400
    try:
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("page_size", "12"))
    except ValueError:
        return jsonify({"error": "page and page_size must be numbers"}), 400
    if page < 1 or not 1 <= page_size <= 100:
        return jsonify({"error": "page must be positive and page_size must be between 1 and 100"}), 400
    filters = {}
    if query:
        pattern = {"$regex": re.escape(query), "$options": "i"}
        filters["$or"] = [{"name": pattern}, {"location": pattern}]
    total = events.count_documents(filters)
    docs = events.find(filters).sort("_id", -1).skip((page - 1) * page_size).limit(page_size)
    return jsonify({"events": [serialize_event(d) for d in docs], "total": total,
                    "page": page, "page_size": page_size}), 200


@app.get("/api/manager/events")
@require_manager
def list_my_events():
    # Only the events THIS manager created (the public /api/events lists everyone's).
    docs = events.find({"manager_id": request.manager_id}).sort("_id", -1)
    return jsonify([serialize_event(d, include_cover=True) for d in docs]), 200


@app.delete("/api/manager/events/<event_id>")
@require_manager
def delete_event(event_id):
    try:
        oid = ObjectId(event_id)
    except InvalidId:
        return jsonify({"error": "Invalid event id"}), 400

    event = events.find_one({"_id": oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    if str(event.get("manager_id")) != str(request.manager_id):
        return jsonify({"error": "You don't manage this event"}), 403

    # Best-effort removal of any photos that were sent to the cloud.
    for photo in photos.find({"event_id": oid, "storage_type": "gcs"}):
        try:
            cloud_storage.delete_photo(str(oid), photo["filename"])
        except Exception as exc:
            app.logger.error("Could not delete %s from cloud: %s", photo["filename"], exc)

    removed = photos.delete_many({"event_id": oid}).deleted_count
    # event_id was validated as an ObjectId above, so this path can't escape uploads/
    shutil.rmtree(os.path.join(UPLOAD_ROOT, str(oid)), ignore_errors=True)
    events.delete_one({"_id": oid})
    return jsonify({"deleted": True, "photos_removed": removed}), 200


@app.get("/api/events/<event_id>")
def get_event(event_id):
    try:
        doc = events.find_one({"_id": ObjectId(event_id)})
    except InvalidId:
        return jsonify({"error": "Invalid event id"}), 400
    if not doc:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(serialize_event(doc)), 200


@app.get("/api/events/<event_id>/photos")
@require_manager
def list_event_photos(event_id):
    try:
        oid = ObjectId(event_id)
    except InvalidId:
        return jsonify({"error": "Invalid event id"}), 400
    event = events.find_one({"_id": oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    if str(event.get("manager_id")) != str(request.manager_id):
        return jsonify({"error": "You don't manage this event"}), 403
    docs = photos.find({"event_id": oid}, {"filename": 1})
    return jsonify([{"filename": d["filename"], "url": photo_access_url(d)} for d in docs]), 200


@app.post("/api/manager/events")
@require_manager
def create_event():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    date = (data.get("date") or "").strip()
    location = (data.get("location") or "").strip()

    if not name:
        return jsonify({"error": "Event name is required"}), 400

    result = events.insert_one(
        {
            "name": name,
            "date": date,
            "location": location,
            "manager_id": request.manager_id,
            "photo_count": 0,
            "scanned_count": 0,
            "scan_failure_count": 0,
            "face_count": 0,
        }
    )
    doc = events.find_one({"_id": result.inserted_id})
    return jsonify(serialize_event(doc)), 201


# ---------------------------------------------------------------------------
# Bulk photo upload - also encodes faces at upload time (not per-search),
# matching the "precompute once, search many times" pipeline from the
# proposal.
# ---------------------------------------------------------------------------

@app.post("/api/manager/events/<event_id>/photos")
@require_manager
def upload_event_photos(event_id):
    try:
        oid = ObjectId(event_id)
    except InvalidId:
        return jsonify({"error": "Invalid event id"}), 400

    event = events.find_one({"_id": oid})
    if not event:
        return jsonify({"error": "Event not found"}), 404
    if str(event.get("manager_id")) != str(request.manager_id):
        return jsonify({"error": "You don't manage this event"}), 403

    files = request.files.getlist("photos")
    if not files:
        return jsonify({"error": "No files were sent (field name should be 'photos')"}), 400

    event_dir = os.path.join(UPLOAD_ROOT, event_id)
    os.makedirs(event_dir, exist_ok=True)

    saved_count = 0
    skipped = []
    faces_found_total = 0
    scanned_count = 0
    scan_failures = []  # photos that were saved but whose face scan crashed
    cloud_failures = []  # photos that stayed on local disk because the cloud upload failed

    for f in files:
        if not f.filename or not allowed_file(f.filename):
            skipped.append(f.filename or "unnamed")
            continue

        ext = f.filename.rsplit(".", 1)[1].lower()
        unique_name = secure_filename(f"{uuid.uuid4().hex}.{ext}")
        full_path = os.path.join(event_dir, unique_name)
        f.save(full_path)
        validation_error = image_error(full_path)
        if validation_error:
            os.remove(full_path)
            skipped.append(f"{f.filename} ({validation_error})")
            continue

        encodings = []
        scan_failed = False
        if face_matching.FACE_MATCHING_AVAILABLE:
            try:
                encodings = face_matching.encode_faces_in_image(full_path)
            except Exception as exc:
                # Don't let one bad image break the whole upload - but DO
                # make the failure visible instead of hiding it.
                encodings = []
                scan_failed = True
                scan_failures.append(f.filename)
                app.logger.error("Face scan failed for %s: %s", f.filename, exc)
            else:
                scanned_count += 1

        # Try Google Cloud Storage first; always fall back to serving the
        # local copy if GCS isn't configured or the upload fails for any
        # reason - an upload should never be lost just because the cloud
        # storage step had a problem.
        storage_type = "local"
        url = f"/uploads/{event_id}/{unique_name}"
        if cloud_storage.is_configured():
            try:
                url = cloud_storage.upload_photo(full_path, event_id, unique_name)
                storage_type = "gcs"
            except Exception as exc:
                # Keep the local url/storage_type set above so the upload
                # isn't lost - but make the failure visible, not silent.
                cloud_failures.append(f.filename)
                app.logger.error("Cloud upload failed for %s: %s", f.filename, exc)

        photos.insert_one(
            {
                "event_id": oid,
                "filename": unique_name,
                "url": url,
                "storage_type": storage_type,
                "has_face": len(encodings) > 0,
                "scan_status": "failed" if scan_failed else ("complete" if face_matching.FACE_MATCHING_AVAILABLE else "pending"),
                "encodings": encodings,
                "uploaded_at": datetime.datetime.utcnow(),
            }
        )
        saved_count += 1
        faces_found_total += len(encodings)

    if saved_count:
        events.update_one({"_id": oid}, {"$inc": {"photo_count": saved_count,
            "scanned_count": scanned_count, "scan_failure_count": len(scan_failures),
            "face_count": faces_found_total}})
    doc = events.find_one({"_id": oid})
    return jsonify(
        {
            "event": serialize_event(doc, include_cover=True),
            "uploaded": saved_count,
            "skipped": skipped,
            "faces_found": faces_found_total,
            "scan_failures": scan_failures,
            "cloud_failures": cloud_failures,
            "face_matching_available": face_matching.FACE_MATCHING_AVAILABLE,
            "cloud_storage_configured": cloud_storage.is_configured(),
        }
    ), 200


# ---------------------------------------------------------------------------
# Face search - a logged-in user uploads a reference photo, we compare it
# against every face found in this event's photos.
# ---------------------------------------------------------------------------

@app.post("/api/user/events/<event_id>/search")
@require_user
def search_event(event_id):
    if not face_matching.FACE_MATCHING_AVAILABLE:
        return jsonify(
            {"error": "Face matching isn't installed on this server yet. See backend README."}
        ), 501

    try:
        oid = ObjectId(event_id)
    except InvalidId:
        return jsonify({"error": "Invalid event id"}), 400

    if not events.find_one({"_id": oid}):
        return jsonify({"error": "Event not found"}), 404

    reference_file = request.files.get("reference")
    if not reference_file or not reference_file.filename:
        return jsonify({"error": "Send your reference photo as field 'reference'"}), 400

    tmp_name = f"ref-{uuid.uuid4().hex}.jpg"
    tmp_path = os.path.join(UPLOAD_ROOT, tmp_name)
    reference_file.save(tmp_path)

    try:
        validation_error = image_error(tmp_path)
        if validation_error:
            return jsonify({"error": f"Reference photo rejected: {validation_error}."}), 400
        reference_encodings = face_matching.encode_faces_in_image(tmp_path)
    except Exception as exc:
        app.logger.error("Face scan failed for reference photo: %s", exc)
        return jsonify(
            {"error": "Couldn't read faces from that photo. Try a different image (JPG or PNG)."}
        ), 422
    finally:
        os.remove(tmp_path)

    if not reference_encodings:
        return jsonify({"error": "No face detected in your reference photo. Try a clearer, front-facing photo."}), 400
    if len(reference_encodings) != 1:
        return jsonify({"error": "Reference photo contains multiple faces. Choose a photo showing only yourself."}), 400

    reference_encoding = reference_encodings[0]

    matches = []
    checked = 0
    closest = None  # smallest distance to ANY face, match or not
    for photo_doc in photos.find({"event_id": oid, "has_face": True}):
        checked += 1
        distance = face_matching.best_distance(reference_encoding, photo_doc["encodings"])
        if distance is None:
            continue
        if closest is None or distance < closest:
            closest = distance
        if distance <= face_matching.MATCH_THRESHOLD:
            matches.append(
                {
                    "filename": photo_doc["filename"],
                    "confidence": face_matching.distance_to_confidence(distance),
                    "url": photo_access_url(photo_doc),
                }
            )

    matches.sort(key=lambda m: m["confidence"], reverse=True)
    total_photos = photos.count_documents({"event_id": oid})
    return jsonify(
        {
            "matches": matches,
            "count": len(matches),
            "checked": checked,
            "total_photos": total_photos,
            "closest_confidence": (
                face_matching.distance_to_confidence(closest) if closest is not None else None
            ),
        }
    ), 200


@app.get("/api/photos/<photo_id>/file")
def serve_photo(photo_id):
    try:
        oid = ObjectId(photo_id)
        payload = jwt.decode(request.args.get("token", ""), JWT_SECRET, algorithms=["HS256"])
    except (InvalidId, jwt.InvalidTokenError):
        return jsonify({"error": "Invalid or expired photo link"}), 403
    if payload.get("type") != "photo" or payload.get("photo_id") != photo_id:
        return jsonify({"error": "Invalid photo link"}), 403
    photo = photos.find_one({"_id": oid})
    if not photo:
        return jsonify({"error": "Photo not found"}), 404
    local_dir = os.path.join(UPLOAD_ROOT, str(photo["event_id"]))
    if photo.get("storage_type") == "gcs":
        try:
            response = redirect(cloud_storage.signed_download_url(str(photo["event_id"]), photo["filename"],
                                                                   download=request.args.get("download") == "1"))
            response.headers["Cache-Control"] = "private, no-store"
            return response
        except Exception as exc:
            app.logger.error("Could not sign cloud photo %s: %s", photo_id, exc)
            if not os.path.isfile(os.path.join(local_dir, photo["filename"])):
                return jsonify({"error": "Photo temporarily unavailable"}), 503
    response = send_from_directory(local_dir,
                                   photo["filename"], as_attachment=request.args.get("download") == "1")
    response.headers["Cache-Control"] = "private, no-store"
    return response


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5000)
