# Deploying RoadSense

The backend goes to **Render** (free web service) and the frontend goes to **Vercel**.

Render's free instance has 512 MB of RAM, which isn't enough for PyTorch. So the model is
**exported to ONNX** and served with ONNX Runtime, which needs about 150 MB.

## 0. Prerequisites

- `backend/weights/best.onnx` and `backend/weights/metrics.json` exist (see step 2a)
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

## 2. Backend on Render

### 2a. Export the model to ONNX (once per trained model)

```bash
cd ~/roadsense/backend
source .venv/bin/activate
pip install onnxruntime
yolo export model=weights/best.pt format=onnx imgsz=640 opset=20   # opset 20: fully supported by ONNX Runtime
python scripts/check_onnx.py path/to/any_road_photo.jpg   # should print MATCH
```

Commit and push `weights/best.onnx`.

### 2b. Create the service

1. Go to https://dashboard.render.com and choose **New → Blueprint**.
2. Connect the `roadsense` GitHub repo. Render reads `render.yaml` and creates **roadsense-api** (free plan).
3. Click **Apply**. The first build takes about 3–5 minutes.
4. Open `https://roadsense-api-us6q.onrender.com/health (your URL is shown on the service page)` (your URL is shown on the service page).
   It should say `"model_loaded": true` and `"runtime": "onnx"`.

The free instance sleeps after 15 minutes without traffic. The first request after that takes
about a minute; the website shows "API waking up" while it does.

## 3. Frontend on Vercel

1. Go to https://vercel.com/new and import the `roadsense` GitHub repo.
2. **Root Directory**: `frontend`. Framework preset: **Vite** (detected automatically).
3. Add the environment variable `VITE_API_URL` = your Render URL, for example `https://roadsense-api.onrender.com`
4. Click **Deploy**.

Every `git push` to `main` redeploys the frontend automatically.

## 4. Finish the README

- Put the Vercel and Render links at the top of `README.md`
- Copy the tables from `training/results/test/report.md` into **Results**

- Push again
