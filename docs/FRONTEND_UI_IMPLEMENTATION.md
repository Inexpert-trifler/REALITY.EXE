# REALITY.EXE — Master Frontend UI Implementation & Integration

This document describes the unified frontend architecture, design system, component hierarchy, user flow routing, API client integration, and build/execution guide for **REALITY.EXE**.

---

## 1. Architecture Overview

- **Framework**: React 18 + Vite 5 + TypeScript 5
- **Styling**: Tailwind CSS + Custom Tactile Neo-Brutalist CSS Tokens
- **Routing**: React Router DOM (`BrowserRouter`)
- **State Management**: React Context (`GameContext`) with centralized API integration
- **Design Language**: Cozy Pixel-Craft Neo-Brutalism (Earthy Biome Palette, Hard Extruded Pixel Shadows, Chunky Borders, Dual Typography)

---

## 2. Route Map & User Flow

| Route | Page Component | Stitch Reference Screen | Description |
|---|---|---|---|
| `/` | `HomePage` | `01_reality.exe_home_base` | Main overworld base, status card, overworld SVG landscape, Enter Reality CTA. |
| `/quest/setup` | `QuestSetupPage` | `02_reality.exe_quest_setup` | Quest parameters: Time (10/20/45/60m), Environment, Play Style selection. |
| `/quest/ready` | `QuestReadyPage` | `03_reality.exe_quest_ready` | Generated quest briefing, objectives list, rewards, Start Quest CTA. |
| `/quest/pocket` | `PocketModePage` | `04_reality.exe_pocket_mode` | Minimal distraction-free mode, audio guide indicator, countdown timer, I'm Back CTA. |
| `/quest/welcome` or `/quest/return` | `WelcomeBackPage` | `05_reality.exe_welcome_back` | Return summary, optional photo evidence upload, Submit Quest CTA. |
| `/quest/verify` | `VerificationPage` | `06_reality.exe_game_master_verification` | AI Game Master verification loading animation & status messages. |
| `/quest/complete` | `QuestCompletePage` | `07_reality.exe_quest_complete` | Victory banner, +XP reward animation, achievement reveal, Next Quest / Profile CTAs. |
| `/profile` | `ProfilePage` | `08_reality.exe_player_profile` | **Primary Visual Benchmark**: Scout Dossier, RPG Character Card, XP Gauge, 3 Stat Cards, Achievement Grid + Badge Inspector, Adventure Log + Empty Toggle. |

---

## 3. Centralized Design System

Located in:
- `src/styles/design-tokens.css`
- `tailwind.config.cjs`
- `DESIGN.md`

### Design Tokens Summary

- **Palette**:
  - `Canvas / Surface`: `#F7F3E8`
  - `Elevated Surface`: `#FFFDF5`
  - `Track Well`: `#EFE8D3`
  - `Primary (Meadow Grass)`: `#6FAF5F`
  - `Primary Dark (Deep Canopy)`: `#3F7042`
  - `Secondary (Loam Dirt)`: `#A9784F` / `#80552F`
  - `Sandstone`: `#D8B892`
  - `XP Gold`: `#E5B84B` / `#C49A2F`
  - `Sky Accent`: `#8FC8D8`
  - `Ink / Dark Border`: `#2B2118` / `#231A11`
  - `Muted Bark`: `#6B5C4D`
- **Typography**:
  - `Display / Headlines / HUD`: `Space Grotesk`
  - `Body / Story Prompts`: `Plus Jakarta Sans`
- **Extruded Shadows & Borders**:
  - `Primary Border`: `2px solid #2B2118`
  - `Card Hard Shadow`: `box-shadow: 0 4px 0 0 #2B2118`
  - `Quest Card Shadow`: `box-shadow: 0 6px 0 0 #2B2118`
  - `Modal Shadow`: `box-shadow: 0 8px 0 0 #2B2118`
  - `Tactile Press`: `:active { transform: translateY(4px); box-shadow: none; }`

---

## 4. Reusable Components

```
src/
├── components/
│   ├── layout/
│   │   ├── AppHeader.tsx       # Standard top header (REALITY.EXE, WORLD: ONLINE badge, settings, profile avatar)
│   │   ├── BottomNavigation.tsx # Shared bottom bar (HOME, QUEST, PROFILE)
│   │   └── AppShell.tsx         # Centered handheld adventure console shell for desktop & mobile
│   ├── pixel/
│   │   ├── PixelCard.tsx       # Base tactile card container with bevel highlights
│   │   ├── PixelButton.tsx     # Primary, Secondary, XP, Ghost & Danger tactile buttons
│   │   ├── PixelBadge.tsx      # Status, XP, play style & difficulty chips
│   │   ├── PixelLoader.tsx     # Animated pixel block loader
│   │   └── PixelSettingsModal.tsx # System settings drawer modal (chimes, emitters, proximity)
│   ├── gamemaster/
│   │   ├── GameMasterMessage.tsx # AI Game Master speech bubble container
│   │   └── VerificationState.tsx # Verification progress renderer
│   ├── player/
│   │   └── XPBar.tsx           # 10-block segmented pixel XP progress meter
│   └── evidence/
│       └── EvidenceUploader.tsx # File upload, preview, and remove handler
```

---

## 5. API Integration & Offline Resiliency

The API client (`src/services/api/client.ts`) connects to `/api/v1` on the FastAPI backend:
- `POST /api/v1/quests/generate`
- `POST /api/v1/quests/{id}/start`
- `POST /api/v1/quests/{id}/pocket`
- `POST /api/v1/quests/{id}/return`
- `POST /api/v1/quests/{id}/complete`
- `POST /api/v1/evidence/upload`
- `GET /api/v1/player/profile`
- `GET /api/v1/player/stats`

**Offline Mode**: If the local FastAPI server is offline, `GameContext` gracefully provides local state transitions and deterministic quest fallbacks so the user experience is never broken.

---

## 6. How to Run & Build

### Development Server
```bash
npm run dev
```
Runs Vite dev server on `http://localhost:3000`.

### Type Checking & Production Build
```bash
npm run build
```
Generates production assets in `dist/`.

---

## 7. Verification & Tests

- TypeScript type check (`tsc`): **0 errors**
- Vite build (`vite build`): **Succeeded cleanly**
- All 8 Stitch screens fully mapped and styled according to the Player Profile benchmark.
