# Deploying RoadSense

The backend goes to **Hugging Face Spaces** (free, 16 GB RAM, enough for PyTorch) and the frontend goes to **Vercel**.
Render's free tier only has 512 MB of RAM, which isn't enough to load PyTorch and YOLO.

## 0. Prerequisites

- `backend/weights/best.pt` and `backend/weights/metrics.json` exist (from training)
- Code is pushed to GitHub

## 1. Push to GitHub

```bash
cd ~/roadsense
git init
git add .
git commit -m "RoadSense: road damage detection with YOLO, FastAPI and React"
git branch -M main
```

Create an **empty** repo named `roadsense` at https://github.com/new (no README, no .gitignore), then:

```bash
git remote add origin https://github.com/tejasavbishnoi/roadsense.git
git push -u origin main
```

GitHub Actions runs the tests, the frontend build and the Docker build automatically. Check the **Actions** tab.

## 2. Backend on Hugging Face Spaces

1. Make an account at https://huggingface.co/join.
2. Create a Space at https://huggingface.co/new-space:
   - Name: `roadsense-api`
   - SDK: **Docker** (Blank template)
   - Hardware: **CPU basic (free)**
3. Create an access token with **write** permission at https://huggingface.co/settings/tokens.
4. Upload the backend folder:

```bash
pip install -U huggingface_hub
hf auth login                       # paste the token
cd ~/roadsense/backend
hf upload tejasavbishnoi/roadsense-api . . --repo-type=space \
  --exclude ".venv/*" "__pycache__/*" ".pytest_cache/*"
```

(If your Hugging Face username is different, use it in place of `tejasavbishnoi`.)

5. The Space builds the Docker image (about 5–8 minutes). When it shows **Running**, open
   `https://tejasavbishnoi-roadsense-api.hf.space/health`. It should say `"model_loaded": true`.
6. In the Space's **Settings → Variables**, add `ALLOWED_ORIGINS` = your Vercel URL (after step 3), for example
   `https://roadsense.vercel.app`. Leaving it as `*` also works.

Free Spaces sleep after 48 hours without visits. The first request after that takes about a minute; the website shows "API waking up" while it does.

To update the model later, run the same `hf upload` command again.

## 3. Frontend on Vercel

1. Go to https://vercel.com/new and import the `roadsense` GitHub repo.
2. **Root Directory**: `frontend`. Framework preset: **Vite** (detected automatically).
3. Add the environment variable `VITE_API_URL` = `https://tejasavbishnoi-roadsense-api.hf.space`
4. Click **Deploy**.

Every `git push` to `main` redeploys the frontend automatically.

## 4. Finish the README

- Put the Vercel and Space links at the top of `README.md`
- Copy the tables from `training/results/test/report.md` into **Results**
- Add a screenshot or GIF to `docs/` and link it
- Push again
