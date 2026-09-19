# FIN --- Typography & Visual Design Specification

## Financial Policy Intelligence (FIN)

**Purpose:** This document is the locked typography and visual-language
specification for the FIN frontend.

The five approved reference screens are the visual source of truth:

1.  Dashboard
2.  Discover Government Schemes
3.  Scheme Details
4.  Scheme Benefits
5.  My Documents

The implementation must reproduce the approved visual language rather
than redesign it.

------------------------------------------------------------------------

# 1. Core Design Principle

FIN should feel like a:

-   trustworthy Indian government-financial service
-   premium financial intelligence product
-   calm and information-rich application
-   human-designed interface

It must **not** look like a generic AI-generated SaaS dashboard.

### Non-negotiable rule

> Reference design \> developer preference \> framework defaults.

If an implementation choice conflicts with the approved reference
screenshots, follow the reference screenshots.

Do not introduce a new visual style without explicit approval.

------------------------------------------------------------------------

# 2. Typography Philosophy

FIN uses a deliberate two-font system:

### Heading / Editorial Font

**Playfair Display**

Used for:

-   page titles
-   major headings
-   scheme names
-   large financial figures
-   editorial statements
-   important hero headings
-   FIN wordmark

### UI / Body Font

**Inter**

Used for:

-   navigation
-   search
-   buttons
-   labels
-   descriptions
-   filters
-   tables
-   metadata
-   status badges
-   supporting text
-   form controls

The contrast between Playfair Display and Inter creates the identity of
FIN:

**Playfair Display = trust, editorial, government/public-service
character**

**Inter = clarity, usability, fintech/product character**

------------------------------------------------------------------------

# 3. Font Loading

Use web fonts rather than relying on local system availability.

Recommended:

``` css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap');
```

Prefer loading only the weights actually used.

Recommended weights:

### Playfair Display

-   500
-   600
-   700

### Inter

-   400
-   500
-   600
-   700

Do not add unnecessary font families.

------------------------------------------------------------------------

# 4. Global Font Tokens

``` css
:root {
  --font-heading: "Playfair Display", Georgia, serif;
  --font-body: "Inter", Arial, sans-serif;
}
```

Global rules:

``` css
body {
  font-family: var(--font-body);
}

h1,
h2,
h3,
h4,
.display,
.editorial-heading {
  font-family: var(--font-heading);
}
```

Do not use:

-   Poppins
-   Roboto
-   Montserrat
-   Manrope
-   Geist
-   Lato
-   system-ui

as replacements for the approved fonts.

------------------------------------------------------------------------

# 5. Type Scale

  -----------------------------------------------------------------------------------
  Token                 Size        Weight   Line Height Font       Typical Usage
  ------------ ------------- ------------- ------------- ---------- -----------------
  Display               48px           600          1.10 Playfair   Hero / major
                                                                    financial figure

  H1                    38px           600          1.15 Playfair   Main page title

  H2                    28px           600          1.20 Playfair   Major section

  H3                    22px           600          1.25 Playfair   Scheme/section
                                                                    heading

  Scheme Title          24px           600          1.25 Playfair   Scheme cards

  Large Number          32px           600          1.15 Playfair   Dashboard metrics

  Financial             48px           600          1.10 Playfair   Benefits page
  Hero                                                              amount

  Body Large            17px           400          1.55 Inter      Page subtitle

  Body                  15px           400          1.50 Inter      General content

  Body Medium           15px           500          1.50 Inter      Emphasized body

  Small                 13px           400          1.45 Inter      Metadata

  Caption               12px           500          1.40 Inter      Table
                                                                    labels/captions

  Button                14px           600          1.00 Inter      Buttons

  Navigation            15px           500          1.40 Inter      Sidebar

  Navigation            15px           600          1.40 Inter      Active sidebar
  Active                                                            item
  -----------------------------------------------------------------------------------

------------------------------------------------------------------------

# 6. Letter Spacing

Keep letter spacing restrained.

### Playfair Display

``` css
letter-spacing: -0.015em;
```

for large headings where appropriate.

### Inter body

``` css
letter-spacing: 0;
```

### Small uppercase labels

Only when uppercase is intentionally used:

``` css
letter-spacing: 0.02em;
```

Do not use wide tracking on normal headings.

Do not turn all UI labels into uppercase.

------------------------------------------------------------------------

# 7. Dashboard Typography

## 7.1 Date

Example:

`Thu, 18 Sep 2026`

``` text
Font: Inter
Size: 14px
Weight: 400
Line-height: 1.4
Color: #667085
```

------------------------------------------------------------------------

## 7.2 Main Greeting

Example:

`Namaste, Hemang 🙏`

``` text
Font: Playfair Display
Size: 48px
Weight: 600
Line-height: 1.10
Color: #10243A
```

Do not exceed 52px on desktop.

Do not make this a generic:

`Good evening, Hemang`

The approved design uses:

`Namaste, Hemang 🙏`

------------------------------------------------------------------------

## 7.3 Hinglish Supporting Message

Example:

`Sarkar ki yojanaon se, aapke sapno ko nayi pehchaan.`

``` text
Font: Inter
Size: 20px
Weight: 600
Line-height: 1.45
Color: #005B50
```

This is an important brand-language element.

------------------------------------------------------------------------

## 7.4 English Supporting Text

Example:

`Let's find the right government schemes for your goals.`

``` text
Font: Inter
Size: 17px
Weight: 400
Line-height: 1.55
Color: #344054
```

------------------------------------------------------------------------

# 8. Dashboard Metric Cards

Examples:

-   12
-   ₹2,45,000
-   7 / 9
-   3

### Metric number

``` text
Font: Playfair Display
Size: 32px
Weight: 600
Line-height: 1.15
Color: #10243A
```

### Metric title

``` text
Font: Inter
Size: 15px
Weight: 600
Line-height: 1.45
Color: #10243A
```

### Metric description

``` text
Font: Inter
Size: 13px
Weight: 400
Line-height: 1.45
Color: #667085
```

### Warning metric description

Example:

`2 documents missing`

``` text
Font: Inter
Size: 13px
Weight: 500
Color: #C56A00
```

------------------------------------------------------------------------

# 9. Dashboard Section Heading

Example:

`Top Opportunities for You`

``` text
Font: Playfair Display
Size: 28px
Weight: 600
Line-height: 1.20
Color: #10243A
```

Supporting line:

`Personalized schemes based on your profile, sorted by relevance.`

``` text
Font: Inter
Size: 15px
Weight: 400
Line-height: 1.5
Color: #667085
```

------------------------------------------------------------------------

# 10. Scheme Cards

## Scheme Name

Example:

`PMEGP`

``` text
Font: Playfair Display
Size: 24px
Weight: 600
Line-height: 1.25
Color: #10243A
```

## Scheme Description

``` text
Font: Inter
Size: 15px
Weight: 400
Line-height: 1.50
Color: #344054
```

## Category Tags

Examples:

-   Business Support
-   Self Employment
-   Agriculture

``` text
Font: Inter
Size: 13px
Weight: 500
Line-height: 1.4
```

## Match Badge

Example:

`96% Match`

``` text
Font: Inter
Size: 14px
Weight: 600
Line-height: 1.4
```

## Benefit Amount

Example:

`₹1,25,000`

``` text
Font: Playfair Display
Size: 22px
Weight: 600
Line-height: 1.2
Color: #10243A
```

## Benefit Label

`Estimated Benefit`

``` text
Font: Inter
Size: 13px
Weight: 400
Line-height: 1.4
Color: #667085
```

## Eligibility Status

Example:

`6/6 conditions match`

``` text
Font: Inter
Size: 14px
Weight: 500
Line-height: 1.4
```

------------------------------------------------------------------------

# 11. Discover Schemes Page

## Page Title

`Discover Government Schemes`

``` text
Font: Playfair Display
Size: 38px
Weight: 600
Line-height: 1.15
Color: #10243A
```

## Page Subtitle

``` text
Font: Inter
Size: 17px
Weight: 400
Line-height: 1.55
Color: #344054
```

## Category Tabs

Examples:

`All`, `Business`, `Agriculture`, `Education`

``` text
Font: Inter
Size: 14px
Weight: 500
Line-height: 1.4
```

Active category:

``` text
Font weight: 600
```

## Scheme Count

Example:

`54 schemes found`

``` text
Font: Inter
Size: 15px
Weight: 500
Color: #344054
```

## Sort Control

Example:

`Most Relevant`

``` text
Font: Inter
Size: 14px
Weight: 600
```

------------------------------------------------------------------------

# 12. Discover Scheme List Typography

### Scheme title

``` text
24px
Playfair Display
600
```

### Description

``` text
15px
Inter
400
1.5 line-height
```

### Tags

``` text
13px
Inter
500
```

### Match percentage

``` text
14px
Inter
600
```

### Financial value

``` text
22px
Playfair Display
600
```

### Condition text

``` text
14px
Inter
500
```

------------------------------------------------------------------------

# 13. Filter Panel Typography

## Filter title

`Filters`

``` text
Font: Inter
Size: 18px
Weight: 600
```

## Filter group heading

Examples:

-   Category
-   Eligibility
-   Scheme Type

``` text
Font: Inter
Size: 14px
Weight: 600
Line-height: 1.4
```

## Checkbox label

``` text
Font: Inter
Size: 14px
Weight: 400
Line-height: 1.45
```

## Select control

``` text
Font: Inter
Size: 14px
Weight: 400
```

------------------------------------------------------------------------

# 14. Scheme Details Page

## Scheme Title

`PMEGP`

``` text
Font: Playfair Display
Size: 40px
Weight: 600
Line-height: 1.15
Color: #10243A
```

## Scheme Subtitle

`Prime Minister's Employment Generation Programme`

``` text
Font: Inter
Size: 20px
Weight: 400
Line-height: 1.45
Color: #344054
```

## Scheme Description

``` text
Font: Inter
Size: 16px
Weight: 400
Line-height: 1.55
Color: #475467
```

------------------------------------------------------------------------

# 15. Scheme Tabs

Examples:

-   Overview
-   Eligibility
-   Benefits
-   Documents
-   How to Apply
-   Source & Rules

``` text
Font: Inter
Size: 14px
Weight: 500
Line-height: 1.4
```

Active tab:

``` text
Weight: 600
```

Do not enlarge the active tab.

The active state should be communicated through:

-   underline
-   color
-   weight

not by increasing font size.

------------------------------------------------------------------------

# 16. Scheme Hero Typography

Example:

`Turn Your Entrepreneurial Dreams into Reality.`

``` text
Font: Playfair Display
Size: 34px
Weight: 600
Line-height: 1.12
Color: #10243A
```

The highlighted word can use the approved green:

``` text
Color: #087443
```

Do not use gradient text.

------------------------------------------------------------------------

# 17. Key Benefits Typography

## Section title

`Key Benefits`

``` text
Font: Playfair Display
Size: 24px
Weight: 600
Line-height: 1.2
```

## Benefit card title

``` text
Font: Inter
Size: 16px
Weight: 600
Line-height: 1.4
```

## Benefit value

Example:

`Up to ₹1,25,000`

``` text
Font: Playfair Display
Size: 20px
Weight: 600
Line-height: 1.25
```

## Benefit description

``` text
Font: Inter
Size: 14px
Weight: 400
Line-height: 1.5
```

------------------------------------------------------------------------

# 18. Scheme Benefits Page

## Page Title

`Scheme Benefits`

``` text
Font: Playfair Display
Size: 32px
Weight: 600
Line-height: 1.2
```

## Subtitle

``` text
Font: Inter
Size: 16px
Weight: 400
Line-height: 1.55
```

------------------------------------------------------------------------

# 19. Financial Hero Amount

Example:

`₹1,25,000`

This is the most prominent number in the Benefits screen.

``` text
Font: Playfair Display
Size: 48px
Weight: 600
Line-height: 1.10
Color: #10243A
```

Do not use 64px, 72px or oversized marketing typography.

The number should feel like a financial report value, not an
advertisement.

## Benefit type

`(Margin Money Subsidy)`

``` text
Font: Inter
Size: 18px
Weight: 600
Line-height: 1.4
```

## Supporting explanation

``` text
Font: Inter
Size: 16px
Weight: 400
Line-height: 1.55
```

------------------------------------------------------------------------

# 20. Benefit Details Table

## Table title

`Benefit Details`

``` text
Font: Inter
Size: 20px
Weight: 600
Line-height: 1.4
```

The table intentionally uses Inter rather than Playfair.

## Table header

``` text
Font: Inter
Size: 14px
Weight: 600
Line-height: 1.4
```

## Table body

``` text
Font: Inter
Size: 14px
Weight: 400
Line-height: 1.5
```

## Important table values

``` text
Font: Inter
Size: 14px
Weight: 600
```

------------------------------------------------------------------------

# 21. Benefit Supporting Cards

Examples:

-   Credit Support
-   Margin Money Subsidy
-   Handholding Support

### Title

``` text
Font: Inter
Size: 16px
Weight: 600
```

### Description

``` text
Font: Inter
Size: 15px
Weight: 400
Line-height: 1.5
```

------------------------------------------------------------------------

# 22. Important Note

Example:

`Benefit amounts are estimates and subject to change as per latest government guidelines.`

``` text
Font: Inter
Size: 14px
Weight: 400
Line-height: 1.5
```

Button:

`View Official Guidelines`

``` text
Font: Inter
Size: 14px
Weight: 600
```

------------------------------------------------------------------------

# 23. My Documents Page

## Page Title

`My Documents`

``` text
Font: Playfair Display
Size: 38px
Weight: 600
Line-height: 1.15
```

## Subtitle

``` text
Font: Inter
Size: 17px
Weight: 400
Line-height: 1.55
```

## Document Status Tabs

Examples:

-   All Documents
-   Verified
-   Pending
-   Action Required

``` text
Font: Inter
Size: 14px
Weight: 600
```

------------------------------------------------------------------------

# 24. Document Table

## Column Header

Examples:

-   Document
-   Purpose
-   Status
-   Uploaded On
-   Actions

``` text
Font: Inter
Size: 12px
Weight: 600
Line-height: 1.4
Color: #344054
```

## Document Name

Example:

`Aadhaar Card`

``` text
Font: Inter
Size: 15px
Weight: 600
Line-height: 1.4
```

## Document Description

Example:

`Identity Verification`

``` text
Font: Inter
Size: 13px
Weight: 400
Line-height: 1.4
Color: #667085
```

## Status

Examples:

-   Verified
-   Under Review
-   Action Required

``` text
Font: Inter
Size: 13px
Weight: 600
Line-height: 1.4
```

## Date

``` text
Font: Inter
Size: 13px
Weight: 400
Color: #667085
```

## View / Upload action

``` text
Font: Inter
Size: 13px
Weight: 600
```

------------------------------------------------------------------------

# 25. Sidebar Typography

## FIN Wordmark

`FIN`

``` text
Font: Playfair Display
Size: 42px
Weight: 600
Line-height: 1
Color: #10243A
```

## Brand subtitle

`Financial Policy Intelligence`

``` text
Font: Inter
Size: 15px
Weight: 400
Line-height: 1.35
```

## Navigation

``` text
Font: Inter
Size: 15px
Weight: 500
Line-height: 1.4
```

## Active navigation

``` text
Font: Inter
Size: 15px
Weight: 600
```

Do not use font-size changes for active navigation.

------------------------------------------------------------------------

# 26. Header Typography

## Search placeholder

``` text
Font: Inter
Size: 14px
Weight: 400
Color: #667085
```

## User name

``` text
Font: Inter
Size: 14px
Weight: 600
Color: #10243A
```

## User type

`Individual Applicant`

``` text
Font: Inter
Size: 12px
Weight: 400
Color: #667085
```

------------------------------------------------------------------------

# 27. Government / Editorial Quotes

Examples:

`Sabka Saath, Sabka Vikas, Sabka Vishwas, Sabka Prayas`

and:

`Empowered citizens build a stronger India.`

Use:

``` text
Font: Playfair Display
Size: 18–22px
Weight: 500
Line-height: 1.45
```

These quotes should feel editorial and calm.

Do not make them bold.

Do not use all caps.

------------------------------------------------------------------------

# 28. Color Tokens

Use centralized CSS variables.

``` css
:root {
  --color-background: #F8F7F3;
  --color-surface: #FFFFFF;
  --color-surface-soft: #F3F6F3;

  --color-text: #10243A;
  --color-text-secondary: #344054;
  --color-text-muted: #667085;

  --color-primary: #005B50;
  --color-primary-dark: #00483F;

  --color-green: #087443;
  --color-green-soft: #E8F5EC;

  --color-blue: #1264D6;
  --color-blue-soft: #EDF5FF;

  --color-saffron: #E98A00;
  --color-saffron-soft: #FFF4DE;

  --color-warning: #C56A00;
  --color-warning-soft: #FFF3DD;

  --color-error: #D92D20;
  --color-error-soft: #FEECEC;

  --color-border: #E4E7EC;
}
```

These values are the initial implementation tokens. Fine adjustments are
allowed only to visually match the approved reference screens.

Do not introduce arbitrary colors.

------------------------------------------------------------------------

# 29. Border Radius

FIN should feel refined, not overly rounded.

Recommended:

``` css
--radius-sm: 8px;
--radius-md: 10px;
--radius-lg: 14px;
--radius-xl: 18px;
```

Use:

-   buttons: 8--10px
-   inputs: 8--10px
-   cards: 12--14px
-   large feature panels: 14--18px

Avoid excessive pill-shaped containers.

Pills should be reserved for:

-   categories
-   match badges
-   statuses

------------------------------------------------------------------------

# 30. Shadows

Use subtle shadows only.

Preferred:

``` css
--shadow-sm: 0 1px 3px rgba(16, 36, 58, 0.05);
--shadow-md: 0 4px 14px rgba(16, 36, 58, 0.06);
```

Do not use:

-   large glowing shadows
-   neon shadows
-   colored shadows
-   excessive elevation

Many cards can remain border-only.

------------------------------------------------------------------------

# 31. Spacing Scale

Use an 8-point-based spacing system:

``` css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
```

Prefer these tokens instead of random values.

------------------------------------------------------------------------

# 32. Layout Dimensions

The desktop reference is the primary target.

### Sidebar

Approximate:

``` text
Width: 220–230px
```

Keep it visually stable across pages.

### Header

Approximate:

``` text
Height: 76–82px
```

### Main content

Use a comfortable content area with consistent horizontal padding.

Approximate:

``` text
Desktop horizontal padding: 32–40px
```

Do not make the content excessively wide.

------------------------------------------------------------------------

# 33. Button Typography

## Primary button

Example:

`Explore Schemes →`

``` text
Font: Inter
Size: 14px
Weight: 600
Line-height: 1
```

## Secondary button

Same typography.

The difference should come from:

-   background
-   border
-   color

not typography.

## Large CTA

Example:

`Apply Now →`

``` text
Font: Inter
Size: 15px
Weight: 600
```

------------------------------------------------------------------------

# 34. Responsive Typography

Desktop is the reference.

Do not aggressively scale typography.

Suggested minimum responsive adjustments:

### Desktop

``` text
H1: 38px
H2: 28px
H3: 22px
Body: 15px
```

### Tablet

``` text
H1: 34px
H2: 26px
H3: 21px
Body: 15px
```

### Mobile

``` text
H1: 30px
H2: 24px
H3: 20px
Body: 14–15px
```

Maintain hierarchy.

Never make mobile text tiny just to fit content.

------------------------------------------------------------------------

# 35. Typography Anti-Patterns

DO NOT:

-   use different fonts on different pages
-   randomly increase headings
-   use 60--80px marketing headings
-   use bold body paragraphs
-   use uppercase everywhere
-   use excessive letter spacing
-   use gradient text
-   use decorative fonts
-   use emoji as icons
-   use multiple unrelated font families
-   use arbitrary font sizes
-   use inconsistent line heights

------------------------------------------------------------------------

# 36. Anti-AI Visual Rules

The following are explicitly prohibited unless added later by the design
owner:

-   purple AI gradients
-   glowing AI effects
-   sparkle icons
-   "AI Powered" badges
-   glassmorphism
-   floating blobs
-   excessive 3D illustrations
-   random charts
-   excessive animations
-   giant rounded cards
-   excessive pill UI
-   generic SaaS dashboard templates
-   dark mode redesign
-   neon accents
-   excessive shadows

FIN should remain:

**calm + trustworthy + Indian + financial + editorial + functional**

------------------------------------------------------------------------

# 37. Animation Rules

Animations should be subtle.

Allowed:

-   150--200ms hover transitions
-   button color transition
-   subtle card border transition
-   sidebar active transition
-   dropdown transition

Avoid:

-   large entrance animations
-   bouncing cards
-   parallax
-   floating elements
-   continuous animations
-   flashy page transitions

Animation must never change the layout or typography.

------------------------------------------------------------------------

# 38. Visual Consistency Across Five Pages

All five pages must share:

-   identical sidebar
-   identical header
-   identical search bar
-   identical profile area
-   identical navigation typography
-   identical color tokens
-   identical button language
-   identical card radius
-   identical border language
-   identical status styles
-   identical icon family

Only the page-specific content/layout changes.

------------------------------------------------------------------------

# 39. Reference-Screen Implementation Order

Implement in this order:

### Phase 1 --- Design Foundation

1.  Fonts
2.  Typography tokens
3.  Color tokens
4.  Spacing tokens
5.  Radius tokens
6.  Shadow tokens

### Phase 2 --- Shared Layout

7.  Sidebar
8.  Header
9.  Search
10. User menu
11. Buttons
12. Cards
13. Status badges

### Phase 3 --- Pages

14. Dashboard
15. Discover Schemes
16. Scheme Details
17. Scheme Benefits
18. My Documents

### Phase 4 --- QA

19. Compare every page against reference
20. Fix typography
21. Fix spacing
22. Fix alignment
23. Fix colors
24. Fix component consistency
25. Test responsive behavior

------------------------------------------------------------------------

# 40. Visual QA Checklist

Before considering a page complete, verify:

### Typography

-   [ ] Correct font family
-   [ ] Correct font size
-   [ ] Correct weight
-   [ ] Correct line height
-   [ ] Correct hierarchy
-   [ ] No random font substitutions

### Color

-   [ ] Background matches
-   [ ] Heading color matches
-   [ ] Primary green matches
-   [ ] Blue accent is controlled
-   [ ] Saffron is restrained
-   [ ] Status colors are consistent

### Layout

-   [ ] Sidebar width matches
-   [ ] Header height matches
-   [ ] Main content alignment matches
-   [ ] Card sizes match
-   [ ] Section spacing matches
-   [ ] Buttons match
-   [ ] Icons match

### Product feel

-   [ ] Government-service trust
-   [ ] Financial-product clarity
-   [ ] Indian visual identity
-   [ ] No generic AI dashboard appearance

------------------------------------------------------------------------

# 41. Final Non-Negotiable Instruction for Antigravity

``` text
DO NOT REDESIGN THE FIN INTERFACE.

The five approved screenshots are the final visual reference.

Do not change:
- typography
- font family
- font sizes
- font weights
- line heights
- colors
- spacing
- card radius
- shadows
- icon style
- layout proportions
- visual hierarchy

If a component can be implemented in multiple ways,
choose the implementation that most closely reproduces
the approved screenshots.

Do not apply your own design preferences.

Do not "modernize" the UI.

Do not simplify the UI by removing visual details.

Do not add visual details that are not present.

Implement the design faithfully.
```

------------------------------------------------------------------------

# 42. One-Line Design Identity

**FIN = Playfair Display editorial authority + Inter product clarity +
restrained government green + Indian visual identity + financial
information density.**

This is the core visual identity and must remain consistent across the
entire application.
