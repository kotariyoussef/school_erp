from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.cockpit, name='cockpit'),
    
    # Student CRUD
    path('students/', views.students_list, name='students_list'),
    path('students/create/', views.student_create, name='student_create'),
    path('students/<int:student_id>/', views.student_page, name='student_page'),
    path('students/<int:student_id>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:student_id>/delete/', views.student_delete, name='student_delete'),
    path('students/<int:student_id>/delete-confirm/', views.student_delete_confirm, name='student_delete_confirm'),
    
    # Enrollment management
    path('students/<int:student_id>/enrollment/add/', views.enrollment_add, name='enrollment_add'),
    path('enrollment/<int:enrollment_id>/remove/', views.enrollment_remove, name='enrollment_remove'),
    
    # Courses
    path('courses/', views.courses_list, name='courses_list'),
    path('teachers/', views.teachers_list, name='teachers_list'),
    path('rooms/', views.rooms_list, name='rooms_list'),
    
    # Sessions
    path('schedule/', views.sessions_schedule, name='sessions_schedule'),
    path('sessions/today/', views.sessions_today, name='sessions_today'),
    path('sessions/<int:session_id>/attendance/', views.session_attendance, name='session_attendance'),
    path('sessions/create/', views.session_create, name='session_create'),
    path('sessions/<int:session_id>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:session_id>/delete/', views.session_delete, name='session_delete'),
    path('sessions/generate/', views.session_generate_bulk, name='session_generate_bulk'),
    path('sessions/exceptions/', views.session_exceptions_list, name='session_exceptions_list'),
    
    # Cashier
    path('cashier/payment/create/', views.payment_create, name='payment_create'),
    path('cashier/student-search/', views.student_search, name='student_search'),
    path('cashier/student-unpaid-search/', views.student_unpaid_search, name='student_unpaid_search'),
    path('cashier/student-detail/', views.student_detail, name='student_detail'),
    
    # Payroll
    path('payroll/teacher/', views.teacher_payroll, name='teacher_payroll'),
]

