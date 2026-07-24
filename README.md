# PDF Manager

A full-stack app: **React** frontend · **FastAPI** backend · **SQLite** database.

## Features
- Log in by name, or create a new account
- Create projects and invite other users
- Upload PDFs per project (stored as binary blobs in SQLite)
- Download any uploaded PDF

---

## Quick Start

### Pre-requisites

- You will need to have python 3.10 or higher installed
- Node.js is also required

### 1 — Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Note: run via python -m uvicorn (OneDrive blocks .exe execution directly)
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

The API runs at **http://localhost:8000**  
Interactive docs: http://localhost:8000/docs

### 2 — Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The app opens at **http://localhost:5173**

---

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI routes
│   ├── database.py      # SQLite init & connection
│   ├── requirements.txt
│   └── app.db           # created on first run
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api.js        # all fetch calls
    │   ├── index.css
    │   ├── main.jsx
    │   └── pages/
    │       ├── Login.jsx
    │       ├── Projects.jsx
    │       └── ProjectDetail.jsx
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## Database Schema

| Table | Key columns |
|---|---|
| `users` | id, name (unique) |
| `projects` | id, name, owner_id |
| `project_members` | project_id, user_id |
| `documents` | id, project_id, filename, content (BLOB), uploaded_by |
