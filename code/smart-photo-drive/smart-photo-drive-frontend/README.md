# Smart Photo Drive frontend

React, Vite, React Router, and Tailwind CSS provide the attendee and event-manager interface. Authentication, events, uploads, and photo search all call the Flask API.

## Run locally

Use Node.js 20 or newer. Start the backend first, then run:

```bash
npm ci
npm run dev
```

Open `http://localhost:5173`. The default API is `http://localhost:5000`; set `VITE_API_BASE` if your local backend uses a different address. The backend's `FRONTEND_ORIGIN` must match the frontend origin.

`npm run build` builds the frontend and `npm run lint` checks source code. Manager uploads are sent in groups of three files to keep each request below the backend size limit.
