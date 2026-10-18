# Design System & Component Blueprints — Stage 1
_Applying `/apple-design` principles to Thank Me Later_

---

## 1. Foundational Design System

### 1.1 Color System & Materials
- **Base Palette**: Neutral, monochrome core with a single vibrant accent for interactive states.
  - `bg-background`: `hsl(0 0% 100%)` (Light) / `hsl(240 10% 3.9%)` (Dark)
  - `bg-foreground`: `hsl(240 10% 3.9%)` (Light) / `hsl(0 0% 98%)` (Dark)
  - `bg-card`: `hsl(0 0% 100%)` (Light) / `hsl(240 5.9% 10%)` (Dark)
  - `accent`: `hsl(240 5.9% 10%)` (Light) / `hsl(0 0% 98%)` (Dark) - Used for primary buttons, active states.
  - `border`: `hsl(240 5.9% 90%)` (Light) / `hsl(240 3.7% 15.9%)` (Dark)
- **Translucent Chrome**: Navigation and other persistent UI elements use a translucent material effect.
  - `background`: `rgba(255, 255, 255, 0.6)` (Light) / `rgba(10, 10, 20, 0.6)` (Dark)
  - `backdrop-filter`: `blur(20px) saturate(180%)`
  - `border-bottom`: `1px solid rgba(0, 0, 0, 0.1)` (Light) / `1px solid rgba(255, 255, 255, 0.1)` (Dark)
- **State Overlays**:
  - `hover`: Subtle `rgba(0, 0, 0, 0.05)` overlay.
  - `active`/`pressed`: `rgba(0, 0, 0, 0.08)` overlay and `transform: scale(0.97)`.

### 1.2 Typography
- **Font Stack**: `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Optical Sizing Scale**:
  | Use Case | Font Size (rem) | Line Height | Letter Spacing | Font Weight |
  |---|---|---|---|---|
  | Display Heading | `clamp(2.5rem, 6vw, 4.5rem)` | `1.05` | `-0.025em` | `700` |
  | Page Title | `2rem` | `1.1` | `-0.02em` | `600` |
  | Card Title | `1.25rem` | `1.2` | `-0.01em` | `600` |
  | Body | `1rem` | `1.6` | `0` | `400` |
  | Small / Meta | `0.875rem` | `1.4` | `0` | `400` |
  | Button | `0.9375rem` | `1` | `0` | `500` |

### 1.3 Spacing & Layout
- **Grid**: 8pt grid system. All spacing is a multiple of `0.5rem` (`8px`).
- **Layout**: Centered content column with a max-width of `1280px`.

### 1.4 Motion & Animation (Springs)
All interactive animations use spring physics. No `ease-in-out` cubic beziers.
- **Default Spring**: Critically damped for UI elements appearing/disappearing.
  - `type: "spring"`, `damping: 1.0`, `response: 0.3` (`bounce: 0`, `duration: 0.3` in Framer Motion).
- **Gesture Spring**: Slightly underdamped for elements responding to a flick/drag.
  - `type: "spring"`, `damping: 0.8`, `response: 0.4` (`bounce: 0.2`, `duration: 0.4` in Framer Motion).
- **Reduced Motion**: All transforms and springs are replaced with simple cross-fades (`opacity`).
  - `@media (prefers-reduced-motion: reduce)`

---

## 2. Component Blueprints

### 2.1 Button
- **Anatomy**: Subtle rounded corners (`radius: 8px`), light inner shadow for depth.
- **Interaction**:
  - `on:pointerdown`: Instant `scale(0.97)` transform and darker background tint.
  - `on:pointerup`: Spring back to `scale(1.0)`.
- **States**: `primary`, `secondary`, `ghost`.

### 2.2 File Dropzone (`/upload`)
- **Anatomy**: Dashed border, centered icon and text prompt.
- **States**:
  - `default`: Neutral state.
  - `ondragover`: Border becomes solid, background color changes, icon animates. Animation is a subtle spring-based scale-up (`scale(1.02)`).
  - `uploading`: Progress bar fills with a smooth spring animation.
  - `error`: Border turns red, error message appears.

### 2.3 Chip / Badge
- **Anatomy**: Pill-shaped, small padding. Used for skills and tags.
- **Interaction**:
  - `editable`: Shows an `(x)` icon on hover, which can be clicked to remove.
  - `on:click` (filter chips): Springs to an "active" state (background color change).

### 2.4 Job Card (`/results`)
- **Anatomy**:
  - `Stack` layout with `Card` container.
  - Header: `Company Logo`, `Job Title`, `Company Name`, `Location`.
  - Body: `Match Score Badge`, `Match Reason` text, `Matched/Missing Skills` chips.
  - Footer: `Posted Date`, `Apply Button`.
- **Interaction**:
  - The entire card is a button that expands/collapses the full job description.
  - `on:click`: The card body smoothly expands using a spring animation (`layout` animation in Framer Motion). The expand icon rotates.
  - `Apply Button`: Standard primary button behavior.

### 2.5 SSE Progress Indicators
- **Parser Progress**: A determinate progress bar that animates its width based on SSE `progress` events. The animation is a gentle spring to avoid jitter.
- **Source Status**:
  - A grid of 7 logos representing the job sources.
  - `pending`: Logo is desaturated (`grayscale(100%)`).
  - `loading`: A subtle spinner appears over the logo.
  - `success`: Logo becomes fully saturated.
  - `error`: Logo remains desaturated and a small error icon appears.
  - State transitions are animated with a quick cross-fade.

---

## 3. Accessibility Overrides

- **`prefers-reduced-motion`**:
  - All spring-based layout and transform animations are replaced with `opacity` fades (`duration: 200ms`).
- **`prefers-reduced-transparency`**:
  - The `backdrop-filter` is removed from all material surfaces.
  - Backgrounds become opaque (`rgba(255, 255, 255, 0.95)` -> `rgb(255, 255, 255)`).
- **`prefers-contrast`**:
  - Borders become thicker (`2px`) and fully opaque.
  - Text and background contrast ratios are increased.
