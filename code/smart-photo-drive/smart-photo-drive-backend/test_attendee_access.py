"""Request tests for event attendee CSV authorization (no MongoDB server needed)."""

import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bson import ObjectId

os.environ["MONGO_URI"] = "mongodb://test.invalid"
os.environ["JWT_SECRET"] = "attendee-access-test-secret"

with patch("pymongo.MongoClient"):
    import app as backend


class MemoryCollection:
    def __init__(self):
        self.documents = {}

    def insert_one(self, document):
        document = dict(document)
        document.setdefault("_id", ObjectId())
        self.documents[document["_id"]] = document
        return SimpleNamespace(inserted_id=document["_id"])

    def find_one(self, query, _projection=None):
        return next((document for document in self.documents.values()
                     if all(document.get(key) == value for key, value in query.items())), None)

    def update_one(self, query, update):
        document = self.find_one(query)
        if document:
            document.update(update["$set"])


class AttendeeAccessTests(unittest.TestCase):
    def setUp(self):
        backend.events = MemoryCollection()
        backend.users = MemoryCollection()
        backend.managers = MemoryCollection()
        backend.photos = MemoryCollection()
        self.manager_id = backend.managers.insert_one({"email": "manager@example.com"}).inserted_id
        self.other_manager_id = backend.managers.insert_one({"email": "other-manager@example.com"}).inserted_id
        self.attendee_id = backend.users.insert_one({"email": "attendee@example.com"}).inserted_id
        self.other_user_id = backend.users.insert_one({"email": "other@example.com"}).inserted_id
        self.client = backend.app.test_client()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_upload_root = backend.UPLOAD_ROOT
        backend.UPLOAD_ROOT = self.temp_dir.name
        self.addCleanup(setattr, backend, "UPLOAD_ROOT", self.original_upload_root)

    def auth(self, account_id, role):
        return {"Authorization": f"Bearer {backend.make_token(account_id, role)}"}

    def csv(self, content):
        return {"attendees": (io.BytesIO(content), "attendees.csv")}

    def create_event(self, content=b"email_id\nattendee@example.com\n"):
        data = {"name": "Test event", **self.csv(content)}
        return self.client.post("/api/manager/events", data=data,
                                headers=self.auth(self.manager_id, "manager"))

    def test_creation_requires_valid_csv_and_normalizes_emails(self):
        missing = self.client.post("/api/manager/events", data={"name": "Test event"},
                                   headers=self.auth(self.manager_id, "manager"))
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(len(backend.events.documents), 0)
        invalid = self.create_event(b"email_id\nnot-an-email\n")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(len(backend.events.documents), 0)
        created = self.create_event(b"\xef\xbb\xbfemail_ids\n Attendee@Example.com \nattendee@example.com\n")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json["attendeeCount"], 1)
        event = next(iter(backend.events.documents.values()))
        self.assertEqual(event["attendee_emails"], ["attendee@example.com"])

    def test_only_listed_user_can_open_and_search_event(self):
        event_id = self.create_event().json["id"]
        access_url = f"/api/user/events/{event_id}/access"
        search_url = f"/api/user/events/{event_id}/search"
        self.assertEqual(self.client.get(access_url, headers=self.auth(self.attendee_id, "user")).status_code, 200)
        self.assertEqual(self.client.get(access_url, headers=self.auth(self.other_user_id, "user")).status_code, 403)
        with patch.object(backend.face_matching, "FACE_MATCHING_AVAILABLE", True):
            self.assertEqual(self.client.post(search_url, headers=self.auth(self.other_user_id, "user")).status_code, 403)
            self.assertEqual(self.client.post(search_url, headers=self.auth(self.attendee_id, "user")).status_code, 400)

    def test_replacement_revokes_access_and_existing_photo_link(self):
        event_id = self.create_event().json["id"]
        event_oid = ObjectId(event_id)
        photo = {"event_id": event_oid, "filename": "photo.jpg", "storage_type": "local"}
        photo["_id"] = backend.photos.insert_one(photo).inserted_id
        photo_dir = Path(self.temp_dir.name) / event_id
        photo_dir.mkdir()
        (photo_dir / "photo.jpg").write_bytes(b"photo contents")
        link = backend.photo_access_url(photo, "user", self.attendee_id)
        response = self.client.get(link)
        self.assertEqual(response.status_code, 200)
        response.close()

        replace_url = f"/api/manager/events/{event_id}/attendees"
        denied = self.client.put(replace_url, data=self.csv(b"email_id\nother@example.com\n"),
                                 headers=self.auth(self.other_manager_id, "manager"))
        self.assertEqual(denied.status_code, 403)
        invalid = self.client.put(replace_url, data=self.csv(b"email_id\ninvalid\n"),
                                  headers=self.auth(self.manager_id, "manager"))
        self.assertEqual(invalid.status_code, 400)
        response = self.client.get(link)
        self.assertEqual(response.status_code, 200)
        response.close()

        replaced = self.client.put(replace_url, data=self.csv(b"email_id\nother@example.com\n"),
                                   headers=self.auth(self.manager_id, "manager"))
        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(self.client.get(link).status_code, 403)
        access_url = f"/api/user/events/{event_id}/access"
        self.assertEqual(self.client.get(access_url, headers=self.auth(self.attendee_id, "user")).status_code, 403)
        self.assertEqual(self.client.get(access_url, headers=self.auth(self.other_user_id, "user")).status_code, 200)

    def test_cloud_photo_is_checked_before_download(self):
        event_id = self.create_event().json["id"]
        photo = {"event_id": ObjectId(event_id), "filename": "photo.jpg", "storage_type": "gcs"}
        photo["_id"] = backend.photos.insert_one(photo).inserted_id
        allowed_link = backend.photo_access_url(photo, "user", self.attendee_id)
        denied_link = backend.photo_access_url(photo, "user", self.other_user_id)
        with patch.object(backend.cloud_storage, "download_photo", return_value=b"cloud contents") as download:
            self.assertEqual(self.client.get(denied_link).status_code, 403)
            download.assert_not_called()
            response = self.client.get(allowed_link)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b"cloud contents")
            response.close()
            download.assert_called_once_with(event_id, "photo.jpg")


if __name__ == "__main__":
    unittest.main()
