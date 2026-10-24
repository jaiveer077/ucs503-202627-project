# Smart Photo Drive

Smart Photo Drive lets an event manager upload event photographs. An attendee uploads a single-face reference photo, and the app returns event photos containing a matching face. The backend detects faces when event photos are uploaded and stores face encodings in MongoDB, so searches compare against saved encodings rather than scanning every original again.

## Run locally

1. Follow [backend setup](smart-photo-drive-backend/README.md). Start Flask on `http://localhost:5000`.
2. Follow [frontend setup](smart-photo-drive-frontend/README.md). Start Vite on `http://localhost:5173`.
3. Register as an event manager, create an event, and upload photos.
4. Register as an attendee, select that event, and upload a clear photo showing only your face.

The manager dashboard shows upload and scan counts. Search results provide one-hour photo links. The displayed match score is a visual ranking derived from face distance; it is not a calibrated probability that a match is correct.

The agreed project scope excludes automated unit, integration, and performance tests; Docker and GitHub Actions CI; and separate frontend/backend deployment.
