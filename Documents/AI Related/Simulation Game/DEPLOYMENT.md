# Deploying to Streamlit Community Cloud

## Quick Deployment Steps

### 1. Push to GitHub

The code is already in your GitHub repository at:
- Owner: sanjayfuloria
- Repo: production
- Branch: community/saas-sanjay-fuloria
- Path: Documents/AI Related/Simulation Game

### 2. Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io/

2. Click "New app"

3. Fill in the details:
   - **Repository**: sanjayfuloria/production
   - **Branch**: community/saas-sanjay-fuloria
   - **Main file path**: `Documents/AI Related/Simulation Game/app/main.py`

4. Click "Advanced settings" and add these secrets:
   ```
   SECRET_KEY = "your-secret-key-here-change-this"
   API_HOST = "http://localhost:8000"
   DATABASE_URL = "sqlite:///./dev.db"
   ```

5. Click "Deploy"

### Important Notes

**This deployment will only work for the Streamlit UI (student/instructor interface).**

The FastAPI backend needs to be deployed separately. Options:

1. **Deploy API to Railway/Render/Fly.io** (Recommended)
   - Deploy the API separately
   - Update `API_HOST` secret to point to your deployed API URL

2. **Use a single deployment platform that supports both**
   - Deploy to a platform like Railway that can run both services
   - Or use Docker Compose on a VPS

### For Full Deployment (UI + API)

Recommended approach:

1. **Deploy API to Render.com** (Free tier available):
   - Create new Web Service
   - Point to your repo
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   
2. **Deploy Streamlit to Streamlit Cloud**:
   - Follow steps above
   - Set `API_HOST` to your Render API URL

### Alternative: Deploy Everything Together

Use Railway.app or Fly.io to deploy both services together with the provided `docker-compose.yml` in the `infra/` folder.

## Files Created for Deployment

- `.gitignore` - Excludes unnecessary files
- `.streamlit/config.toml` - Streamlit configuration
- `packages.txt` - System dependencies
- `requirements.txt` - Python dependencies (already exists)
