# TalentAI — Frontend

React + TypeScript + Vite + Tailwind frontend for the TalentAI recruitment platform,
built against the FastAPI backend (`/api/v1/...` + public `/apply/{token}`).

## Stack

- **Vite + React 18 + TypeScript**
- **Tailwind CSS** for styling
- **@tanstack/react-query v5** for server state
- **zustand** (persisted) for auth state
- **react-router-dom v6** for routing
- **recharts** for dashboard/report charts
- **react-dropzone** for CV uploads
- **axios** with an interceptor that auto-refreshes the access token on 401

## Getting started

```bash
npm install
cp .env.example .env      # set VITE_API_URL to your backend, e.g. http://localhost:8000
npm run dev
```

The app expects the FastAPI backend running and reachable at `VITE_API_URL`.

## Project structure

```
src/
  api/            # axios client + endpoint wrappers (authApi, jobsApi, candidatesApi, ...)
  components/
    ui/           # shared primitives: Button, Card, Modal, Input, Tabs, ScoreRing, Toast, ...
    layout/       # Sidebar + top bar shell (Layout, PageHeader)
    ProtectedRoute.tsx
  pages/          # one file per route
  store/          # zustand auth store (token + user, persisted to localStorage)
  types/          # shared TS interfaces mirroring the backend schemas
  utils/          # formatting + badge/color helpers
  App.tsx         # route table
  main.tsx        # app entry (QueryClientProvider, BrowserRouter, ToastContainer)
```

## Routes

| Path | Access | Purpose |
|---|---|---|
| `/login`, `/register`, `/forgot-password`, `/reset-password` | public | auth |
| `/apply/:token` | public | candidate application form (no auth) |
| `/dashboard` | authenticated | KPIs, funnel, AI config |
| `/jobs` | authenticated | job CRUD, apply-link/QR, knockout rules |
| `/candidates` | authenticated | filterable candidate list + bulk upload |
| `/candidates/:id` | authenticated | full profile: overview, AI analysis, timeline, AI chat |
| `/reports` | authenticated | time-to-hire, source quality, funnel, audit log (admin) |
| `/settings` | authenticated | team management, webhooks, account |

## Notes

- Recruiter-level data isolation, org scoping, and knockout/decision logic all live in the
  backend — the frontend just reflects `role` (`owner`/`admin`/`recruiter`/`viewer`) to
  show/hide management actions (inviting teammates, managing webhooks, deleting jobs, etc.).
- The access-token refresh flow in `api/client.ts` expects a `refresh_token` in
  `localStorage`; wire that up wherever you persist it after login if you enable the
  `/auth/refresh` flow from `auth_extended.py`.
