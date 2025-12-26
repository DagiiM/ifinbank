# iFin Bank - UI/UX Specification

> **Version:** 1.0  
> **Last Updated:** December 26, 2024

---

## Design Philosophy

The iFin Bank Verification System UI follows a modern, professional design language appropriate for financial applications:

- **Clean & Professional** - Minimal clutter, focus on data
- **Dark Theme** - Reduces eye strain for extended use
- **Data-Centric** - Quick access to verification details
- **Status-Driven** - Clear visual indicators for request states

---

## Color Palette

### Primary Colors
```css
--primary: #6366f1;        /* Indigo - Primary actions */
--primary-hover: #4f46e5;  /* Darker indigo for hover */
--secondary: #8b5cf6;      /* Purple - Secondary elements */
```

### Status Colors
```css
--success: #22c55e;        /* Green - Passed/Approved */
--warning: #f59e0b;        /* Amber - Review Required */
--danger: #ef4444;         /* Red - Failed/Rejected */
--info: #3b82f6;           /* Blue - Informational */
```

### Background Colors
```css
--bg-primary: #0f0f23;     /* Main background */
--bg-secondary: #1a1a2e;   /* Card background */
--bg-tertiary: #252542;    /* Elevated elements */
--bg-hover: #2d2d52;       /* Hover states */
```

### Text Colors
```css
--text-primary: #ffffff;   /* Primary text */
--text-secondary: #9ca3af; /* Secondary/muted text */
--text-tertiary: #6b7280;  /* Disabled/subtle text */
```

---

## Typography

### Font Family
```css
font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
```

### Font Sizes
```css
--text-xs: 0.75rem;   /* 12px - Labels, captions */
--text-sm: 0.875rem;  /* 14px - Body small */
--text-base: 1rem;    /* 16px - Body default */
--text-lg: 1.125rem;  /* 18px - Subheadings */
--text-xl: 1.25rem;   /* 20px - Card titles */
--text-2xl: 1.5rem;   /* 24px - Page titles */
--text-3xl: 1.875rem; /* 30px - Dashboard stats */
```

---

## Page Layouts

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                         HEADER                                   │
│  [Logo] iFin Bank Verify     [Search]      [User] ▼             │
├──────────────┬──────────────────────────────────────────────────┤
│              │                                                   │
│   SIDEBAR    │                 MAIN CONTENT                     │
│              │                                                   │
│  Dashboard   │  ┌─────────┬─────────┬─────────┬─────────┐      │
│  Requests    │  │ Pending │ Review  │ Today   │ Approved│      │
│  Documents   │  │   24    │   8     │   156   │  98.5%  │      │
│  Compliance  │  └─────────┴─────────┴─────────┴─────────┘      │
│  Reports     │                                                   │
│  Settings    │  ┌────────────────────────────────────────┐      │
│              │  │         Recent Requests                 │      │
│              │  │  [Table with verification requests]    │      │
│              │  └────────────────────────────────────────┘      │
│              │                                                   │
└──────────────┴──────────────────────────────────────────────────┘
```

### Verification Detail Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back to List    Verification #VR-2024-001    [Process] [→]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │   CUSTOMER INFO     │  │      VERIFICATION PROGRESS      │  │
│  │                     │  │                                  │  │
│  │  Name: John Doe     │  │  [▓▓▓▓▓▓▓▓▓▓] 95.5%            │  │
│  │  ID: 12345678       │  │                                  │  │
│  │  Account: ACC123    │  │  ✓ Identity Verified            │  │
│  │                     │  │  ✓ Documents Validated          │  │
│  └─────────────────────┘  │  ✓ Compliance Passed            │  │
│                           └─────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    DOCUMENTS                              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │  ID Card   │  │  Passport  │  │   Form     │         │  │
│  │  │  [Preview] │  │  [Preview] │  │  [Preview] │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 VERIFICATION RESULTS                      │  │
│  │  Field          │ Entered    │ Document   │ Match        │  │
│  │  ──────────────────────────────────────────────────────  │  │
│  │  Full Name      │ John Doe   │ JOHN DOE   │ ✓ 98%       │  │
│  │  ID Number      │ 12345678   │ 12345678   │ ✓ 100%      │  │
│  │  Date of Birth  │ 1990-01-15 │ 1990-01-15 │ ✓ 100%      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### Status Badge
```html
<span class="badge badge-success">Approved</span>
<span class="badge badge-warning">Review Required</span>
<span class="badge badge-danger">Rejected</span>
<span class="badge badge-info">Processing</span>
```

### Score Display
```html
<div class="score-ring">
  <svg class="score-ring__svg">
    <circle class="score-ring__bg" />
    <circle class="score-ring__progress" style="--progress: 95.5" />
  </svg>
  <span class="score-ring__value">95.5%</span>
</div>
```

### Verification Card
```html
<div class="card verification-card">
  <div class="card-header">
    <h3 class="card-title">VR-2024-001</h3>
    <span class="badge badge-success">Approved</span>
  </div>
  <div class="card-body">
    <p class="customer-name">John Doe</p>
    <p class="customer-id">ID: 12345678</p>
    <div class="score-badge">Score: 95.5%</div>
  </div>
  <div class="card-footer">
    <span class="timestamp">5 min ago</span>
    <a href="#" class="btn btn-primary btn-sm">View</a>
  </div>
</div>
```

### Data Comparison Row
```html
<tr class="comparison-row comparison-row--match">
  <td class="field-name">Full Name</td>
  <td class="entered-value">John Doe</td>
  <td class="document-value">JOHN DOE</td>
  <td class="match-score">
    <span class="match-indicator match-indicator--success">✓</span>
    98%
  </td>
</tr>
```

---

## Page Specifications

### 1. Dashboard (`/verification/dashboard/`)
- Summary statistics (cards with counts and percentages)
- Recent verification requests (table with quick actions)
- Charts showing verification trends (optional Phase 2)

### 2. Request List (`/verification/requests/`)
- Filterable/sortable table of all verification requests
- Bulk actions (assign, prioritize)
- Quick status filters (tabs or sidebar)

### 3. Request Detail (`/verification/requests/{id}/`)
- Full customer information display
- Document viewer with zoom/pan
- Side-by-side comparison view
- Verification results breakdown
- Action buttons (Approve/Reject/Request Info)

### 4. Document Viewer (`/documents/{id}/`)
- Full-page document display
- OCR text overlay toggle
- Field highlighting
- Zoom controls

### 5. Manual Review (`/verification/requests/{id}/review/`)
- Split-screen: Document on left, Data on right
- Field-by-field approval
- Discrepancy resolution form
- Notes and comments

---

## Responsive Breakpoints

```css
/* Mobile */
@media (max-width: 639px) { ... }

/* Tablet */
@media (min-width: 640px) and (max-width: 1023px) { ... }

/* Desktop */
@media (min-width: 1024px) { ... }

/* Wide Desktop */
@media (min-width: 1280px) { ... }
```

---

## Animation Guidelines

### Transitions
```css
--transition-fast: 150ms ease;
--transition-base: 200ms ease;
--transition-slow: 300ms ease;
```

### Loading States
- Skeleton loaders for content loading
- Spinner for actions in progress
- Progress bar for multi-step processes

### Micro-interactions
- Button hover/active states
- Card hover elevation
- Status badge pulse for new items
- Smooth page transitions
