# Chatbot Plugin Installation and Setup

## Overview

The Resources AI Chatbot frontend is bundled inside the Jenkins plugin. After
installing the plugin, Jenkins serves the chatbot UI without a separate
frontend server.

The chatbot backend runs as a separate FastAPI service. The plugin connects to
it using the backend URL configured in Jenkins.

```text
Jenkins plugin (bundled frontend) ──> FastAPI backend
```

## Install the Released Plugin

1. Open **Manage Jenkins > Plugins**.
2. Search for **Resources AI Chatbot** in the available plugins.
3. Install the plugin and restart Jenkins if requested.
4. Open the chatbot from the button in the bottom-right corner.

The released plugin already contains the chatbot frontend. Users do not need
to build or start a separate frontend application.

## Prepare RAG Data

Before using documentation-based answers for the first time, generate the
retrieval data and vector indexes from the repository root:

```bash
make run-data-pipeline
```

This collects, processes, chunks, embeds, and stores the configured data
sources. The backend can start without this step, but RAG-based answers will
not work until the required indexes have been created.

## Start the Backend

From the repository root, run:

```bash
make api
```

The default backend URL is:

```text
http://localhost:8000
```

## Configure the Backend URL

To connect the plugin to a different backend:

1. Go to **Manage Jenkins > System**.
2. Find **Resources AI Chatbot Plugin**.
3. Enter the FastAPI backend URL.
4. Save the configuration.

The URL must use `http://` or `https://`. For example:

```text
http://localhost:8000
https://chatbot.example.com
```

The plugin stores only this URL. API keys are not entered or returned through
this Jenkins configuration.

## Local Plugin Development

Run the backend and Jenkins in separate terminals.

**Terminal 1 — FastAPI backend**

```bash
make api
```

**Terminal 2 — Jenkins plugin**

```bash
mvn hpi:run
```

The Maven build compiles the frontend and packages it into the plugin before
Jenkins starts. A separate frontend server is not required for this flow.

If frontend assets need to be built independently, run this from the
repository root before starting Jenkins:

```bash
make build-frontend
```

This is normally unnecessary because `mvn hpi:run` builds the frontend as part
of the plugin lifecycle.

For frontend-only development, the frontend can also be started separately:

```bash
cd frontend
npm run dev
```

## Backend Status

The chatbot header shows whether the configured backend is reachable:

- Green indicator: the backend is available.
- Red indicator: the backend is unavailable.

When the backend is unavailable, the chatbot shows the `make api` command and
a link to the repository setup guide. The status indicator tooltip shows the
latest health-check result and check time.

## Troubleshooting

If the chatbot cannot connect:

1. Confirm that the FastAPI service is running.
2. Check the URL under **Manage Jenkins > System > Resources AI Chatbot Plugin**.
3. Confirm that the configured port is reachable from Jenkins.
4. Refresh the Jenkins page after changing the configuration.

If RAG answers are unavailable, confirm that `make run-data-pipeline` finished successfully and check `logs/data-pipeline.log` for errors.

If the frontend appears stale during local development, run `make build-frontend` and restart Jenkins.
