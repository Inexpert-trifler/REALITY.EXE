# REALITY.EXE Deployment Guide

This guide provides step-by-step instructions for deploying the REALITY.EXE application, comprising a Vercel-hosted React frontend and a Render-hosted FastAPI backend.

## 1. Backend Deployment (Render)

The backend is built with FastAPI and runs on Docker. Render is ideal for hosting this service.

### 1.1 Prerequisites
- A Render account (https://render.com)
- Optional: Your existing PostgreSQL database credentials (if running with persistence)

### 1.2 Create the Web Service
1. In the Render Dashboard, click **New +** and select **Web Service**.
2. Connect the repository containing the backend code.
3. Configure the service:
   - **Name**: `reality-exe-backend` (or your preferred name)
   - **Environment**: `Docker`
   - **Region**: Choose the region closest to your database
   - **Instance Type**: Starter or Standard (do not use Free if you need constant uptime)
   - **Docker Command**: Leave blank (Render uses the `Dockerfile`)

### 1.3 Environment Variables
Under **Environment Variables**, add the following (do NOT commit these values to version control):

| Key | Value | Description |
|---|---|---|
| `ENVIRONMENT` | `production` | **Required.** Must be `production`. |
| `DEBUG` | `False` | **Required.** Must be `False`. |
| `AUTH_SECRET` | `[YOUR_SECURE_SECRET]` | **Required.** A cryptographically secure random string (min 32 chars). |
| `DATABASE_MODE` | `disabled` | **Optional.** Set to `disabled` to run the application without any database. |
| `DATABASE_URL` | `[YOUR_DB_URL]` | Required if `DATABASE_MODE` is enabled. The `postgresql+asyncpg://...` URL for your database. |
| `SYNC_DATABASE_URL` | `[YOUR_SYNC_DB_URL]`| Required if `DATABASE_MODE` is enabled. The `postgresql://...` URL (for migrations). |
| `ALLOWED_ORIGINS` | `["https://your-vercel-app.vercel.app"]` | **Required.** Update this with your actual Vercel frontend URL once deployed. |
| `STORAGE_BACKEND` | `local` | **Warning: Render uses an ephemeral filesystem by default.** Evidence uploads saved to `local` will be permanently lost when the instance restarts or redeploys unless you attach a persistent disk (Render "Disk") to `/tmp/reality_exe_evidence`. For durable storage without a disk, you must configure S3 via `STORAGE_ENDPOINT` et al. |

*Note on AI Features:* If you do not configure `OLLAMA_BASE_URL`, the backend gracefully degrades:
- Quest Generation will serve deterministic, curated fallback quests.
- Evidence Verification will return `UNCERTAIN` (requiring manual review) and gracefully prompt the user without awarding verified status or XP.

*Note on Database-Disabled Mode (`DATABASE_MODE=disabled`):*
- Health check endpoints (`/health`, `/api/v1/health`) will work and report the API is running with `database="disabled"`.
- Features requiring persistence (quests state, XP, achievements) will gracefully return HTTP 503 errors and will not be silently mocked.
- Do not attempt to use persistent endpoints without a database.

### 1.4 Deploy
Click **Create Web Service**. Once deployed, Render will provide a URL (e.g., `https://reality-exe-backend.onrender.com`). Note this URL for the frontend configuration.

---

## 2. Frontend Deployment (Vercel)

The frontend is a Vite + React application.

### 2.1 Prerequisites
- A Vercel account (https://vercel.com)
- The backend API URL from the previous step

### 2.2 Create the Project
1. In the Vercel Dashboard, click **Add New...** -> **Project**.
2. Import the frontend repository.
3. Configure the project:
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### 2.3 Environment Variables
Under **Environment Variables**, add:

| Key | Value | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `https://reality-exe-backend.onrender.com` | The URL of your deployed Render backend (no trailing slash). |

*(Do not include `/api/v1` in the URL; the API client appends it automatically.)*

### 2.4 Deploy
Click **Deploy**. Vercel will build and deploy the SPA.
A `vercel.json` file is already included in the repository to ensure React Router handles SPA routing correctly via rewrites.

### 2.5 Final Step: Update Backend CORS
After the frontend deploys successfully, copy its URL (e.g., `https://reality-exe.vercel.app`).
Go back to your Render backend configuration and update the `ALLOWED_ORIGINS` environment variable to include this URL, then trigger a manual redeploy of the backend.

---

## 3. Production Readiness Checklist
- [ ] `ENVIRONMENT=production` and `DEBUG=False` on the backend.
- [ ] `AUTH_SECRET` changed from default to a secure >32 character string.
- [ ] `ALLOWED_ORIGINS` strict on backend (pointing only to the Vercel app).
- [ ] No database credentials or secrets exposed in frontend environment variables.
- [ ] `VITE_API_BASE_URL` accurately pointing to the deployed backend.
