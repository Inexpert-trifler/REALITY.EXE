# REALITY.EXE — Master Design Tokens & System Reference

## Brand & Visual Philosophy

- **Name**: REALITY.EXE
- **Tagline**: AI creates the game. Reality is the playground.
- **Visual Aesthetic**: Tactile Neo-Brutalist Pixel-Craft.
- **Core Philosophy**: Handheld expedition compendium blending warm Sandbox survival aesthetics with crisp modern mobile UX.

---

## 1. Color System (Biome Derived)

| Token Name | Hex Code | Semantic Purpose |
|---|---|---|
| `--color-background` | `#F7F3E8` | Base parchment canvas |
| `--color-surface-card` | `#FFFDF5` | Warm white elevated slates and cards |
| `--color-surface-low` | `#FFF1E8` | Inset card highlights and item wells |
| `--color-surface-container` | `#FEEADC` | Container fills |
| `--color-surface-high` | `#F8E5D6` | Highlight containers and headers |
| `--color-surface-dim` | `#E9D7C8` | Structural dimmed surfaces |
| `--color-primary` | `#6FAF5F` | Meadow Grass — Primary actions, active quest triggers |
| `--color-primary-dark` | `#3F7042` | Deep Canopy — Primary borders, active status framing |
| `--color-secondary` | `#A9784F` | Loam Dirt — Secondary utilities, inventory panels |
| `--color-secondary-light` | `#D8B892` | Sandstone — Secondary button fill |
| `--color-tertiary` | `#E5B84B` | XP Gold — Level-up notifications, rewards |
| `--color-tertiary-dark` | `#C49A2F` | XP Gold container fill |
| `--color-sky` | `#8FC8D8` | Clear Atmosphere — AI Game Master bubbles |
| `--color-ink` | `#2B2118` | Dark Peat Charcoal — Typography, hard borders |
| `--color-muted` | `#6B5C4D` | Weathered Bark — Supporting metadata |
| `--color-track` | `#EFE8D3` | Progress bar wells and troughs |

---

## 2. Typography System

- **Display & Headlines**: `Space Grotesk`, sans-serif (Bold / All Caps)
- **Body & Narrative**: `Plus Jakarta Sans`, sans-serif (500 / 700 / 800)

| Token | Font Family | Size / Line-Height | Tracking | Weight |
|---|---|---|---|---|
| `display-xl` | Space Grotesk | 32px / 40px | -0.02em | 700 |
| `headline-lg` | Space Grotesk | 26px / 34px | -0.01em | 700 |
| `headline-md` | Space Grotesk | 20px / 28px | -0.01em | 700 |
| `headline-sm` | Space Grotesk | 16px / 24px | 0em | 700 |
| `body-lg` | Plus Jakarta Sans | 16px / 24px | 0em | 500 |
| `body-md` | Plus Jakarta Sans | 14px / 22px | 0em | 500 |
| `body-sm` | Plus Jakarta Sans | 12px / 18px | 0em | 500 |
| `label-lg` | Space Grotesk | 14px / 18px | 0.04em | 700 |
| `label-md` | Plus Jakarta Sans | 12px / 16px | 0.02em | 700 |
| `label-sm` | Plus Jakarta Sans | 10px / 14px | 0.06em | 800 |

---

## 3. Geometry & Extrusions

- **Border Weight**: `2px solid #2B2118`
- **Corner Radius**:
  - `xs / sm`: `2px`
  - `DEFAULT`: `4px`
  - `md`: `6px`
  - `lg`: `8px`
  - `xl`: `12px`
- **Extruded Shadows**:
  - `card-sm`: `0 2px 0 0 #2B2118`
  - `card-md`: `0 4px 0 0 #2B2118`
  - `card-lg`: `0 6px 0 0 #2B2118`
  - `modal-xl`: `0 8px 0 0 #2B2118`
  - `btn-primary`: `0 4px 0 0 #3F7042`
  - `btn-secondary`: `0 4px 0 0 #A9784F`
  - `btn-xp`: `0 4px 0 0 #B88526`
- **Active Press State**:
  - `transform: translateY(4px)`
  - `box-shadow: 0 0 0 0 transparent`

---

## 4. Header & Navigation Standard

- **Header**: Fixed top `h-16`, REALITY.EXE logo, `WORLD: ONLINE` status dot, Settings icon, Profile avatar.
- **Bottom Navigation**: Fixed bottom `h-16`, 3 destinations: `HOME`, `QUEST`, `PROFILE`.
- **Desktop Shell**: Max-width `440px`, centered with rounded corners, simulating a handheld expedition console.
