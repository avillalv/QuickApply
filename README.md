# QuickApply

Automated job application tool. Paste a job URL, analyze the match, and let the browser fill and submit the application for you — with optional co-pilot review at each step.

## Requirements

- Python 3.11+
- Node.js 18+
- A [Supabase](https://supabase.com) project (free tier works)
- An [Anthropic](https://console.anthropic.com) API key for AI-powered field mapping

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/avillalv/quickapply.git
cd quickapply
```

**Backend:**
```bash
cd backend
pip install -r ../requirements.txt
playwright install chromium
```

**Frontend:**
```bash
cd frontend
npm install
```

---

### 2. Database (Supabase)

1. Create a new Supabase project at [supabase.com](https://supabase.com).
2. Open the **SQL Editor** and run the contents of `schema.sql` to create all tables.
3. Copy your **Project URL** and **anon public key** from Settings → API.

---

### 3. Environment variables

Create `backend/.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
ANTHROPIC_API_KEY=sk-ant-...
```

---

### 4. Run

**Option A — single command:**
```bash
python run.py
```

**Option B — separate terminals:**

Terminal 1 (backend):
```bash
cd backend
uvicorn main:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Usage

### Analyze a job

1. Paste a job posting URL into the input on the **Command Center** page.
2. Click **Analyze** — QuickApply scrapes the listing, scores your resume match, and detects the ATS platform.
3. Review the match score, required skills, and recommended resume.

### Apply

Click **Co-Pilot** or **Full Auto** on the job card:

| Mode | What it does |
|------|-------------|
| **Co-Pilot** | Opens a browser, fills every field automatically, then pauses for your review before advancing each page. You can edit any value before proceeding. |
| **Full Auto** | Fills and advances every page without stopping, then submits. Use when you've already reviewed the job. |

The automation overlay slides in on the right side. It shows:
- Fields auto-filled (green)
- Fields needing review (yellow) — click any to edit
- A live activity log
- Elapsed time

After submission, the application is automatically saved to the **Tracker** with its match score and the values that were filled. Click **View in Tracker** to jump there directly.

### Edge cases handled

- **CAPTCHA** — automation pauses and shows a prompt; solve it in the browser window then click Continue.
- **Login wall** — automation pauses and asks you to sign in, then resumes.
- **Already applied** — detected and flagged without re-submitting.
- **Validation errors** — errors from the form surface in the overlay so you can fix and resubmit.

---

## Profile

Fill in your details at **Profile** → personal info, work experience, education, skills, and links. The more complete your profile, the fewer fields you'll need to review manually.

Upload one or more resumes under **Profile → Resumes**. Label each one (e.g. `Data Engineer`, `Backend`) and QuickApply will pick the best match automatically.

---

## Settings

| Setting | Default | Notes |
|---------|---------|-------|
| Default mode | Co-Pilot | Can be switched to Full Auto |
| Browser visible | On | Turn off for headless (faster, no window) |
| Auto-submit | Off | Full Auto only; submits without confirmation |
| Typing speed | 35 ms/char | Lower = faster; raise if sites reject fast input |
| Page load timeout | 30 s | Increase for slow corporate ATS sites |
| AI model | claude-sonnet-4-6 | Used for field mapping and cover letter generation |

---

## Supported ATS Platforms

Greenhouse · Lever · Workday · iCIMS · SmartRecruiters · Ashby · BambooHR · Generic HTML forms

---

## Tracker

All submitted applications appear on the **Tracker** page with status, match score, company, and the values that were filled. Update status manually (Applied → Interviewing → Offer → Rejected) as you hear back.

---

## Troubleshooting

**Backend won't start** — check that `.env` is present and `SUPABASE_URL` / `SUPABASE_ANON_KEY` are correct.

**"Failed to analyze"** — make sure the backend is running on port 8000 and the job URL is publicly accessible (no login required to view the listing).

**Automation hangs on page load** — increase Page Load Timeout in Settings, or switch to Co-Pilot mode so you can intervene manually.

**Fields not filling** — the site may use a non-standard form library. Use Co-Pilot mode to fill those fields manually; the rest will still be auto-filled.
