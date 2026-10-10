---
name: Overworld Tactile Pixel
colors:
  surface: '#fff8f5'
  surface-dim: '#e9d7c8'
  surface-bright: '#fff8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fff1e8'
  surface-container: '#feeadc'
  surface-container-high: '#f8e5d6'
  surface-container-highest: '#f2dfd1'
  on-surface: '#231a11'
  on-surface-variant: '#41493d'
  inverse-surface: '#392e25'
  inverse-on-surface: '#ffeee1'
  outline: '#717a6c'
  outline-variant: '#c1c9b9'
  surface-tint: '#2e6b24'
  primary: '#2e6b24'
  on-primary: '#ffffff'
  primary-container: '#6faf5f'
  on-primary-container: '#014100'
  inverse-primary: '#95d782'
  secondary: '#80552f'
  on-secondary: '#ffffff'
  secondary-container: '#fdc394'
  on-secondary-container: '#794e29'
  tertiary: '#785a00'
  on-tertiary: '#ffffff'
  tertiary-container: '#c49a2f'
  on-tertiary-container: '#473400'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#b0f49c'
  primary-fixed-dim: '#95d782'
  on-primary-fixed: '#002200'
  on-primary-fixed-variant: '#14520d'
  secondary-fixed: '#ffdcc2'
  secondary-fixed-dim: '#f4bb8d'
  on-secondary-fixed: '#2e1500'
  on-secondary-fixed-variant: '#653e1a'
  tertiary-fixed: '#ffdf9b'
  tertiary-fixed-dim: '#eec052'
  on-tertiary-fixed: '#251a00'
  on-tertiary-fixed-variant: '#5b4300'
  background: '#fff8f5'
  on-background: '#231a11'
  surface-variant: '#f2dfd1'
typography:
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '700'
    lineHeight: 24px
    letterSpacing: 0em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 22px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 18px
  label-lg:
    fontFamily: Space Grotesk
    fontSize: 14px
    fontWeight: '700'
    lineHeight: 18px
    letterSpacing: 0.04em
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 10px
    fontWeight: '800'
    lineHeight: 14px
    letterSpacing: 0.06em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system establishes an earthy, nostalgic, and intrinsically physical digital realm. It blends the warmth of childhood sandbox survival worlds with high-fidelity, contemporary mobile usability. The design language transforms routine physical environments into an unfolding sandbox adventure.

- **Emotional Tone:** Cozy, exploratory, tactile, rewarding, and grounded. The interface feels like an organic field journal running inside a playful handheld console.
- **Aesthetic Movement:** Tactile Neo-Brutalist Pixel-Craft. It deliberately rejects sterile tech glass and ungrounded modern minimalism in favor of structured pixel stepped contours, extruded hard bevels, and warm natural textures.
- **Target Audience:** Real-world adventurers, urban explorers, geocachers, tabletop RPG enthusiasts, and creative builders seeking to gamify everyday walks and expeditions through an open-source AI companion.

## Colors

The palette is derived strictly from natural biomes: verdant meadows, rich loamy soil, baked sandstone, sunlit skies, and golden rewards. It delivers a sun-drenched, welcoming environment without cold chromatic gray values.

- **Canvas & Surfaces:**
  - Base Background: `#F7F3E8` (Looming parchment / warm cream canvas).
  - Elevated Cards / Containers: `#FFFDF5` (Warm white, bone-tinted inventory slots and message slates).
  - Sunken / Inset Track Wells: `#EFE8D3` (Recessed progress troughs, health bars, inventory wells).
- **Core Role Tokens:**
  - `primary` (`#6FAF5F` — Meadow Grass): Primary actions, success nodes, stamina meters, active quest triggers.
  - `primary-container` / `primary-dark` (`#3F7042` — Deep Canopy): Structural border extrusions for primary surfaces, strong emphasis headlines, active status framing.
  - `secondary` (`#A9784F` — Loam Dirt): Secondary utilities, inventory panels, structural physical pillars.
  - `secondary-light` (`#D8B892` — Sandstone): Inactive badges, neutral tooltips, wood-grain tags.
  - `tertiary` (`#E5B84B` — Quest XP Gold): Level-up notifications, rare encounters, reward chests, gold metrics.
  - `sky-accent` (`#8FC8D8` — Clear Atmosphere): AI Master prompt bubbles, weather cues, real-world teleport/map pins.
- **Ink & Neutral Tokens:**
  - `neutral` (`#2B2118` — Peat Charcoal): Deep earthy carbon for all high-contrast typography, hard border outlines, and rigid pixel dropshadows.
  - `neutral-variant` (`#6B5C4D` — Weathered Bark): Supporting metadata, subheadings, and passive coordinate values.

## Typography

Typography strikes a deliberate balance: structural, punchy, geometric retro-tech headers paired with exceptionally legible, ergonomic mobile body text. 

- **Display & Headlines (`Space Grotesk`):** Chosen for its monospaced-adjacent structural cuts, quirky vintage tech cadence, and robust rendering at tight grid footprints. Used in all caps or title caps for quest banners, stat cards, and level indicators.
- **Narrative & UI (`Plus Jakarta Sans`):** Smooth, warm, and highly readable. Prevents the eye fatigue typical of prolonged pixel font reading. Accommodates lengthy AI Game Master story prompts, real-world navigation updates, and inventory descriptions.
- **Labels & Micro-Data:** Set with bold weights and expanded tracking to resemble vintage game cartridge specs and arcade HUD chips.

## Layout & Spacing

The interface is structured along a strict 4px/8px modular grid that matches the pixel block nature of the aesthetic while preserving fluid mobile responsiveness.

- **Layout Grid:** 
  - **Mobile:** 4-column fluid layout with `margin-mobile` (16px) and `gutter-mobile` (12px). All HUD elements and primary action controls pin to bottom reach zones.
  - **Desktop / Tablet:** 12-column layout capped at a max-width of `960px` to maintain the feeling of an intimate handheld expedition compendium rather than a sprawling data dashboard.
- **Rhythm & Safe Areas:** Vertical spacing leverages `space-md` (16px) between sequential interaction cards, and `space-xl` (40px) to separate distinct expedition chapters and map vistas. Touch targets enforce a strict minimum boundary of 48px by 48px.

## Elevation & Depth

This design system deliberately excludes blurry ambient Gaussian dropshadows. Depth is purely physical, mechanical, and extruded—reminiscent of tactile plastic switches, chunky pixel blocks, and layered timber panels.

- **The Hard Pixel Extrusion:**
  - Cards, buttons, and badges utilize an opaque outer boundary: `border: 2px solid #2B2118`.
  - Elevation is achieved strictly via directional hard drop blocks: `box-shadow: 0px 4px 0px 0px #2B2118`.
  - Elevated modal panels and quest overlays jump to: `box-shadow: 0px 8px 0px 0px #2B2118`.
- **Top Bevel Highlight:**
  - Elevated surfaces feature a 2px inner highlight inset along the top edge (`inset 0px 2px 0px 0px rgba(255, 255, 255, 0.45)`) paired with a bottom inner shade (`inset 0px -2px 0px 0px rgba(0, 0, 0, 0.15)`) to simulate cast stone or carved wood blocks.
- **Physical "Press" Feedback:**
  - Interactive elements sink when depressed. On `:active`, components transform down (`transform: translateY(4px)`) and compress their hard shadow (`box-shadow: 0px 0px 0px 0px #2B2118`), creating instantaneous tactile response.

## Shapes

The geometric vocabulary prioritizes squarish, chunky silhouettes with subtle 4px rounded corners (`roundedness: 1`). This provides the illusion of chiseled wood, tumbled stone, and 8-bit masonry, preventing modern pill-fatigue while keeping mobile tap targets comfortable to touch.

- **Core Elements (Cards, Buttons, Inputs):** 4px corner radius (`rounded-md` / `0.25rem`). Maintains the chunky pixel geometry while preventing needle-sharp corners.
- **Pill Badges:** Limited strictly to stat tags, XP pills, and status orbs to balance soft friendly modern touches with rigid architectural containers.

## Components

### Buttons
- **Primary ("Adventure / Action"):** Background `#6FAF5F`, solid 2px `#2B2118` border, hard drop `0px 4px 0px 0px #3F7042`. Text `#FFFDF5` with subtle letterpress effect.
- **Secondary ("Craft / Inventory"):** Background `#D8B892`, solid 2px `#2B2118` border, hard drop `0px 4px 0px 0px #A9784F`. Text `#2B2118`.
- **XP / Special ("Claim Reward"):** Background `#E5B84B`, solid 2px `#2B2118` border, hard drop `0px 4px 0px 0px #B88526`. Text `#2B2118`.
- **Tactile State Transition:** On click/tap, translateY(4px) with shadow zeroed out.

### Cards & Dialogues
- **Quest Card:** Surface `#FFFDF5`, 2px `#2B2118` border, hard drop `0px 6px 0px 0px #2B2118`. Inset top highlight line. Headers flanked by mini pixel glyph brackets (e.g., `[ QUEST: THE ANCIENT OAK ]`).
- **AI Game Master Bubble:** Surface `#8FC8D8` with 10% opacity tint or solid `#FFFDF5` with `#8FC8D8` top-ridge pixel stripe (3px tall). Contains AI speech text set in `body-md`.

### Chips & Stat Badges
- **Biome & Skill Chips:** 4px radius, 1.5px `#2B2118` border, 2px bottom shadow. Background variations: `#F7F3E8` for inactive, `#6FAF5F` for active exploration mode, `#E5B84B` for player level indicators.

### Inputs & Search Fields
- **Item/Action Fields:** Recessed well styling. Background `#EFE8D3`, 2px `#2B2118` border, inset inner shadow `inset 0px 3px 0px 0px rgba(43, 33, 24, 0.12)`. Focus swaps border to `#3F7042` with 2px hard extrusion.

### Checkboxes & Progress Gauges
- **Checkboxes:** 20px x 20px chunky square, 2px `#2B2118` border. When checked, filled with `#6FAF5F` displaying a hard 4px pixel checkmark glyph in `#FFFDF5`.
- **Health / XP Bars:** Segmented notched meters. Recessed background `#EFE8D3` framed by 2px border, filled with stepped horizontal blocks of `#6FAF5F` (Stamina) or `#E5B84B` (XP) with 1px spacer gaps between units.

### Environmental Decorative Elements
- **Pixel Foliage Accents:** Micro 3-pixel grass tufts (`#6FAF5F`) and golden star blooms (`#E5B84B`) positioned at container header borders to frame world milestones and location check-ins.