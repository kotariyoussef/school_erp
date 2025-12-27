# 📚 School ERP System

A comprehensive Django-based school management system with modern Bootstrap 5 UI/UX.

## 🎯 Features

### Finance Management
- 💰 Student payment processing with AJAX autocomplete
- 📄 Automatic PDF receipt generation
- 📊 Payment history and status tracking
- 🔴 Red list of unpaid students

### Academic Management
- 📅 Session scheduling with room conflict prevention
- ✅ Daily attendance checklist (default: present)
- 👥 Student and course management
- 📈 Enrollment tracking

### HR/Payroll
- 👨‍🏫 Teacher profile management
- 💵 Automatic payroll calculation (hours × hourly_rate)
- 📋 Session-based pay computation
- 📊 Payroll reports by date range

### Dashboard
- 📊 Real-time KPI cards (revenue, students, unpaid)
- 📅 Weekly schedule grid view
- ⚡ Quick action buttons
- 🔍 Advanced filtering and search

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Django 6.0
- SQLite/PostgreSQL

### Installation

1. **Navigate to project**
```bash
cd c:\Users\yk1yo\Documents\Afnan\server\venv\school_erp
```

2. **Create and apply migrations**
```bash
python manage.py makemigrations core
python manage.py migrate
```

3. **Generate test data**
```bash
python manage.py shell
```
```python
from core.fixtures import generate_fixtures
generate_fixtures()
exit()
```

4. **Create superuser** (if needed)
```bash
python manage.py createsuperuser
```

5. **Start server**
```bash
python manage.py runserver
```

6. **Access application**
- App: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

## 📋 Navigation

| Link | Purpose |
|------|---------|
| `/` | Dashboard with KPIs |
| `/students/` | Student list |
| `/students/<id>/` | Student profile & history |
| `/courses/` | Course management |
| `/teachers/` | Teacher profiles |
| `/rooms/` | Room management |
| `/cashier/payment/create/` | Payment entry |
| `/sessions/today/` | Today's sessions |
| `/schedule/` | Weekly schedule grid |
| `/payroll/teacher/` | Payroll calculator |

## 🏗️ Project Structure

```
school_erp/
├── core/                    # Main app
│   ├── models.py           # Database models
│   ├── views.py            # Request handlers
│   ├── urls.py             # URL routing
│   ├── admin.py            # Admin interface
│   ├── utils.py            # Business logic
│   └── fixtures.py         # Test data
├── templates/core/         # HTML templates
│   ├── base.html           # Master layout
│   ├── dashboard.html      # Main dashboard
│   ├── payment_create.html # Payment form
│   └── ...                 # Other pages
├── manage.py
└── COMPLETION_SUMMARY.md   # Full documentation
```

## 💻 Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 6.0 |
| Frontend | Bootstrap 5.3 |
| Database | Django ORM (SQLite/PostgreSQL) |
| Search | Select2 4.1 |
| PDF | ReportLab |
| Icons | Bootstrap Icons 1.11 |

## 🔑 Key Models

### Room
- Name, Capacity

### Teacher
- Name, Phone, Hourly Rate

### CourseGroup
- Name, Level, Price/month
- Relations: Teacher, Room

### Student
- Name, DOB, Parent Contact, Phone, Address

### Enrollment
- Student ↔ CourseGroup relationship

### Payment
- Student, Amount, Method, Receipt #
- Auto-generates receipt PDF

### Session
- Date, Time, Group, Room
- Validation: No room double-booking

### Attendance
- Session, Student, Is Present

## 🎨 UI/UX Highlights

- **Gradient Sidebar**: Purple theme (260px fixed width)
- **Responsive Design**: Mobile-first approach
- **KPI Cards**: Hover animation with shadow
- **Status Badges**: Color-coded status indicators
- **Professional Tables**: With hover effect
- **Icons**: Bootstrap Icons throughout
- **Dark Mode Ready**: CSS variable based colors

## 📊 Business Logic

### Payment Flow
```
Search Student → Auto-fill Amount → Confirm → PDF Receipt
```

### Attendance Flow
```
Daily Session List → Click Attendance → Check Absences → Save
```

### Payroll Flow
```
Select Teacher + Date Range → Calculate → Display Hours & Pay
```

## 🔐 Security Features

- Django CSRF protection
- Form validation
- Admin authentication
- Session management

## 📱 Responsive Breakpoints

- Desktop (≥992px): Full layout
- Tablet (≥768px): Adjusted sidebar
- Mobile (<768px): Collapsed sidebar

## 🚨 Common Tasks

### Create Test Data
```bash
python manage.py shell
from core.fixtures import quick_test_data
quick_test_data()
```

### Access Admin
```
URL: http://127.0.0.1:8000/admin/
Username: (your superuser)
```

### Generate Payment Report
```python
from core.utils import get_dashboard_stats
stats = get_dashboard_stats()
print(stats['revenue']['month'])  # Monthly revenue
```

### Calculate Teacher Pay
```python
from core.models import Session
from decimal import Decimal
teacher_id = 1
sessions = Session.objects.filter(group__teacher_id=teacher_id, status='DONE')
total_hours = sum(s.duration_hours() for s in sessions)
total_pay = Decimal(total_hours) * teacher.hourly_rate
```

## 📚 Documentation

- **COMPLETION_SUMMARY.md** - Detailed feature overview
- **IMPLEMENTATION_CHECKLIST.md** - Complete checklist
- **This file** - Quick reference

## 🤝 Support

For detailed information, refer to:
1. `COMPLETION_SUMMARY.md` - Feature details
2. Code comments in views.py and models.py
3. Django admin for data management

## 📈 Next Steps

1. ✅ Run migrations
2. ✅ Generate test data
3. ✅ Test payment workflow
4. ✅ Test attendance tracking
5. ✅ Verify payroll calculations
6. ✅ Deploy to production

## 📄 License

This project is designed for school management use.

---

**Status**: ✅ Complete and Ready for Testing  
**Last Updated**: Session 5  
**Tech Stack**: Django 6.0 + Bootstrap 5.3
