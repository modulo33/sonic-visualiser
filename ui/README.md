# React UI for Sonic Visualiser

This folder contains a small Vite + React front-end that can be wired to the Python bindings or any
HTTP bridge that exposes Sonic Visualiser functionality.

## Getting started

```bash
cd ui
npm install
npm run dev
```

The UI expects two endpoints when you are ready to connect it to a backend:

- `GET /api/plugins` – returns an array of plugin objects. If the request fails, the UI falls back to
  bundled mock plugins so you can still iterate on the design.
- `POST /api/analyse` – accepts `{ plugin, parameters, source }` and returns `{ id, status }`. When the
  request fails, the UI simulates a job so that the task queue remains interactive.

## Layout

- **Input panel**: choose local audio files or reference remote/live sources.
- **Plugin selector**: lists available Vamp/custom plugins with tags and default parameters.
- **Parameter controls**: tweak sensitivity, hop size, and add notes for the Python bridge.
- **Task queue**: mirrors submitted analysis jobs; statuses are simulated unless your backend responds.
- **Preview**: shows the payload that would be delivered to the backend.

You can customise styling by editing `src/App.css`.
