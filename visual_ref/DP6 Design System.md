# DP6 Design System

*Markdown export — 10 Aug 2026. Single-file reference: brand rules, all design tokens and every component API.*

**DP6** is a Brazilian data-intelligence consultancy (São Paulo, founded 2007), specialising in **Marketing Analytics, MarTech and Data Science**. In 2025–26 it became **part of the brandtech group** (The Brandtech Group / You & Mr Jones) and refreshed its identity to align globally — adopting the group's vibrant yellow and the official "part of the brandtech group" endorsement. The name and the three-bar grafismo stay.

Its work product is data: tracking and analytics implementations, data pipelines, dashboards, reports and predictive models for large advertisers. That is why this system treats **data visualisation as a first-class surface**, with an official chart palette split for light and dark backgrounds.

## Sources given to me

| Source | Notes |
| --- | --- |
| `assets/reference/Guideline Refresh DP6 Brandtech.pdf` | 29-page brand refresh guideline (índice: Introdução, Logos oficiais, Grafismo, Tipografia, Cores, Iconografia, Assinatura de e-mail). The single source of truth for everything below. |
| `assets/logos/*.png` | 10 official lockups: primary, monochrome, horizontal, horizontal-with-divider and vertical, each in dark and light artwork. |
| `assets/reference/paleta-de-cores.png`, `paleta-graficos.png` | Base palette and chart palette specimen boards. |
| dp6.com.br (public pages, read via search) | Used only for information architecture and copy tone in the website UI kit. |

**No codebase and no Figma file were provided.** There is therefore no source-of-truth component inventory: the component set below is the standard primitive set sized to DP6's needs, and the UI kits are brand-faithful constructions rather than recreations of existing product screens. If you can attach the site repo or a Figma library, the kits should be rebuilt against it.

---

## CONTENT FUNDAMENTALS

**Language.** Portuguese (Brazil) is the primary language; English exists for international audiences (the Medium blog runs both). Keep accents and PT-BR number formatting: `R$ 1.284.930`, `3,84%`, `4,59`.

**Voice.** Expert consultant, not vendor. Confident, technical, plain. The brand explains complexity rather than performing it. Sentences are declarative and short-to-medium; jargon is used precisely (GA4, server-side, Data Mesh, MMM, clean room) and never as decoration.

**Person.** "Nós" for DP6 — *"Somos especialistas…", "Nossa missão é estruturar dados…", "Recomendamos utilizar as cores abaixo"*. The reader is addressed as *você* / *sua empresa*, usually as an invitation: *"Quer estruturar um projeto com a gente?"*.

**Headline patterns.**
- Imperative discovery verbs on content: *"Descubra como o Data Mesh…"*, *"Entenda o impacto do '(not set)' no GA4"*, *"Saiba como se preparar…"*.
- Provocative question + payoff: *"Sua arquitetura de MarTech é um 'Data Mess'?"*.
- Numbered promise: *"10 aprendizados com Marketing Mix Modeling"*, *"4 padrões de engenharia de dados"*.
- CTA is almost always **SAIBA MAIS** (uppercase, letterspaced) or *"Fale com a DP6"*.

**Casing.** Sentence case for headlines and body. UPPERCASE with wide letterspacing for section labels, eyebrows, buttons, table headers and slide dividers (`I N T R O D U Ç Ã O`, `SAIBA MAIS`). Never uppercase a whole paragraph.

**Numbers & claims.** Always attributed and specific: *"+34% de ROAS"*, *"+500 projetos"*, *"desde 2007"*. Pair a metric with the mechanism that produced it.

**Emoji: never.** Not in product, marketing, decks or reports. Unicode symbols are used only functionally (✓ in checklists, × to dismiss, / in breadcrumbs).

**Vibe.** Technical clarity with warmth from the yellow. Sober, engineered, no hype words ("revolucionário", "mágico") — DP6 says *estruturar*, *governança*, *confiabilidade*, *escala*, *maturidade digital*.

---

## VISUAL FOUNDATIONS

**Colour.** Four base colours only: **amarelo #FFB302** (the brandtech yellow — accent, never a body-text colour on light), **preto #1D1D1B** (the dominant brand surface), **cinza #5B626C**, **branco #FFFFFF**. Amarelo is used at roughly 5–10% coverage: one CTA, one rule, one highlighted data series, one watermark. Full-bleed amarelo is reserved for statement moments (a CTA band, a quote slide).

Mandated pairings (guideline, "Combinação de cores base"):
- dark background → white **or** amarelo text · never cinza
- cinza background → white text only · never preto or amarelo
- amarelo background → preto text · never white
- light background → preto or cinza text · never amarelo

**Chart palette.** Semantic and split by background. Light: azul `#1A365D` (contraste), vermelho `#D64500` (atenção/quedas), verde `#059669` (positivo), roxo `#6B46C1` (inovação/premium), rosa `#D81B60` (clientes/tendências), areia `#F4F1EA` (fundo neutro — cards and slide backgrounds only, never a bar or line). Dark: `#63B3ED`, `#E53E3E`, `#34D399`, `#B794F4`, `#FF53A1`, `#D0D3D4`.

**Type.** **Ubuntu** (Google Fonts, Dalton Maag) is primary — it echoes the logo's rounded-geometric wordmark. **Verdana** is the secondary/system face for e-mail signatures and office documents. Ubuntu Mono handles figures in dashboards. Display sizes run *light* (300) with slightly negative tracking; headings are medium (500); body regular (400) at 16/1.65. Eyebrows: uppercase, 12–16px, `.28em` tracking. Scale is a 1.25 major third from 16px.

**Layout.** 1200px max content width, 64px page gutters on desktop, 96px vertical section rhythm. Generous left-aligned composition with a lot of preto negative space; content blocks are anchored by a 2px × 120–180px amarelo rule sitting above or beside the label. Sticky preto header (80px); the footer is `--neutral-950`. Nothing else is fixed.

**Backgrounds.** Flat colour, always — no photographic hero, no gradient wash, no noise or texture. Depth comes from the **grafismo** (three ascending, right-sheared bars) used at 10–15% opacity as an oversized watermark bleeding off a corner, or at full strength as an accent. The grafismo may also mask photography or be drawn in outline. Bege `#F4F1EA` is the only warm surface; use it to give charts breathing room.

**Imagery.** No photography or illustration library was supplied, so this system ships none and never invents any: image areas are neutral preto/bege blocks with a grafismo mark. When real photography arrives, the guideline's direction implies cool, sober, high-contrast, un-stylised images — never warm-filtered, never grainy, never hand-drawn.

**Corners & borders.** The brand is squared-off. Radii: 0/2/4/8/12px; `--radius-pill` is reserved for chips, chart legends and the palette specimen capsules. Borders are 1px hairlines in `--neutral-200` (dark: `--neutral-700`); 2px is used for the amarelo rule, keylines and control borders.

**Cards.** Flat by default: white surface, 1px hairline border, 8px radius, 24px padding, **no shadow at rest**. Emphasis comes from a 2px amarelo top rule (`accent`) or a bege/preto surface swap — never a coloured left border alone, never a gradient.

**Shadows.** Rare and soft, keyed to elevation events only: `--shadow-md` on card hover, `--shadow-lg` on modals/toasts, `--shadow-brand` (amarelo glow) for the occasional promoted CTA. No inner shadows.

**Transparency & blur.** Only two uses: the modal scrim (preto at 60% + 2px blur) and grafismo watermarks at 8–15% opacity. No frosted-glass panels, no translucent cards.

**Animation.** Short and flat: 140ms for hover/focus/press, 220ms for cards and tab changes, 400ms for overlays and section reveals, all on `cubic-bezier(.2,.6,.2,1)`. Fades and small (≤8px) translations only. No bounce, elastic, spin or parallax. Everything collapses to 0ms under `prefers-reduced-motion`.

**States.** Hover: primary buttons darken (`--amarelo-600`), secondary borders turn amarelo, ghost picks up `--surface-muted`, cards lift 2px with `--shadow-md`. Press: darken again (`--amarelo-700`) plus `scale(.98)`. Focus: 3px amarelo ring at 45% opacity, plus an amarelo border on fields. Disabled: 40% opacity, pointer events off — never a grey re-colour. Links are preto (amarelo on dark) with a 1px underline at 3px offset; hover shifts to `--amarelo-700`.

---

## ICONOGRAPHY

The guideline (06. ICONOGRAFIA) sets rules but ships **no icon library**: icons may be **solid fill or outline**, never mixed in the same piece; outline icons must all share one stroke weight; colours come from the official palette with high contrast against the background; and **no gradients, hand-drawn strokes or 3D**.

Since no proprietary set exists, this system **substitutes Lucide** (outline, uniform 2px stroke, geometric — the closest match to Ubuntu's rounded-geometric drawing). **⚠ Flagged substitution:** replace it if DP6 has an internal icon set.

Load it from CDN and let `Icon` render names:

```html
<script src="https://unpkg.com/lucide@0.469.0/dist/umd/lucide.min.js"></script>
```
```jsx
<Icon name="bar-chart-3" size={20} />
```

The **grafismo** (three ascending bars) is not an icon — it is the brand graphic; use `Grafismo`. Emoji are never used. Unicode symbols appear only functionally (✓, ×, /).

**Fonts:** Ubuntu and Ubuntu Mono load from Google Fonts (`tokens/fonts.css`) — the licence is free and this is what the guideline prescribes, so no substitution was needed. **⚠ If you need offline/self-hosted builds, send the `.woff2` files and I'll swap the `@font-face` rules to local paths.**

---

## Index

| Path | What it is |
| --- | --- |
| `styles.css` | Entry point — `@import`s every token file. Consumers link only this. |
| `tokens/` | `fonts.css`, `colors.css`, `typography.css`, `spacing.css`, `shape.css`, `motion.css`, `base.css` |
| `assets/logos/` | 10 official lockups (see `components/brand/Logo.prompt.md` for which to use) |
| `assets/reference/` | Source guideline PDF and palette boards |
| `guidelines/` | 18 foundation specimen cards (Colors, Type, Spacing, Brand) |
| `components/core/` | `Button`, `IconButton`, `Icon`, `Badge`, `Tag`, `Card` |
| `components/forms/` | `Input`, `Select`, `Checkbox`, `Radio`, `Switch` |
| `components/navigation/` | `Tabs`, `Breadcrumb` |
| `components/feedback/` | `Dialog`, `Toast`, `Tooltip` |
| `components/brand/` | `Logo`, `Grafismo` |
| `ui_kits/website/` | Clickable institutional site: home, serviços, insights, contato |
| `ui_kits/report/` | Clickable client report/dashboard with chart primitives |
| `templates/deck/` | Reusable DP6 deck (Design Component) — cover, section divider, chart slide, statement, closing |
| `slides/` | 8 sample 1280×720 slides in the guideline's own deck style |
| `SKILL.md` | Agent-Skills front matter for use in Claude Code |

**Intentional additions** (not defined by the source, added because the system needs them):
- `Icon` — wrapper for the substituted Lucide set, so stroke weight and sizing stay consistent.
- `Grafismo` — the guideline describes the three ascending bars in prose but supplied no vector; this renders them with CSS. Replace with official artwork when available.
- `Breadcrumb` — needed by the insights/report surfaces; styled from the guideline's label typography.
- `ui_kits/report/Charts.jsx` — minimal bar/line/donut primitives so the official chart palette has somewhere to live.


---

# DESIGN TOKENS

Entry point: `styles.css` `@import`s every file below.

## tokens/fonts.css

```css
@import url("https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&family=Ubuntu+Mono:wght@400;700&display=swap");
/* Primary: Ubuntu (Dalton Maag, Google Fonts) — declared in the brand guideline.
   Secondary: Verdana — system font, no webfont needed.
   Ubuntu Mono is included for tabular/code use in dashboards and reports. */
```

## tokens/colors.css

```css
:root{
/* ---- Base brand palette (Guideline 05. CORES) ---- */
--dp6-amarelo:#FFB302;
--dp6-preto:#1D1D1B;
--dp6-cinza:#5B626C;
--dp6-branco:#FFFFFF;

/* ---- Neutral ramp (derived from --dp6-preto / --dp6-cinza) ---- */
--neutral-0:#FFFFFF;
--neutral-50:#F7F7F6;
--neutral-100:#EFEFEE;
--neutral-200:#DFE0E2;
--neutral-300:#C4C7CB;
--neutral-400:#9BA0A7;
--neutral-500:#5B626C;
--neutral-600:#474D55;
--neutral-700:#33373C;
--neutral-800:#262728;
--neutral-900:#1D1D1B;
--neutral-950:#131312;

/* ---- Amarelo ramp (tints/shades of #FFB302, for states only) ---- */
--amarelo-100:#FFF3D6;
--amarelo-200:#FFE1A3;
--amarelo-300:#FFCC5C;
--amarelo-400:#FFBD2E;
--amarelo-500:#FFB302;
--amarelo-600:#E39C00;
--amarelo-700:#B87E00;

/* ---- Data-viz palette, light backgrounds (Guideline: CORES PARA GRÁFICOS) ---- */
--chart-blue-on-light:#1A365D;
--chart-red-on-light:#D64500;
--chart-green-on-light:#059669;
--chart-purple-on-light:#6B46C1;
--chart-pink-on-light:#D81B60;
--chart-sand-on-light:#F4F1EA;

/* ---- Data-viz palette, dark backgrounds ---- */
--chart-blue-on-dark:#63B3ED;
--chart-red-on-dark:#E53E3E;
--chart-green-on-dark:#34D399;
--chart-purple-on-dark:#B794F4;
--chart-pink-on-dark:#FF53A1;
--chart-sand-on-dark:#D0D3D4;

/* ---- Semantic aliases: light surfaces (default) ---- */
--brand:var(--dp6-amarelo);
--brand-contrast:var(--dp6-preto);
--surface-page:var(--neutral-0);
--surface-card:var(--neutral-0);
--surface-sunken:var(--neutral-50);
--surface-muted:var(--neutral-100);
--surface-sand:var(--chart-sand-on-light);
--surface-inverse:var(--dp6-preto);
--text-strong:var(--dp6-preto);
--text-body:var(--dp6-preto);
--text-muted:var(--dp6-cinza);
--text-on-brand:var(--dp6-preto);
--text-on-inverse:var(--dp6-branco);
--text-link:var(--dp6-preto);
--text-link-hover:var(--amarelo-700);
--border-subtle:var(--neutral-200);
--border-strong:var(--neutral-300);
--border-focus:var(--dp6-amarelo);
--focus-ring:0 0 0 3px rgb(255 179 2 / .45);

/* ---- Feedback (reuses the official chart palette; no new hues) ---- */
--feedback-positive:var(--chart-green-on-light);
--feedback-negative:var(--chart-red-on-light);
--feedback-info:var(--chart-blue-on-light);
--feedback-premium:var(--chart-purple-on-light);
--feedback-warning:var(--dp6-amarelo);
}

/* ---- Dark scope: apply .dp6-dark (or data-theme="dark") to any container ---- */
.dp6-dark,[data-theme="dark"]{
--surface-page:var(--dp6-preto);
--surface-card:var(--neutral-800);
--surface-sunken:var(--neutral-950);
--surface-muted:var(--neutral-700);
--surface-sand:var(--neutral-800);
--surface-inverse:var(--dp6-branco);
--text-strong:var(--dp6-branco);
--text-body:var(--dp6-branco);
--text-muted:var(--neutral-300);
--text-on-inverse:var(--dp6-preto);
--text-link:var(--dp6-amarelo);
--text-link-hover:var(--amarelo-300);
--border-subtle:var(--neutral-700);
--border-strong:var(--neutral-600);
--feedback-positive:var(--chart-green-on-dark);
--feedback-negative:var(--chart-red-on-dark);
--feedback-info:var(--chart-blue-on-dark);
--feedback-premium:var(--chart-purple-on-dark);
}
```

## tokens/typography.css

```css
:root{
--font-primary:"Ubuntu","Verdana","Segoe UI",sans-serif;
--font-secondary:Verdana,sans-serif;
--font-mono:"Ubuntu Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
--font-display:var(--font-primary);
--font-body:var(--font-primary);

--weight-light:300;
--weight-regular:400;
--weight-medium:500;
--weight-bold:700;

/* Type scale — 1.25 major third from 16px */
--text-2xs:11px;
--text-xs:12px;
--text-sm:14px;
--text-base:16px;
--text-md:18px;
--text-lg:20px;
--text-xl:25px;
--text-2xl:31px;
--text-3xl:39px;
--text-4xl:49px;
--text-5xl:61px;
--text-6xl:76px;

--leading-tight:1.05;
--leading-snug:1.2;
--leading-normal:1.5;
--leading-relaxed:1.65;

/* Wide letterspacing is a DP6 signature: section labels and eyebrows */
--tracking-eyebrow:.28em;
--tracking-label:.12em;
--tracking-normal:0;
--tracking-display:-.015em;

/* Semantic roles */
--type-eyebrow:var(--weight-regular) var(--text-xs)/var(--leading-normal) var(--font-primary);
--type-display:var(--weight-light) var(--text-5xl)/var(--leading-tight) var(--font-primary);
--type-h1:var(--weight-medium) var(--text-4xl)/var(--leading-snug) var(--font-primary);
--type-h2:var(--weight-medium) var(--text-2xl)/var(--leading-snug) var(--font-primary);
--type-h3:var(--weight-medium) var(--text-lg)/var(--leading-snug) var(--font-primary);
--type-body:var(--weight-regular) var(--text-base)/var(--leading-relaxed) var(--font-primary);
--type-body-sm:var(--weight-regular) var(--text-sm)/var(--leading-normal) var(--font-primary);
--type-button:var(--weight-medium) var(--text-sm)/1 var(--font-primary);
--type-metric:var(--weight-bold) var(--text-3xl)/var(--leading-tight) var(--font-primary);
}
```

## tokens/spacing.css

```css
:root{
--space-0:0px;
--space-1:4px;
--space-2:8px;
--space-3:12px;
--space-4:16px;
--space-5:24px;
--space-6:32px;
--space-7:40px;
--space-8:56px;
--space-9:72px;
--space-10:96px;
--space-11:128px;

--gutter-page:24px;
--gutter-page-lg:64px;
--container-max:1200px;
--container-narrow:720px;
--section-y:var(--space-10);

/* Logo clear space = 50% of the mark's height on every side (Guideline: RESPIRO) */
--logo-clearspace:.5em;
--logo-min-width-print:3cm; /* @kind spacing */
--logo-min-width-screen:150px;
}
```

## tokens/shape.css

```css
:root{
/* Corners: the brand is geometric and squared-off. Small radii only;
   the pill radius is reserved for chart legends/chips, as in the guideline. */
--radius-none:0px;
--radius-xs:2px;
--radius-sm:4px;
--radius-md:8px;
--radius-lg:12px;
--radius-pill:999px;

--border-width:1px;
--border-width-strong:2px;
--rule-thickness:2px;

/* Shadows are used sparingly — elevation is expressed with flat contrast first */
--shadow-none:none;
--shadow-sm:0 1px 2px rgb(29 29 27 / .06);
--shadow-md:0 4px 12px rgb(29 29 27 / .08);
--shadow-lg:0 16px 40px rgb(29 29 27 / .14);
--shadow-brand:0 8px 24px rgb(255 179 2 / .28);
}
```

## tokens/motion.css

```css
:root{
--duration-instant:80ms; /* @kind other */
--duration-fast:140ms; /* @kind other */
--duration-base:220ms; /* @kind other */
--duration-slow:400ms; /* @kind other */
--ease-standard:cubic-bezier(.2,.6,.2,1); /* @kind other */
--ease-out:cubic-bezier(0,0,.2,1); /* @kind other */
--ease-in:cubic-bezier(.4,0,1,1); /* @kind other */
--transition-control:background-color var(--duration-fast) var(--ease-standard),color var(--duration-fast) var(--ease-standard),border-color var(--duration-fast) var(--ease-standard),box-shadow var(--duration-fast) var(--ease-standard);
--press-scale:.98; /* @kind other */
}
@media (prefers-reduced-motion:reduce){:root{--duration-instant:0ms /* @kind other */;--duration-fast:0ms /* @kind other */;--duration-base:0ms /* @kind other */;--duration-slow:0ms /* @kind other */}}
```

## tokens/base.css

```css
body{font:var(--type-body);color:var(--text-body);background:var(--surface-page);-webkit-font-smoothing:antialiased}
a{color:var(--text-link);text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:3px;transition:color var(--duration-fast) var(--ease-standard)}
a:hover{color:var(--text-link-hover)}
::selection{background:var(--dp6-amarelo);color:var(--dp6-preto)}
.dp6-eyebrow{font:var(--type-eyebrow);letter-spacing:var(--tracking-eyebrow);text-transform:uppercase;color:var(--text-muted)}
.dp6-rule{height:var(--rule-thickness);background:var(--dp6-amarelo);border:0;width:120px}
```


---

# COMPONENT API

All components read from `window.DP6` when the compiled bundle (`_ds_bundle.js`) is loaded.

## core

### Button

```ts
import * as React from 'react';

/**
 * Primary call-to-action. Yellow fill + black uppercase label is the DP6 default ("SAIBA MAIS").
 */
export interface ButtonProps extends React.HTMLAttributes<HTMLElement> {
  /** Visual treatment. */
  variant?: 'primary' | 'secondary' | 'ghost' | 'inverse' | 'link';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  fullWidth?: boolean;
  /** Render as another element, e.g. 'a'. */
  as?: 'button' | 'a';
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
  children?: React.ReactNode;
}
export declare function Button(props: ButtonProps): JSX.Element;
```

### IconButton

```ts
import * as React from 'react';

/** Square, icon-only action. Always pass `label` for accessibility. */
export interface IconButtonProps extends React.HTMLAttributes<HTMLButtonElement> {
  /** Lucide icon name, or a ready-made node. */
  icon: string | React.ReactNode;
  label: string;
  variant?: 'primary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
}
export declare function IconButton(props: IconButtonProps): JSX.Element;
```

### Icon

```ts
import * as React from 'react';

/** Thin wrapper over Lucide outline icons (substituted set — DP6 has no proprietary icon library). */
export interface IconProps extends React.HTMLAttributes<HTMLElement> {
  /** Lucide icon name, e.g. 'bar-chart-3'. */
  name: string;
  size?: number;
  strokeWidth?: number;
  color?: string;
}
export declare function Icon(props: IconProps): JSX.Element;
```

### Badge

```ts
import * as React from 'react';

/** Small uppercase status marker. Tones map onto the official chart palette. */
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: 'neutral' | 'brand' | 'positive' | 'negative' | 'info' | 'premium';
  variant?: 'solid' | 'outline';
  children?: React.ReactNode;
}
export declare function Badge(props: BadgeProps): JSX.Element;
```

### Tag

```ts
import * as React from 'react';

/** Pill-shaped filter/category chip. The pill radius is reserved for chips and chart legends. */
export interface TagProps extends React.HTMLAttributes<HTMLSpanElement> {
  active?: boolean;
  onRemove?: () => void;
  children?: React.ReactNode;
}
export declare function Tag(props: TagProps): JSX.Element;
```

### Card

```ts
import * as React from 'react';

/** Flat surface container: 1px hairline border, 8px radius, shadow only while hovered. */
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  surface?: 'card' | 'sunken' | 'sand' | 'inverse';
  /** Adds the 2px amarelo rule along the top edge. */
  accent?: boolean;
  padding?: string;
  interactive?: boolean;
  children?: React.ReactNode;
}
export declare function Card(props: CardProps): JSX.Element;
```

## forms

### Input

```ts
import * as React from 'react';

/** Labelled text field. The focus ring is always amarelo. */
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  /** 'textarea' renders a multi-line field. */
  as?: 'input' | 'textarea';
  rows?: number;
}
export declare function Input(props: InputProps): JSX.Element;
```

### Select

```ts
import * as React from 'react';

/** Native select styled to match Input, with a CSS-drawn caret. */
export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  options?: Array<string | { value: string; label: string }>;
}
export declare function Select(props: SelectProps): JSX.Element;
```

### Checkbox

```ts
import * as React from 'react';

/** Square checkbox; checked state is amarelo fill with a preto tick. */
export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: React.ReactNode;
  checked?: boolean;
  disabled?: boolean;
}
export declare function Checkbox(props: CheckboxProps): JSX.Element;
```

### Radio

```ts
import * as React from 'react';

/** Single-choice control. Use for 2–5 mutually exclusive options. */
export interface RadioProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: React.ReactNode;
  checked?: boolean;
  name?: string;
  value?: string;
  disabled?: boolean;
}
export declare function Radio(props: RadioProps): JSX.Element;
```

### Switch

```ts
import * as React from 'react';

/** Instant on/off toggle (no Save step). For form submission use Checkbox instead. */
export interface SwitchProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: React.ReactNode;
  checked?: boolean;
  disabled?: boolean;
}
export declare function Switch(props: SwitchProps): JSX.Element;
```

## navigation

### Tabs

```ts
import * as React from 'react';

/** Horizontal section switcher; the active tab is underlined with the 2px amarelo rule. */
export interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  items: Array<string | { value: string; label: string }>;
  value?: string;
  onChange?: (value: string) => void;
}
export declare function Tabs(props: TabsProps): JSX.Element;
```

### Breadcrumb

```ts
import * as React from 'react';

/** Uppercase, letterspaced trail — mirrors the guideline's section-label typography. */
export interface BreadcrumbProps extends React.HTMLAttributes<HTMLElement> {
  items: Array<string | { label: string; href?: string }>;
}
export declare function Breadcrumb(props: BreadcrumbProps): JSX.Element;
```

## feedback

### Dialog

```ts
import * as React from 'react';

/** Modal over a preto 60% scrim with a light blur; amarelo rule on the top edge. */
export interface DialogProps extends React.HTMLAttributes<HTMLDivElement> {
  open?: boolean;
  title?: React.ReactNode;
  onClose?: () => void;
  footer?: React.ReactNode;
  width?: number;
  children?: React.ReactNode;
}
export declare function Dialog(props: DialogProps): JSX.Element | null;
```

### Toast

```ts
import * as React from 'react';

/** Transient confirmation. Always preto surface, tone shown by the left keyline + icon. */
export interface ToastProps extends React.HTMLAttributes<HTMLDivElement> {
  tone?: 'info' | 'positive' | 'negative' | 'warning';
  title: React.ReactNode;
  description?: React.ReactNode;
  onClose?: () => void;
}
export declare function Toast(props: ToastProps): JSX.Element;
```

### Tooltip

```ts
import * as React from 'react';

/** Hover label for icon-only controls and chart data points. */
export interface TooltipProps extends React.HTMLAttributes<HTMLSpanElement> {
  content: React.ReactNode;
  placement?: 'top' | 'bottom';
  children?: React.ReactNode;
}
export declare function Tooltip(props: TooltipProps): JSX.Element;
```

## brand

### Logo

```ts
import * as React from 'react';

/**
 * The official DP6 lockups. Never recolour, stretch, outline or rebuild the mark.
 */
export interface LogoProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  /** primary = dp6 wordmark; the others carry the "part of the brandtech group" endorsement. */
  variant?: 'primary' | 'mono' | 'horizontal' | 'divider' | 'vertical';
  /** true picks the light (white) artwork for dark backgrounds. */
  onDark?: boolean;
  /** Rendered height in px. Minimum 60px on screen for the endorsed lockups. */
  height?: number;
  /** Path prefix to assets/logos, relative to the page. */
  assetBase?: string;
}
export declare function Logo(props: LogoProps): JSX.Element;
```

### Grafismo

```ts
import * as React from 'react';

/** The three ascending bars that remain DP6's independent brand graphic. */
export interface GrafismoProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'solid' | 'outline';
  /** Any brand colour token; amarelo and the neutrals are preferred. */
  color?: string;
  height?: number;
  gap?: number;
  /** Lower it (e.g. 0.08) to use the grafismo as a background watermark. */
  opacity?: number;
}
export declare function Grafismo(props: GrafismoProps): JSX.Element;
```


---

# KITS, TEMPLATES & SLIDES

These are HTML/JSX artifacts and are not reproduced here — open them in the project.

| Path | What it is |
| --- | --- |
| `ui_kits/website/` | Clickable institutional site — home, serviços, insights, contato |
| `ui_kits/report/` | Clickable client report/dashboard with chart primitives (`Charts.jsx`) |
| `templates/deck/PitchDeck.dc.html` | Reusable DP6 deck template (Design Component) |
| `slides/01-08*.html` | 8 sample 1280×720 slides in the guideline deck style |
| `guidelines/` | Foundation specimen cards (colour, type, spacing, brand) |
| `assets/logos/` | 10 official lockups, dark and light artwork |
| `assets/reference/` | Source guideline PDF and palette boards |
