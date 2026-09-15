---
name: Lumina Finance
colors:
  surface: '#fcf8fa'
  surface-dim: '#dcd9db'
  surface-bright: '#fcf8fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f5'
  surface-container: '#f0edef'
  surface-container-high: '#eae7e9'
  surface-container-highest: '#e4e2e4'
  on-surface: '#1b1b1d'
  on-surface-variant: '#45464d'
  inverse-surface: '#303032'
  inverse-on-surface: '#f3f0f2'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#505f76'
  on-secondary: '#ffffff'
  secondary-container: '#d0e1fb'
  on-secondary-container: '#54647a'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#191c1e'
  on-tertiary-container: '#818486'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#e0e3e5'
  tertiary-fixed-dim: '#c4c7c9'
  on-tertiary-fixed: '#191c1e'
  on-tertiary-fixed-variant: '#444749'
  background: '#fcf8fa'
  on-background: '#1b1b1d'
  surface-variant: '#e4e2e4'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  title-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: 0.01em
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: 0.01em
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.08em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding-desktop: 40px
  container-padding-mobile: 20px
  gutter: 24px
  stack-sm: 12px
  stack-md: 24px
  stack-lg: 48px
---

## Brand & Style

This design system is anchored in the concept of "Digital Clarity." It targets high-net-worth individuals and professionals who require a sense of calm and precision in their financial management. The aesthetic is a refined evolution of Glassmorphism, leaning into the sophisticated "frosted" look of modern premium OS environments.

The UI evokes an emotional response of absolute trust and competence. By utilizing high-transparency layers, subtle backdrop blurs, and an expansive use of white space, the interface feels lightweight yet structurally sound. It avoids the aggressive visuals of consumer fintech in favor of a quiet, high-end SaaS atmosphere that prioritizes data legibility and effortless navigation.

## Colors

The palette is intentionally restrained to maintain a "financial-grade" atmosphere. 

- **Primary (Deep Navy):** Used for critical text, primary icons, and structural emphasis. It provides the "anchor" for the lighter elements.
- **Secondary (Slate):** Used for supporting text and non-interactive UI elements to reduce visual noise.
- **Surface (Glass):** The core of the experience. Surfaces are primarily semi-transparent white with high-saturation backdrop blurs (20px - 40px).
- **Background:** A very light, neutral gray (`#F8FAFC`) serves as the canvas, ensuring that the glass cards "pop" through light refraction rather than heavy color contrast.
- **Accents:** Used sparingly for interactive states; never vibrant or neon, but always grounded in charcoal or deep navy tones.

## Typography

The design system utilizes **Inter** exclusively to achieve a systematic, Swiss-inspired clarity. 

- **Hierarchy:** Deep contrast between "Display" types and "Body" text is achieved through weight and letter spacing rather than color. 
- **Character:** Headlines use tight negative letter-spacing for a modern, "compacted" premium feel. Conversely, labels and secondary metadata use generous positive letter-spacing and uppercase styling to ensure they feel like architectural annotations rather than just "small text."
- **Readability:** For financial data, tabular lining (tnum) should be enabled to ensure numbers align perfectly in lists and cards.

## Layout & Spacing

This design system uses a **Fluid Grid** model with a max-width of 1440px for desktop environments. 

- **The 8px Rhythm:** All spacing (padding, margins, gaps) must be a multiple of 8px to maintain a mathematical, rigorous layout typical of high-end financial tools.
- **Safe Margins:** Large cards and glass surfaces require generous internal padding (typically 32px or 40px) to prevent data from feeling cramped against the frosted edges.
- **Floating Logic:** Content is organized into "floating stacks." Instead of traditional sidebars that hit the edge of the screen, navigation and secondary panels are rendered as independent glass floating cards with 24px margins from the screen edge.

## Elevation & Depth

Depth is the primary communicator of hierarchy in this design system. We use a three-tier elevation model:

1.  **Floor (0):** The base background (`#F8FAFC`). No interactivity.
2.  **Surface (Level 1):** Floating glass cards. These use a `backdrop-filter: blur(30px)` and a 1px border with `rgba(15, 23, 42, 0.08)`. A very soft, diffused shadow (0px 10px 30px rgba(0,0,0,0.03)) defines its separation from the floor.
3.  **Active (Level 2):** Modals, dropdowns, and hovered states. These increase the shadow intensity and slightly darken the border to suggest they are "closer" to the user.

**The "Glass Stroke":** Every card must have a top-down inner light highlight (a 1px white border at 50% opacity) and a bottom-up dark stroke (1px primary color at 8% opacity) to simulate the physical thickness of glass.

## Shapes

The shape language is consistently rounded to soften the professional tone. 

- **Cards & Containers:** Use `rounded-lg` (16px) as the default for all major data containers and floating panels.
- **Interactive Elements:** Buttons and input fields use `rounded-md` (8px) to provide a subtle distinction from the larger layout containers.
- **Selection States:** Circular or pill-shaped indicators are reserved exclusively for status badges or user avatars.

## Components

### Buttons
Primary buttons are solid Deep Navy (`#0F172A`) with white text, providing a high-contrast focal point. Secondary buttons are glass-based with a subtle border and no background fill until hovered.

### Floating Cards
The core layout unit. These should have a slight "inner glow" and the aforementioned backdrop blur. Content inside cards should be separated by thin, 1px horizontal dividers with 5% opacity.

### Input Fields
Inputs should be transparent with a 1px border that darkens on focus. Use a subtle `rgba(15, 23, 42, 0.02)` background fill to indicate the clickable area.

### AI Assistant Chat Bubbles
User messages are rendered in simple Slate text. AI responses are rendered on a slightly more "frosted" glass surface than the main background to highlight the "intelligence" generating the content.

### Data Lists
Financial rows should have ample vertical padding (16px). Use "Inter" with tabular figures for currency values. Hovering a row should apply a light 2% primary color overlay.

### Chips & Tags
Small, 12px font-size badges with a low-opacity version of the accent color. They should not have shadows, keeping them "flat" against the glass surfaces.