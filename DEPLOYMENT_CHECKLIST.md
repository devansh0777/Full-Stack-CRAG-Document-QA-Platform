# Deployment Checklist

## 1. Push To GitHub

Run:

```bash
cd /Users/devansh/AI_Customer_Support_Sytem
git init -b main
git add .
git commit -m "Initial CRAG platform"
git remote add origin <your-github-repo-url>
git push -u origin main
```

## 2. Deploy Backend On Render

1. Open Render and create a new Blueprint service from the GitHub repo.
2. Confirm it detects [render.yaml](/Users/devansh/AI_Customer_Support_Sytem/render.yaml).
3. Set `GROQ_API_KEY`.
4. Wait for backend and Postgres to finish provisioning.
5. Copy the backend public URL.

## 3. Deploy Frontend On Streamlit Community Cloud

1. Open Streamlit Community Cloud.
2. Create a new app from the same GitHub repo.
3. Set:
   - Repository: your repo
   - Branch: `main`
   - Main file path: `frontend/app.py`
4. Add app secret:
   - `API_BASE_URL = "https://<your-render-backend-url>"`
5. Deploy and copy the Streamlit app URL.

## 4. Final Wiring

1. In Render, set `ALLOWED_ORIGINS` to the exact Streamlit app URL.
2. Redeploy the backend.
3. Open the Streamlit app and test:
   - signup/login
   - PDF upload
   - subject list question
   - marks question
   - web fallback question

## 5. Required Secrets

- Render backend:
  - `GROQ_API_KEY`
- Streamlit Cloud frontend:
  - `API_BASE_URL`

## 6. Known Production Note

Uploaded PDFs currently live on the backend filesystem. On free/ephemeral hosting this is not durable long term. For production, move uploads to object storage such as S3 or Cloudinary-backed file storage.
