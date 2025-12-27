# Session Generation & Exception Management Setup Guide

## Overview
The system now supports:
- **Automatic Session Generation** from CourseGroup schedules
- **Per-Date Session Exceptions** (cancel or override time/room)
- **Flexible Timetable Management** via Web UI and management commands

## Features

### 1. Session Generation
Sessions are auto-generated based on CourseGroup fixed weekly schedules.

**Via Web UI:**
- Navigate to **Planification > Générer sessions**
- Select number of weeks
- Choose "Force update" to modify existing sessions if group times changed
- See detailed summary of created/updated/deleted sessions

**Via Management Command:**
```bash
python manage.py generate_sessions --weeks=4
python manage.py generate_sessions --start=2024-12-22 --end=2025-01-31
python manage.py generate_sessions --weeks=4 --force
```

### 2. Session Exceptions
Define per-date exceptions for any CourseGroup:
- **Cancel**: Remove a single occurrence
- **Override**: Change time/room for that date only

**Via Web UI:**
- Navigate to **Planification > Exceptions**
- Add/edit/delete exceptions
- Auto-regenerates affected sessions

**Example:**
- CourseGroup "Math 101" normally meets Monday 10:00-12:00 in Room A
- Create exception: Dec 22, change to 14:00-16:00 (afternoon)
- Or: Dec 20, cancel (holiday)

### 3. Models

#### SessionException
```python
- course_group: FK to CourseGroup
- date: DateField (unique together with course_group)
- cancelled: Boolean (if True, session is deleted)
- override_room: Optional FK to Room
- override_start_time: Optional TimeField
- override_end_time: Optional TimeField
- notes: TextField
```

#### Session (updated)
- Added optional `room` FK for per-session overrides
- Updated conflict detection to consider effective room

## Setup Instructions

### Step 1: Create Migrations
```bash
cd c:\Users\yk1yo\Documents\Afnan\server\venv\school_erp
python manage.py makemigrations core
```

Expected output:
```
Migrations for 'core':
  core/migrations/XXXX_auto_YYYYMMDD_HHMMSS.py
    - Create model SessionException
    - Add field room to session
```

### Step 2: Apply Migrations
```bash
python manage.py migrate core
```

### Step 3: Generate Initial Sessions
```bash
# For next 4 weeks
python manage.py generate_sessions --weeks=4

# Or specify exact date range
python manage.py generate_sessions --start=2024-12-22 --end=2025-02-22
```

### Step 4: Verify in Admin
- Login to Django Admin
- Check "Sessions" table (should have many new entries)
- Check "Session Exceptions" section to manage exceptions

## URLs & Views

| Feature | URL | Method |
|---------|-----|--------|
| Schedule View | `/schedule/` | GET |
| Generate Sessions | `/sessions/generate/` | GET, POST |
| Session Exceptions | `/sessions/exceptions/` | GET, POST |
| Session Create | `/sessions/create/` | GET, POST |
| Session Edit | `/sessions/{id}/edit/` | GET, POST |
| Session Delete | `/sessions/{id}/delete/` | POST |
| Today's Sessions | `/sessions/today/` | GET |

## Workflow Example

1. **Define CourseGroups**
   - Math 101: Monday 10:00-12:00, Room A
   - English: Tuesday 14:00-16:00, Room B

2. **Generate Sessions**
   - Run: `python manage.py generate_sessions --weeks=8`
   - Creates 8 × 2 = 16 sessions

3. **Add Exception**
   - Create exception: Math 101, Dec 23, override to 15:00-17:00
   - Session auto-regenerated with new time

4. **View Schedule**
   - Navigate to **Planification**
   - See all sessions with visual grid
   - Buttons to generate or manage exceptions

## Database Structure

```
CourseGroup
├── schedule_day: MON, TUE, WED, THU, FRI, SAT, SUN
├── start_time
├── end_time
└── Sessions (auto-generated from above)
    ├── date
    ├── start_time (can differ from CourseGroup if room override)
    ├── end_time
    ├── room (optional override)
    └── SessionException (per-date rules)
        ├── cancelled
        ├── override_room
        ├── override_start_time
        └── override_end_time
```

## Troubleshooting

**Sessions not showing?**
- Run: `python manage.py generate_sessions --weeks=4 --force`
- Check CourseGroup status (must be `is_active=True`)

**Room conflicts when generating?**
- Check admin for overlapping CourseGroups
- SessionException override_room allows moving to alternate room

**Exception not applied?**
- Verify date matches exactly (YYYY-MM-DD format)
- Check CourseGroup is active
- Run: `python manage.py generate_sessions --force` to regenerate

## Future Enhancements

- Export timetable (PDF, Excel)
- Student view of personal schedule
- Automatic holiday exceptions
- Bulk exception import (CSV)
- Calendar view (month/day)
- Payroll summary based on actual sessions
