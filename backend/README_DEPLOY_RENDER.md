Deploying the backend to Render

This document explains recommended steps to deploy the FastAPI backend on Render.com with a slim Docker image.

1) Recommended approach
- Use Render's "Web Service" with Docker. Point to the `backend` folder and Dockerfile.
- Do NOT commit `.env` to the repository. Add required environment variables in the Render dashboard (see list below).

2) Build args and heavy ML libs
- The Dockerfile supports a build-arg `INSTALL_ML_LIBS` which is false by default.
- To include heavy packages (torch/transformers/sentence-transformers), set the build command to:

  docker build --build-arg INSTALL_ML_LIBS=true -t myapp-backend .

- Recommended: keep ML libraries out of this service and run them in a separate worker or a managed service with GPU support.

3) Environment variables (example keys required)
- PORT (optional, default 5000)
- POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT
- REDIS_URL_CELERY, REDIS_URL_CHAT
- NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
- PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME
- GEMINI_API_KEYS, COHERE_API_KEY (or set whichever AI provider you use)
- JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRES_MINUTES
- EMAIL_USER, EMAIL_PASS (for email sending)

4) Static checks and size
- `.dockerignore` is configured to exclude `.env`, tests and caches so Render receives a small build context.
- `requirements.txt` excludes heavy ML libs by default to reduce image size and build time.

5) Start command
- The Dockerfile already sets a production Uvicorn command. No need to override.

Troubleshooting
- If build fails on packages like `psycopg2-binary`, ensure `libpq-dev` is present (installed in Dockerfile).
- For slow installs of ML packages, consider using a custom prebuilt image or a separate service.

If you want, I can:
- Add a small GitHub Action to build and push the image to a registry before Render deploy.
- Move ML-heavy code into a separate `worker/` service and add a minimal example.
