# Deploying ClinicalAI on Render

This project is pre-configured for free-tier deployment on [Render](https://render.com) using two decoupled services:
1. **Backend Web Service (`hospital-readmission-api`):** FastAPI + Uvicorn serving live model inference and governance data.
2. **Frontend Static Site (`hospital-readmission-frontend`):** Fast global CDN hosting the React + Vite SPA.

---

## Pre-Deployment Verification

The repository is already optimized for Render's free tier:
- **Lightweight dependencies:** [`requirements-render.txt`](file:///d:/hackfest/requirements-render.txt) excludes unnecessary dev/training packages.
- **Precomputed artifacts:** Model weights (`production_model.joblib`, `preprocessor.joblib`, and `worklist_precomputed.joblib`) are pre-generated and checked into Git, requiring zero offline training during build.
- **Low memory footprint:** Runtime memory is ~220 MB (comfortably below Render's 512 MB free tier ceiling).
- **CORS enabled:** Backend already permits cross-origin requests from any frontend URL.

---

## Method 1: Automatic Blueprint Deployment (Recommended)

Render Blueprints use [`render.yaml`](file:///d:/hackfest/render.yaml) to automatically provision both the Backend and Frontend with a single click.

1. **Push your repository to GitHub:**
   ```bash
   git push origin main
   ```
2. **Log into Render:** Navigate to [dashboard.render.com](https://dashboard.render.com).
3. **Create a Blueprint:**
   - Click **New +** (top right) $\rightarrow$ **Blueprint**.
   - Select and connect your GitHub repository (`hospital_readmission`).
4. **Deploy:**
   - Render will detect [`render.yaml`](file:///d:/hackfest/render.yaml) and list two services:
     - `hospital-readmission-api` (Python Web Service)
     - `hospital-readmission-frontend` (Static Site)
   - Click **Apply**.
5. Render will build and deploy both services automatically.

---

## Method 2: Manual Dashboard Setup (Step-by-Step)

If you prefer to configure the services manually in the Render dashboard:

### Step 1: Deploy the Backend API (Web Service)

1. In the Render Dashboard, click **New +** $\rightarrow$ **Web Service**.
2. Connect your GitHub repository.
3. Configure the service settings:
   - **Name:** `hospital-readmission-api`
   - **Region:** Any (e.g., *Oregon (US West)* or *Frankfurt (EU)*)
   - **Branch:** `main`
   - **Root Directory:** Leave empty (root)
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install -r requirements-render.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type:** `Free`
4. Expand **Advanced**:
   - **Health Check Path:** `/api/health`
   - **Add Environment Variable:**
     - Key: `PYTHON_VERSION`
     - Value: `3.11.11`
5. Click **Create Web Service**.
6. Once deployed, note down your backend URL (e.g., `https://hospital-readmission-api.onrender.com`).

---

### Step 2: Deploy the Frontend (Static Site)

1. In the Render Dashboard, click **New +** $\rightarrow$ **Static Site**.
2. Connect your GitHub repository.
3. Configure the static site settings:
   - **Name:** `hospital-readmission-frontend`
   - **Branch:** `main`
   - **Root Directory:** `frontend`
   - **Build Command:**
     ```bash
     npm install && npm run build
     ```
   - **Publish Directory:** `dist`
4. Expand **Advanced**:
   - **Add Environment Variable:**
     - Key: `VITE_API_BASE_URL`
     - Value: `https://hospital-readmission-api.onrender.com` *(Replace with your Step 1 backend URL)*
   - Under **Redirects/Rewrites**:
     - Click **Add Rule**
     - **Type:** `Rewrite`
     - **Source:** `/*`
     - **Destination:** `/index.html`
5. Click **Create Static Site**.

---

## Verification After Deployment

Once both services show **Live**:

1. **Verify Backend Health:**
   - Open `https://<your-backend-name>.onrender.com/api/health` in your browser.
   - Expected response: `{"status":"ok","service":"clinicalai-api","cohort_size":500,"model":"calibrated ensemble"}`
   - Interactive Swagger API docs are available at `https://<your-backend-name>.onrender.com/docs`.
2. **Verify Frontend UI:**
   - Open `https://<your-frontend-name>.onrender.com`.
   - The status pill in the top navigation should illuminate green as **API Online**.
   - Worklist, Bedside Risk Calculator, and Model Governance & Audits will load live data from your Render backend.

> [!NOTE]
> **Free Tier Cold Starts:** Render free-tier web services spin down after 15 minutes of inactivity. The initial request after spin-down may take ~30–50 seconds to warm up. Static sites on Render are always instantly available on global CDN edges.
