---
name: Precision Energy Intelligence
colors:
  surface: '#f8fafb'
  surface-dim: '#d8dadb'
  surface-bright: '#f8fafb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f5'
  surface-container: '#eceeef'
  surface-container-high: '#e6e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#43474c'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#eff1f2'
  outline: '#73777c'
  outline-variant: '#c3c7cc'
  surface-tint: '#4b6173'
  primary: '#001625'
  on-primary: '#ffffff'
  primary-container: '#142b3b'
  on-primary-container: '#7c93a6'
  inverse-primary: '#b2c9de'
  secondary: '#006a64'
  on-secondary: '#ffffff'
  secondary-container: '#86f5ea'
  on-secondary-container: '#00716a'
  tertiary: '#001726'
  on-tertiary: '#ffffff'
  tertiary-container: '#022c44'
  on-tertiary-container: '#7394b0'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#cee5fb'
  primary-fixed-dim: '#b2c9de'
  on-primary-fixed: '#051e2d'
  on-primary-fixed-variant: '#33495a'
  secondary-fixed: '#86f5ea'
  secondary-fixed-dim: '#69d8ce'
  on-secondary-fixed: '#00201e'
  on-secondary-fixed-variant: '#00504b'
  tertiary-fixed: '#cbe6ff'
  tertiary-fixed-dim: '#a8cae9'
  on-tertiary-fixed: '#001e30'
  on-tertiary-fixed-variant: '#284a63'
  background: '#f8fafb'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
  sidebar-surface: '#142B3B'
  sidebar-surface-hover: '#1C384D'
  sidebar-surface-active: '#20435C'
  sidebar-border: '#20435C'
  sidebar-text: '#F5F7F8'
  sidebar-text-muted: '#7E99AB'
  surface-card: '#FFFFFF'
  surface-canvas: '#F5F7F8'
  border-subtle: '#E4E8EB'
  border-strong: '#CBD5DB'
  text-primary: '#142B3B'
  text-muted: '#526B7A'
  text-faint: '#8A9EA8'
  chart-primary: '#159A91'
  chart-secondary: '#142B3B'
  chart-tertiary: '#7E99AB'
  chart-grid: '#E4E8EB'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.03em
  label-sm:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 12px
    letterSpacing: 0.05em
  kpi-value:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.02em
  tabular-data:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system delivers a disciplined, high-density analytical workspace built specifically for energy trading desks, quantitative market analysts, and power procurement leads evaluating UK electricity market wind forecasts. The visual language rejects decorative ornamentation—avoiding gradients, illustrations, synthetic drop-shadows, and extraneous micro-interactions—in favor of rigorous structural precision, flat geometric surfaces, exact numeric alignment, and immediate signal-to-noise clarity.

Taking cues from precision-engineered interfaces like Linear and Vercel Dashboard, the aesthetic is rooted in Swiss modernist information design and utilitarian data presentation. The experience communicates operational authority, audit-grade reliability, and calm computational efficiency under high cognitive loads. High-contrast typography and precise grid lines organize real-time generation metrics, error vectors, and historical cutoffs without visual distraction.

## Colors

The color architecture is built around three foundational tones: Deep Navy (`#142B3B`), Teal (`#159A91`), and Off-white (`#F5F7F8`). To maintain absolute analytical focus and prevent cognitive friction, standard traffic-light chromatic schemes (red/green alerts) are strictly prohibited. Bias indicators, over/under forecasts, and error deltas are communicated through sign markers (`+`/`-`), structural layout placement, and directional contrast between Deep Navy and Teal.

- **Deep Navy (`#142B3B`)**: Serves as the primary structural anchor. It covers the fixed 240px application sidebar, primary numerical readouts, table headers, primary typographic hierarchy, and the historical baseline data traces in time-series plots.
- **Teal (`#159A91`)**: Reserved exclusively for high-intent actions, active navigation states, forecast series curves, and interactive focus triggers. It acts as the lone luminous accent in a quiet monochromatic foundation.
- **Off-white (`#F5F7F8`)**: Forms the overall canvas, panel backing, and card container foundations. It mitigates eye fatigue across intensive 1440px desktop sessions while maintaining high contrast against pure white inner modules and crisp borders.
- **Derived Neutrals**: Systemic borders, table delimiters, and muted metadata levels are derived by stepping between Off-white and Deep Navy (`#E4E8EB` for grid dividers, `#CBD5DB` for boundary controls, and `#526B7A` for explanatory labels).

## Typography

Typography relies uniformly on **Inter** to ensure geometric neutrality, robust rendering across non-retina displays, and flawless OpenType feature support.

1. **Tabular Numerics (`tnum`)**: All numeric presentations—including KPI cards, time codes, megawatt volumes, error values, and coordinate ticks—must activate OpenType tabular numbers (`font-feature-settings: "tnum" 1`). This enforces uniform character widths across dynamic updates and preserves vertical alignment across financial matrices.
2. **Density Hierarchy**: Font sizing tops out conservatively at 28px for page titles. Metric cards leverage 24px semi-bold integers paired with 11px uppercase track labels. Compact 12px body tiers enable high row counts in data tables without vertical sprawl.
3. **Weight Distribution**: Weights are strictly restricted to Regular (400) for readings, Medium (500) for interface labels/controls, and Semi-Bold (600) for section titles and primary metrics. Light and Black weights are omitted to safeguard high-density readability.

## Layout & Spacing

The layout is optimized for high-resolution desktop terminals, anchored to a **1440px viewport baseline**. It comprises a persistent 240px fixed left rail and a fluid analytical work canvas with rigid boundaries.

- **Grid Architecture**: The main viewport spans a 12-column layout governed by a strict 16px (`1rem`) gutter and 24px (`1.5rem`) outer margin. KPI rows leverage uniform 4-column cards (3 spans each) or dual-span data columns.
- **Top Header**: Anchored to a fixed 56px height, containing contextual page headers, delivery date toggles, and the immutable 15:00 UK Cutoff badge.
- **Rhythm & Padding**: Vertical and horizontal component padding is calibrated strictly in multiples of 4px. Compact table cell padding uses 8px vertically and 12px horizontally to display over 20 delivery periods within an unscrollable viewport frame.
- **Scroll Containment**: Horizontal screen overflow is prevented. Complex analytical tables implement self-contained vertical scroll containers with fixed stickied table headers.

## Elevation & Depth

Visual hierarchy rejects multi-stop drop shadows, floating elevations, and frosted glass effects. Elevation is articulated exclusively through **flat structural tiers, tonal layering, and 1px crisp hairline borders**:

1. **Base Foundation**: The browser canvas sits on `#F5F7F8`.
2. **Card Surfaces**: Metric cards, data viewports, and table housings utilize pure white (`#FFFFFF`) or off-white tonal containers defined by a crisp `1px solid #E4E8EB` hairline stroke.
3. **Sidebar Depth**: The 240px sidebar operates as an inverted deep tonal monolith (`#142B3B`), separated from the content frame by a single `1px solid #20435C` delimiter.
4. **Interactive Overlays**: Menus, cutoff selectors, and popover date pickers utilize an unblurred, razor-sharp 1px border (`#CBD5DB`) accompanied by an extremely faint ambient contact shadow: `box-shadow: 0 1px 3px 0 rgba(20, 43, 59, 0.06), 0 1px 2px -1px rgba(20, 43, 59, 0.04)`.

## Shapes

The geometric form factor is restrained and architectural (`roundedness: 1`):

- **Panels & Cards**: Bounded by a crisp 4px border radius (`0.25rem`). Curved container edges exceeding 6px are prohibited to retain structural density and alignment with charts.
- **Interactive Controls**: Buttons, input fields, selector toggles, and chips share the consistent 4px radius.
- **Indicators**: Status dots and data plot nodes remain pure circles (`50%`), while categorical chips use flat 3px or 4px rectangles rather than fully rounded pill shapes.

## Components

### Buttons & Action Triggers
- **Primary Button**: Solid Deep Navy (`#142B3B`) fill, Off-white (`#F5F7F8`) label, 4px radius, 32px height, padding: `0 12px`. Hover state shifts fill to `#20435C`. Focus ring: `2px solid #159A91` with a 1px offset.
- **Secondary / Action Accent Button**: Solid Teal (`#159A91`) fill, Off-white label. Used strictly for triggering data evaluations or key filter updates.
- **Ghost / Outline Button**: Transparent fill, `1px solid #CBD5DB` border, Deep Navy text. Hover state: surface `#F5F7F8`, border `#142B3B`.

### KPI Metric Tiles
- **Container**: White (`#FFFFFF`) surface, `1px solid #E4E8EB` border, 4px corner radius, padding: `16px`.
- **Top Row**: 11px uppercase label in `#526B7A` with letter spacing `0.03em`. Optional trailing secondary indicator (e.g., target delta or threshold unit) in `#8A9EA8`.
- **Primary Metric**: 24px `Inter` semi-bold in Deep Navy (`#142B3B`), using tabular numerals (`tnum`).
- **Footer Metadata**: 12px descriptor detailing sample size or time context (e.g., `Evaluated: 744 Hours`), styled in `#526B7A`.

### Tables & Data Grids
- **Header**: `#F5F7F8` background, 32px height, 11px uppercase labels in `#526B7A`, `1px solid #E4E8EB` bottom border. Right-aligned for numerical measurements (MW, Error, Forecast), left-aligned for time stamps.
- **Rows**: 36px standard row height, alternating white/canvas background or uniform white with `1px solid #E4E8EB` bottom hairline dividers. Hover: `#F5F7F8`.
- **Numeric Cells**: Styled in `12px Inter` tabular figures. Negative deviations (`Underforecast`) and positive deviations (`Overforecast`) are distinguished through explicit algebraic prefixes (`+1,692.47 MW` or `-342.10 MW`) rendered in Deep Navy rather than colored tags.

### Filter Bars & Dropdown Selectors
- **Control Bar**: Unified height of 32px.
- **Dropdown Field**: `1px solid #CBD5DB` border, white surface, Deep Navy value text with a subtle chevron indicator.
- **Cutoff Selector**: Persistent 15:00 UK Cutoff display framed as an intentional operational constraint: `#F5F7F8` background with an inset Deep Navy label and active Teal status mark.

### Data Visualizations & Charts
- **Palette**: Forecast curves in Teal (`#159A91`, 2px solid stroke); Actual generation series in Deep Navy (`#142B3B`, 2px solid stroke); Error distribution bars in neutral `#7E99AB` or alternating Navy/Teal.
- **Grid Lines**: Horizontal rules only, styled in `1px solid #E4E8EB`. Vertical tick lines are removed.
- **Tooltips**: Minimal white panel, `1px solid #142B3B`, no rounded pill shapes, tabular mono-spaced numbers aligned left-to-right.