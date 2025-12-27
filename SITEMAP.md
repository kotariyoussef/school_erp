# 🗺️ School ERP - Site Map & Wireframe Guide

## 📍 Site Structure

```
School ERP Application
│
├── 🏠 Dashboard (/)
│   ├── KPI Cards (Revenue, Students, Unpaid)
│   ├── Stats Row (Today Revenue, Teachers, Courses, Amount Due)
│   ├── Quick Actions (Payment, Sessions, Students, Schedule)
│   └── Red List (Unpaid Students Table)
│
├── 👥 Élèves (Students)
│   ├── 📋 Liste (/students/)
│   │   ├── Searchable Table
│   │   ├── Status Badges
│   │   └── Quick Actions
│   │
│   └── 👤 Détail (/students/<id>/)
│       ├── Profile Card
│       ├── Enrollments Table
│       ├── Payment History (Paginated)
│       └── Quick Payment Button
│
├── 📚 Cours (/courses/)
│   ├── Card Grid Layout
│   ├── Teacher, Room, Price Info
│   ├── Enrollment Count
│   └── Admin Links
│
├── 👨‍🏫 Professeurs (/teachers/)
│   ├── Teacher Card Grid
│   ├── Hourly Rate Display
│   ├── Course & Session Counts
│   └── Admin Links
│
├── 🚪 Salles (/rooms/)
│   ├── Room Card Grid
│   ├── Capacity Info
│   ├── Usage Statistics
│   └── Admin Links
│
├── 💰 Caisse (Finance)
│   └── Paiement (/cashier/payment/create/)
│       ├── Student Search (Select2 AJAX)
│       ├── Student Info Display
│       ├── Amount Auto-fill
│       ├── Payment Method Selector
│       └── PDF Receipt Download
│
├── 📅 Sessions
│   ├── Aujourd'hui (/sessions/today/)
│   │   ├── Today's Sessions Table
│   │   ├── Room & Time Info
│   │   └── Attendance Buttons
│   │
│   └── Présence (/sessions/<id>/attendance/)
│       ├── Session Details Card
│       ├── Student Checklist
│       ├── Default Present Checkboxes
│       └── Submit/Cancel Buttons
│
├── 📊 Planification (/schedule/)
│   ├── Week Navigation
│   ├── Room × Day Grid
│   ├── Session Display
│   ├── Time Indicators
│   └── Statistics Cards
│
└── 💵 Paie (/payroll/teacher/)
    ├── Teacher Selection
    ├── Date Range Picker
    ├── KPI Cards (Hours, Rate, Total)
    └── Sessions Detail Table

└── ⚙️ Admin (/admin/)
    └── Django Admin Interface
```

---

## 🎨 Layout Overview

### Master Layout (base.html)

```
┌─────────────────────────────────────────────┐
│  [LOGO] ← Search Bar → [Time Display]       │  Navbar
├──────────┬──────────────────────────────────┤
│          │                                  │
│          │                                  │
│ Sidebar  │       Main Content Area          │
│          │                                  │
│ 260px    │    (Flex Container)              │
│          │                                  │
├──────────┴──────────────────────────────────┤
│  © 2024 School ERP System                   │  Footer
└─────────────────────────────────────────────┘
```

### Sidebar Navigation

```
┌──────────────────┐
│  🎓 SCHOOL ERP   │
├──────────────────┤
│ 📊 Dashboard     │
│ 👥 Élèves       │
│ 📚 Cours        │
│ 👨‍🏫 Professeurs │
│ 💰 Caisse       │
│ 📅 Sessions     │
│ 📊 Planification │
│ 💵 Paie         │
│ ⚙️ Admin        │
└──────────────────┘
```

---

## 📄 Page Layouts

### Dashboard (/)

```
┌─ DASHBOARD ────────────────────────────────┐
│  [KPI Card 1]  [KPI Card 2]  [KPI Card 3] │
│  Revenue       Students       Unpaid       │
├────────────────────────────────────────────┤
│  [Stat Card] [Stat Card] [Stat Card] [Stat]│
│  Today Rev   Teachers   Courses    Amount  │
├────────────────────────────────────────────┤
│ ⚡ QUICK ACTIONS                          │
│ [Payment] [Sessions] [Students] [Schedule] │
├────────────────────────────────────────────┤
│ 🔴 RED LIST - UNPAID STUDENTS              │
│ ┌────────────────────────────────────────┐ │
│ │ Name  │ Parent │ Due │ Paid │ Actions│ │
│ │─────────────────────────────────────── │ │
│ │ ...                                    │ │
│ └────────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

### Payment Form (/cashier/payment/create/)

```
┌─ ENCAISSEMENT DE PAIEMENT ─────────────────┐
│                                            │
│  🔍 Rechercher Élève                       │
│  ┌─────────────────────────────────────┐  │
│  │ [Select2 AJAX Dropdown]             │  │
│  └─────────────────────────────────────┘  │
│                                            │
│  Informations de l'Élève:                  │
│  ┌─────────────────────────────────────┐  │
│  │ Nom: [Auto-filled]                  │  │
│  │ Parent: [Auto-filled]               │  │
│  │ Groupes: [Icons with course names] │  │
│  └─────────────────────────────────────┘  │
│                                            │
│  Montant Dû:                               │
│  ┌─────────────────────────────────────┐  │
│  │ [Auto-filled from calculation]      │  │
│  └─────────────────────────────────────┘  │
│                                            │
│  Méthode de Paiement:                      │
│  [ Espèces ] [ Virement ] [ Chèque ]       │
│                                            │
│  [Confirm & Download Receipt] [Cancel]    │
└────────────────────────────────────────────┘
```

### Student Detail (/students/<id>/)

```
┌─ PROFILE ÉLÈVE ────────────────────────────┐
│                                            │
│  ┌──────────────┐  ┌─────────────────────┐│
│  │ PROFIL       │  │ GROUPES INSCRITS    ││
│  │ Nom          │  │ ┌─────────────────┐││
│  │ Date Naiss   │  │ │ Groupe │ Prof   │││
│  │ Contact      │  │ │─────────────────│││
│  │ Adresse      │  │ │ ...             │││
│  │              │  │ └─────────────────┘││
│  │ [Payer]      │  │                     ││
│  │              │  │ HISTORIQUE PAIEMENTS││
│  └──────────────┘  │ ┌─────────────────┐││
│                    │ │ Reçu │ Date │... │││
│                    │ │─────────────────│││
│                    │ │ ...             │││
│                    │ └─────────────────┘││
│                    │ [Prev] [Next]       ││
│                    └─────────────────────┘│
└─────────────────────────────────────────────┘
```

### Schedule Grid (/schedule/)

```
┌─ PLANIFICATION HEBDOMADAIRE ───────────────┐
│  [◀ Prev Week]  Jan 8-14, 2024  [Next ►]  │
├───┬─────┬─────┬─────┬─────┬─────┬─────────┤
│   │ Lun │ Mar │ Mer │ Jeu │ Ven │ Sam     │
│   │ 8/1 │ 9/1 │10/1 │11/1 │12/1 │13/1    │
├───┼─────┼─────┼─────┼─────┼─────┼────────┤
│ 1 │ --  │09:30│ --  │ --  │14:00│ --     │
│   │     │Gr 1 │     │     │Gr 2 │        │
│   │     │Prof │     │     │Prof │        │
├───┼─────┼─────┼─────┼─────┼─────┼────────┤
│ 2 │14:00│ --  │10:00│ --  │ --  │10:30  │
│   │Gr 3 │     │Gr 4 │     │     │Gr 1   │
├───┼─────┼─────┼─────┼─────┼─────┼────────┤
│ 3 │ --  │ --  │ --  │ --  │ --  │ --    │
└───┴─────┴─────┴─────┴─────┴─────┴────────┘
```

### Attendance Checklist (/sessions/<id>/attendance/)

```
┌─ PRÉSENCE - GROUP: Maths Avancé ──────────┐
│  📅 Date: 2024-01-15                      │
│  ⏰ Horaire: 10:00 - 12:00                │
│  👨‍🏫 Prof: Ahmed El-Mansouri               │
├────────────────────────────────────────────┤
│  LISTE PRÉSENCE                            │
│  ┌────────────────────────────────────┐   │
│  │ ☑ Ahmed Ben Ali                    │   │
│  │ ☑ Fatima Al-Zahara                │   │
│  │ ☑ Mohammed Hassan                 │   │
│  │ ☐ Amina Boudrissa  (Absent)       │   │
│  │ ☑ Khalid Al-Rashid                │   │
│  └────────────────────────────────────┘   │
│                                            │
│  [Enregistrer] [Annuler]                   │
└────────────────────────────────────────────┘
```

### Payroll Calculator (/payroll/teacher/)

```
┌─ CALCUL DE PAIE ────────────────────────────┐
│                                             │
│ PARAMÈTRES          RÉSULTATS               │
│                                             │
│ 👨‍🏫 Professeur:      ┌─────────────────────┐
│ [Select dropdown]    │ HEURES TRAVAILLÉES  │
│                      │ 120.5 h             │
│ 📅 De:               ├─────────────────────┤
│ [Date picker]        │ TARIF HORAIRE       │
│                      │ 150 DH/h            │
│ 📅 À:                ├─────────────────────┤
│ [Date picker]        │ TOTAL À PAYER       │
│                      │ 18,075 DH ✓         │
│ [Calculer]           └─────────────────────┘
│                      
│                      SESSIONS DÉTAILLÉES
│                      ┌─────────────────────┐
│                      │ Date│Groupe│Heures  │
│                      │──────────────────── │
│                      │2024-01-01│Math│2.0 │
│                      │2024-01-02│Sci │1.5 │
│                      └─────────────────────┘
└─────────────────────────────────────────────┘
```

---

## 🎨 Color Scheme

```
Primary Colors:
├── Gradient: #667eea → #764ba2 (Sidebar)
├── Primary: #0d6efd (Buttons, Links)
└── Light: #f8f9fa (Background)

Status Colors:
├── Success: #198754 (✓ Paid, Done)
├── Danger: #dc3545 (✗ Unpaid, Error)
├── Warning: #ffc107 (⚠ Partial, Pending)
├── Info: #0d6efd (ℹ Due, Info)
└── Secondary: #6c757d (Neutral)
```

---

## 📱 Responsive Breakpoints

### Mobile (< 768px)
```
Sidebar: Full width, collapsible
Layout: Single column
Tables: Horizontal scroll
Cards: Stack vertically
```

### Tablet (768px - 992px)
```
Sidebar: Responsive width
Layout: 2 columns when possible
Tables: Condensed
Cards: Grid 2 columns
```

### Desktop (≥ 992px)
```
Sidebar: Fixed 260px
Layout: Full multi-column
Tables: Full width
Cards: Grid 3-4 columns
```

---

## 🔄 User Flow Diagrams

### Payment Flow
```
Student Selected
      ↓
Search Results ← [AJAX Request: /cashier/student-search/]
      ↓
Student Clicked
      ↓
Student Info Loaded ← [AJAX Request: /cashier/student-detail/]
      ↓
Amount Due Auto-filled
      ↓
User Enters Payment Details
      ↓
Confirm Payment
      ↓
[POST to /cashier/payment/create/]
      ↓
Payment Saved to DB
      ↓
PDF Generated ← [generate_receipt_pdf()]
      ↓
PDF Downloaded
      ↓
Success Message
```

### Attendance Flow
```
Dashboard (/)
      ↓
Click "Sessions d'aujourd'hui"
      ↓
Redirects to /sessions/today/
      ↓
Display Today's Sessions Table
      ↓
Click "Présence" Button
      ↓
Redirects to /sessions/<id>/attendance/
      ↓
Display Student Checklist
      ↓
User Unchecks Absent Students
      ↓
Click "Enregistrer"
      ↓
[POST to /sessions/<id>/attendance/]
      ↓
Attendance Records Created
      ↓
Session Status: DONE
      ↓
Success Confirmation Page
```

### Payroll Flow
```
Navigate to /payroll/teacher/
      ↓
Select Teacher from Dropdown
      ↓
Enter Start Date
      ↓
Enter End Date
      ↓
Click "Calculer"
      ↓
[POST Request with Form Data]
      ↓
Query Sessions (DONE, Teacher, Date Range)
      ↓
Calculate Hours per Session
      ↓
Total Hours = Sum of Session Hours
      ↓
Total Pay = Total Hours × Hourly Rate
      ↓
Display Results with Breakdown
```

---

## 📊 Data Models Visualization

```
┌─────────┐
│  Room   │
├─────────┤
│ id      │
│ name    │
│ capacity│
└────┬────┘
     │
     │ (1:M)
     │
┌────▼──────────────┐
│  CourseGroup      │
├───────────────────┤
│ id                │
│ name              │
│ level             │
│ price_per_month   │
│ teacher_id ─┐     │
│ room_id ────┼──→ (foreign key)
└────┬─────┬────────┘
     │     │
     │     └─── (1:M) ──→ Session
     │
     │ (M:M via Enrollment)
     │
┌────▼──────────────┐      ┌──────────────┐
│  Student          │      │  Enrollment  │
├───────────────────┤      ├──────────────┤
│ id                │◄─────│ id           │
│ name              │  M:M │ student_id   │
│ dob               │      │ coursegroup_id
│ parent_contact    │      │ date_enrolled│
│ phone             │      └──────────────┘
│ address           │
└────┬──────────────┘
     │
     │ (1:M)
     │
┌────▼──────────────┐
│  Payment          │
├───────────────────┤
│ id                │
│ student_id        │
│ amount            │
│ date              │
│ method            │
│ receipt_number    │
└───────────────────┘

┌──────────────────┐      ┌──────────────┐
│  Teacher         │      │  Session     │
├──────────────────┤      ├──────────────┤
│ id               │◄─────│ id           │
│ name             │  1:M │ group_id     │
│ phone            │      │ date         │
│ hourly_rate      │      │ start_time   │
└──────────────────┘      │ end_time     │
                          │ status       │
                          │ room_id      │
                          └────┬─────────┘
                               │
                               │ (1:M)
                               │
                          ┌────▼────────────┐
                          │  Attendance     │
                          ├─────────────────┤
                          │ id              │
                          │ session_id      │
                          │ student_id      │
                          │ is_present      │
                          │ date_recorded   │
                          └─────────────────┘
```

---

## 🎯 Key Interactions

### AJAX Interactions
- Student Search: `/cashier/student-search/?q=name`
- Student Detail: `/cashier/student-detail/?student_id=<id>`
- Returns JSON with Select2 format or student info

### Form Submissions
- Payment: `POST /cashier/payment/create/`
- Attendance: `POST /sessions/<id>/attendance/`
- Payroll: `POST /payroll/teacher/`

### PDF Downloads
- Receipt: Auto-download from payment form

---

This sitemap provides a visual guide to the entire application structure, user flows, and page layouts.
