# CRAG Document QA Platform

Full-stack Python system with:
- `FastAPI` backend
- `Streamlit` frontend
- `LangChain` and `LangGraph` for CRAG orchestration
- `Postgres + pgvector` for persistence and vector search
- `Groq` for grading, rewriting, and answer generation

## Repository Layout

- `backend/`: API, ingestion, retrieval, CRAG graph, persistence
- `frontend/`: Streamlit UI
- `docker-compose.yml`: local stack

## Local Development

1. Copy env files:
   - `cp backend/.env.example backend/.env`
   - `cp frontend/.env.example frontend/.env`
2. Add your `GROQ_API_KEY` to `backend/.env`
3. Start the stack:

```bash
docker compose up --build
```

Frontend:
- [http://localhost:8501](http://localhost:8501)

Backend:
- [http://localhost:8000/docs](http://localhost:8000/docs)

## Separate Deployment

Deploy the frontend and backend independently:
- Backend: build from `backend/Dockerfile`
- Frontend: build from `frontend/Dockerfile`

Configure the frontend with the public backend URL via `API_BASE_URL`.

## Recommended Hosted Deployment

### Backend on Render

This repo includes [render.yaml](/Users/devansh/AI_Customer_Support_Sytem/render.yaml) for the backend and Postgres.

Render setup:
1. Push this repo to GitHub.
2. Create a new Render Blueprint from the repo.
3. Set `GROQ_API_KEY` in Render.
4. The backend now normalizes Render Postgres URLs automatically, so `postgres://...` and `postgresql://...` both work.
5. After Streamlit Cloud gives you the frontend URL, update `ALLOWED_ORIGINS` in Render to that exact app URL.

Backend result:
- FastAPI API on Render
- managed Postgres database on Render

### Frontend on Streamlit Community Cloud

Use the `frontend/` app as the Streamlit entrypoint.

Streamlit Cloud setup:
1. Push this repo to GitHub.
2. In Streamlit Community Cloud, create a new app from the repo.
3. Set:
   - Main file path: `frontend/app.py`
   - Python version: `3.11`
4. Add app secrets/environment:
   - `API_BASE_URL=https://<your-render-backend>.onrender.com`

After Streamlit is live:
1. Copy the Streamlit app URL.
2. Put that URL into Render `ALLOWED_ORIGINS`.
3. Redeploy backend once.

## Notes

- Uploaded files are stored on the backend filesystem under `backend/uploads/`
- v1 stores feedback for later analysis; it does not auto-tune models
- Embeddings use a free local Hugging Face sentence-transformer model by default
