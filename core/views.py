from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from django.utils import timezone
from datetime import datetime
from django.db.models import Q, Count, Sum
from decimal import Decimal
from datetime import timedelta

from .models import Student, Payment, Enrollment, Room, Teacher
from .utils import _build_room_schedule, _build_teacher_schedule, _calculate_week_stats, get_dashboard_stats, generate_receipt_pdf, calculate_student_monthly_total, generate_sessions_from_coursegroups
from .forms import SessionForm, StudentForm, EnrollmentForm
from django.core.paginator import Paginator
from .models import CourseGroup, Session, Attendance, SessionException
from django.views.decorators.http import require_http_methods
from django.db import transaction
from decimal import Decimal as D
from collections import defaultdict
from .filters import StudentFilter, CourseGroupFilter, TeacherFilter, RoomFilter, SessionFilter
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_POST


def payment_create(request):
	"""
	Cashier view to create a payment. GET renders the form, POST creates the Payment
	and returns a PDF receipt for download.
	"""
	if request.method == 'GET':
		return render(request, 'core/payment_create.html', {
            'default_student_id': request.GET.get('student_id')
        })

	# POST -> create payment
	if request.method == 'POST':
		student_id = request.POST.get('student_id')
		amount = request.POST.get('amount')
		payment_method = request.POST.get('payment_method', 'CASH')
		month_covered = request.POST.get('month_covered')

		if not student_id or not amount:
			return HttpResponseBadRequest('Missing student or amount')

		student = get_object_or_404(Student, pk=student_id)

		try:
			amount_dec = Decimal(amount)
		except Exception:
			return HttpResponseBadRequest('Montant invalide')

		# default month_covered to first day of current month
		if not month_covered:
			now = timezone.now().date()
			month_covered = now.replace(day=1)
		else:
			try:
				month_covered = datetime.strptime(month_covered, '%Y-%m-%d').date()
			except Exception:
				month_covered = timezone.now().date().replace(day=1)

		payment = Payment.objects.create(
			student=student,
			amount=amount_dec,
			payment_date=timezone.now().date(),
			month_covered=month_covered,
			status='PAID',
			payment_method=payment_method,
			created_by=request.user.get_username() if hasattr(request, 'user') and request.user.is_authenticated else ''
		)

		# Generate receipt PDF
		pdf_buffer = generate_receipt_pdf(payment)

		response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
		response['Content-Disposition'] = f'attachment; filename="receipt_{payment.receipt_number}.pdf"'
		return response


@require_GET
def student_search(request):
	"""AJAX endpoint for Select2 student search. Query param `q`."""
	q = request.GET.get('q', '').strip()
	results = []
	if q:
		students = Student.objects.filter(name__icontains=q)[:20]
	else:
		students = Student.objects.all()[:20]

	for s in students:
		results.append({
			'id': s.id,
			'text': f"{s.name} ({s.parent_name or s.parent_contact})"
		})

	return JsonResponse({'results': results})


@require_GET
def student_unpaid_search(request):
	"""AJAX endpoint for Select2 student search filtered to unpaid students. Query param `q`."""
	from django.utils import timezone
	
	q = request.GET.get('q', '').strip()
	
	# Get current month
	current_month = timezone.now().date().replace(day=1)
	
	# Get all students or filter by name
	if q:
		students = Student.objects.filter(name__icontains=q, is_active=True)[:50]
	else:
		students = Student.objects.filter(is_active=True)[:50]
	
	# Filter to unpaid students only
	unpaid_students = []
	for s in students:
		required = calculate_student_monthly_total(s)
		paid = Payment.objects.filter(
			student=s,
			month_covered=current_month,
			status='PAID'
		).aggregate(total=Sum('amount'))['total'] or Decimal('0')
		
		if paid < required:  # Student has unpaid amount
			unpaid_students.append({
				'id': s.id,
				'text': f"{s.name} ({s.parent_name or s.parent_contact}) - Due: {required - paid} DH",
				'due_amount': str(required - paid)
			})
	
	return JsonResponse({'results': unpaid_students})


@require_GET
def student_detail(request):
	"""Return student details including calculated amount due and enrollments."""
	student_id = request.GET.get('id')
	if not student_id:
		return HttpResponseBadRequest('Missing id')

	student = get_object_or_404(Student, pk=student_id)

	required = calculate_student_monthly_total(student)
	enrollments = student.enrollment_set.filter(is_active=True).select_related('course_group')
	groups = []
	
	# Get current month
	current_month = timezone.now().date().replace(day=1)

	paid = Payment.objects.filter(
			student=student,
			month_covered=current_month,
			status='PAID'
		).aggregate(total=Sum('amount'))['total'] or Decimal('0')
	required -= paid
	for e in enrollments:
		groups.append({'name': e.course_group.name, 'price': str(e.course_group.monthly_price)})

	data = {
		'id': student.id,
		'name': student.name,
		'parent_contact': student.parent_contact,
		'required': str(required),
		'groups': groups
	}

	return JsonResponse(data)


def cockpit(request):
	"""Operational dashboard (cockpit) for director"""
	stats = get_dashboard_stats()

	# Red list: students unpaid (use unpaid_students from utils)
	red_list = stats.get('alerts', {}).get('unpaid_students', [])

	context = {
		'stats': stats,
		'red_list': red_list,
	}

	return render(request, 'core/dashboard.html', context)


def students_list(request):
    """List all students with filtering and pagination"""
    
    # Base queryset with optimizations
    students_qs = Student.objects.filter(
        is_active=True
    ).prefetch_related(
        'enrollment_set__course_group',
        'payments'
    ).select_related()
    
    # Apply filters
    student_filter = StudentFilter(request.GET, queryset=students_qs)
    filtered_qs = student_filter.qs.order_by('name')
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', '25')
    
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 25
    except (ValueError, TypeError):
        per_page = 25
    
    paginator = Paginator(filtered_qs, per_page)
    students = paginator.get_page(page)
    
    # Build querystring for pagination (exclude 'page' parameter)
    qs_dict = request.GET.copy()
    qs_dict.pop('page', None)
    querystring = qs_dict.urlencode()
    
    # Check if any filters are active
    filters_active = any([
        request.GET.get('q'),
        request.GET.get('payment_status'),
        request.GET.get('course_group'),
        request.GET.get('is_active') and request.GET.get('is_active') != '',
    ])
    
    context = {
        'students': students,
        'filter': student_filter,
        'per_page': per_page,
        'querystring': querystring,
        'filters_active': filters_active,
        'total_students': students_qs.count(),
        'filtered_count': filtered_qs.count(),
    }
    
    return render(request, 'core/students_list.html', context)



def student_page(request, student_id):
	"""Student detail page with profile, enrollments, payments, attendance, and stats"""
	from django.db.models import Count, Q
	from .utils import get_student_payment_status
	
	student = get_object_or_404(Student, pk=student_id)

	# Enrollments
	enrollments = student.enrollment_set.filter(is_active=True).select_related('course_group')
	total_enrolled = enrollments.count()
	
	# Payment info (current month)
	current_month = timezone.now().date().replace(day=1)
	payment_status = get_student_payment_status(student, current_month)
	
	# Payment history
	payments_qs = Payment.objects.filter(student=student).order_by('-payment_date', '-created_at')
	paginator = Paginator(payments_qs, 10)
	page_number = request.GET.get('page')
	payments = paginator.get_page(page_number)
	
	# Attendance stats (last 30 days)
	from datetime import timedelta
	from_date = timezone.now().date() - timedelta(days=30)
	attendance_qs = Attendance.objects.filter(student=student, date__gte=from_date)
	total_classes = attendance_qs.count()
	attended_classes = attendance_qs.filter(is_present=True).count()
	attendance_rate = (attended_classes / total_classes * 100) if total_classes > 0 else 0
	
	# Monthly payment history (last 6 months)
	from dateutil.relativedelta import relativedelta
	six_months_ago = timezone.now().date() - relativedelta(months=6)
	payment_months = []
	for i in range(6):
		month_date = timezone.now().date() - relativedelta(months=i)
		month_date = month_date.replace(day=1)
		paid = Payment.objects.filter(
			student=student,
			month_covered=month_date,
			status='PAID'
		).aggregate(total=Sum('amount'))['total'] or Decimal('0')
		required = student.total_monthly_fees()
		payment_months.insert(0, {
			'month': month_date.strftime('%b %Y'),
			'paid': paid,
			'required': required,
			'status': 'OK' if paid >= required else 'PARTIAL' if paid > 0 else 'UNPAID'
		})

	context = {
		'student': student,
		'enrollments': enrollments,
		'total_enrolled': total_enrolled,
		'payments': payments,
		'payment_status': payment_status,
		'attendance_rate': round(attendance_rate, 1),
		'attended_classes': attended_classes,
		'total_classes': total_classes,
		'payment_months': payment_months,
	}

	return render(request, 'core/student_detail.html', context)


def sessions_today(request):
    """Enhanced session view with navigation and statistics"""
    
    # Determine the date to display
    date_param = request.GET.get('date')
    if date_param:
        try:
            from datetime import datetime
            view_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            view_date = timezone.now().date()
    else:
        view_date = timezone.now().date()
    
    today = timezone.now().date()
    
    # Calculate navigation dates
    prev_day = view_date - timedelta(days=1)
    next_day = view_date + timedelta(days=1)
    
    # Base queryset for the view date
    sessions_qs = Session.objects.filter(
        date=view_date
    ).select_related(
        'group',
        'group__teacher',
        'group__room'
    ).prefetch_related(
        'group__students'
    ).order_by('start_time')
    
    # Apply filters
    session_filter = SessionFilter(request.GET, queryset=sessions_qs)
    sessions = session_filter.qs
    
    # Calculate statistics
    stats = {
        'total': sessions.count(),
        'planned': sessions.filter(status='PLANNED').count(),
        'done': sessions.filter(status='DONE').count(),
        'cancelled': sessions.filter(status='CANCELLED').count(),
    }
    
    # Check if any filters are active (excluding date parameter)
    filters_active = any([
        request.GET.get('date_after'),
        request.GET.get('date_before'),
        request.GET.get('room'),
        request.GET.get('teacher'),
        request.GET.get('status'),
        request.GET.get('group_name'),
    ])
    
    # Build querystring for navigation (preserve filters)
    qs_dict = request.GET.copy()
    qs_dict.pop('date', None)  # Remove date to add it dynamically
    querystring = qs_dict.urlencode()
    
    context = {
        'sessions': sessions,
        'view_date': view_date,
        'today': today,
        'prev_day': prev_day,
        'next_day': next_day,
        'is_today': view_date == today,
        'filter': session_filter,
        'stats': stats,
        'filters_active': filters_active,
        'querystring': querystring,
    }
    
    return render(request, 'core/sessions_today.html', context)

@require_http_methods(['GET', 'POST'])
def session_create(request):
	"""Create a new session (class)"""
	if request.method == 'POST':
		form = SessionForm(request.POST)
		if form.is_valid():
			session = form.save(commit=False)
			try:
				session.full_clean()
				session.save()
			except Exception as e:
				form.add_error(None, str(e))
			else:
				return render(request, 'core/session_form_saved.html', {'session': session})
	else:
		form = SessionForm()

	return render(request, 'core/session_form.html', {'form': form, 'action': 'Créer'})


@require_http_methods(['GET', 'POST'])
def session_edit(request, session_id):
	"""Edit an existing session"""
	session = get_object_or_404(Session, pk=session_id)
	if request.method == 'POST':
		form = SessionForm(request.POST, instance=session)
		if form.is_valid():
			s = form.save(commit=False)
			try:
				s.full_clean()
				s.save()
			except Exception as e:
				form.add_error(None, str(e))
			else:
				return render(request, 'core/session_form_saved.html', {'session': s})
	else:
		form = SessionForm(instance=session)

	return render(request, 'core/session_form.html', {'form': form, 'action': 'Modifier', 'session': session})


@require_http_methods(['POST'])
def session_delete(request, session_id):
	session = get_object_or_404(Session, pk=session_id)
	session.delete()
	return render(request, 'core/session_deleted.html', {'session_id': session_id})


@require_http_methods(['GET', 'POST'])
def session_attendance(request, session_id):
	"""Show attendance checklist for a session and save attendance.

	Business rule: default all present; admin unchecks absentees.
	"""
	session = get_object_or_404(Session, pk=session_id)
	students = session.group.students.filter(is_active=True)

	if request.method == 'GET':
		# prefill: check if Attendance exists for this date/group
		existing = Attendance.objects.filter(course_group=session.group, date=session.date)
		present_map = {a.student_id: a.is_present for a in existing}
		students_list = []
		for s in students:
			# default to True (present) when no record exists
			checked = present_map.get(s.id, True)
			students_list.append({'student': s, 'checked': checked})

		return render(request, 'core/session_attendance.html', {
			'session': session,
			'students_list': students_list,
		})

	# POST: process attendance form
	# expected: checkbox 'present_<student_id>' for those present
	with transaction.atomic():
		for student in students:
			key = f'present_{student.id}'
			is_present = key in request.POST
			att, created = Attendance.objects.update_or_create(
				student=student,
				course_group=session.group,
				date=session.date,
				defaults={'is_present': is_present}
			)

	# mark session as DONE if attendance saved
	session.status = 'DONE'
	session.save()

	return render(request, 'core/session_attendance_saved.html', {'session': session})


def teacher_payroll(request):
	"""Calculate payroll for a teacher over a date range."""
	teachers = CourseGroup.objects.values_list('teacher', flat=True).distinct()
	from .models import Teacher
	teacher_qs = Teacher.objects.filter(id__in=teachers)

	result = None
	if request.method == 'POST':
		teacher_id = request.POST.get('teacher_id')
		start = request.POST.get('start_date')
		end = request.POST.get('end_date')
		if not (teacher_id and start and end):
			return HttpResponseBadRequest('Missing parameters')
		teacher = get_object_or_404(Teacher, pk=teacher_id)
		start_d = datetime.strptime(start, '%Y-%m-%d').date()
		end_d = datetime.strptime(end, '%Y-%m-%d').date()

		sessions = Session.objects.filter(
			group__teacher=teacher,
			status='DONE',
			date__range=[start_d, end_d]
		)

		sessions_list = []
		total_hours = 0.0
		for s in sessions:
			hrs = s.duration_hours()
			total_hours += hrs
			sessions_list.append({'session': s, 'hours': hrs})

		total_pay = D(str(total_hours)) * teacher.hourly_rate

		result = {
			'teacher': teacher,
			'sessions': sessions_list,
			'total_hours': total_hours,
			'total_pay': total_pay,
		}

	return render(request, 'core/teacher_payroll.html', {'teacher_qs': teacher_qs, 'result': result})


def courses_list(request):
	"""Display all course groups (classes) with summary info."""
	from .models import CourseGroup
	courses = CourseGroup.objects.all().select_related('teacher', 'room')
	
	# Annotate with enrollment count
	from django.db.models import Count
	courses = courses.annotate(enrollment_count=Count('enrollment'))

	course_filter = CourseGroupFilter(request.GET, queryset=courses)
	courses = course_filter.qs

	return render(request, 'core/courses_list.html', {'courses': courses, 'filter': course_filter})


def teachers_list(request):
    """Display all teachers with summary info."""
    from .models import Teacher

    teachers = Teacher.objects.annotate(
        course_count=Count('course_groups', distinct=True),
        session_count=Count(
            'course_groups__sessions',
            filter=Q(course_groups__sessions__status='PLANNED'),
            distinct=True
        )
    )

    teacher_filter = TeacherFilter(request.GET, queryset=teachers)
    teachers = teacher_filter.qs

    return render(request, 'core/teachers_list.html', {'teachers': teachers, 'filter': teacher_filter})

def rooms_list(request):
	"""Display all rooms with summary info."""
	from .models import Room
	from django.db.models import Count
	
	rooms = Room.objects.all()
	rooms = rooms.annotate(
		course_count=Count('coursegroup'),
		session_count=Count('coursegroup__session', filter=timezone.Q(coursegroup__session__status='PLANNED'))
	)
	
	room_filter = RoomFilter(request.GET, queryset=rooms)
	rooms = room_filter.qs

	return render(request, 'core/rooms_list.html', {'rooms': rooms, 'filter': room_filter})


def sessions_schedule(request):
    """Enhanced weekly schedule view with better structure and filtering"""
    
    # Get the week starting date (Monday)
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Get week parameter from request
    week_param = request.GET.get('week')
    if week_param:
        try:
            parsed = datetime.strptime(week_param, '%Y-%m-%d').date()
            # Normalize to Monday
            week_start = parsed - timedelta(days=parsed.weekday())
            week_end = week_start + timedelta(days=6)
        except (ValueError, TypeError):
            pass  # Keep current week
    
    # Determine view mode (room-based or teacher-based)
    view_mode = request.GET.get('view', 'room')  # 'room' or 'teacher'
    
    # Get filter parameters
    room_filter = request.GET.get('room_id')
    teacher_filter = request.GET.get('teacher_id')
    status_filter = request.GET.get('status')
    
    # Build list of dates for the week
    dates = [week_start + timedelta(days=i) for i in range(7)]
    
    # Base sessions queryset for the week
    base_sessions = Session.objects.filter(
        date__range=[week_start, week_end]
    ).select_related(
        'group',
        'group__teacher',
        'group__room'
    ).prefetch_related(
        'group__students'
    )
    
    # Apply filters
    if room_filter:
        base_sessions = base_sessions.filter(group__room_id=room_filter)
    if teacher_filter:
        base_sessions = base_sessions.filter(group__teacher_id=teacher_filter)
    if status_filter:
        base_sessions = base_sessions.filter(status=status_filter)
    
    # Get all rooms and teachers for the filters
    rooms = Room.objects.filter(is_active=True).order_by('name')
    teachers = Teacher.objects.filter(is_active=True).order_by('name')
    
    # Build schedule grid based on view mode
    if view_mode == 'teacher':
        rows = _build_teacher_schedule(teachers, dates, base_sessions)
        row_label = 'Professeur'
    else:
        rows = _build_room_schedule(rooms, dates, base_sessions)
        row_label = 'Salle'
    
    # Build date labels with weekday names
    weekdays = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    date_labels = [
        {
            'weekday': weekdays[i],
            'date': date,
            'is_today': date == today,
            'is_weekend': i >= 5
        }
        for i, date in enumerate(dates)
    ]
    
    # Calculate statistics
    stats = _calculate_week_stats(base_sessions, dates)
    
    # Check if filters are active
    filters_active = any([room_filter, teacher_filter, status_filter])
    
    context = {
        'week_start': week_start,
        'week_end': week_end,
        'prev_week': week_start - timedelta(days=7),
        'next_week': week_start + timedelta(days=7),
        'dates': dates,
        'date_labels': date_labels,
        'rows': rows,
        'row_label': row_label,
        'view_mode': view_mode,
        'rooms': rooms,
        'teachers': teachers,
        'stats': stats,
        'today': today,
        'filters_active': filters_active,
        'room_filter': room_filter,
        'teacher_filter': teacher_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'core/sessions_schedule.html', context)

@require_POST
def session_quick_status_update(request, session_id):
    """
    Quick update session status via AJAX
    Used for marking sessions as done/cancelled from schedule view
    """
    session = get_object_or_404(Session, id=session_id)
    new_status = request.POST.get('status')
    
    if new_status not in ['PLANNED', 'DONE', 'CANCELLED']:
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    
    session.status = new_status
    session.save()
    
    return JsonResponse({
        'success': True,
        'session_id': session.id,
        'new_status': new_status,
        'message': f'Statut mis à jour: {session.get_status_display()}'
    })


def session_detail_ajax(request, session_id):
    """
    Get session details for modal display
    """
    session = get_object_or_404(
        Session.objects.select_related(
            'group',
            'group__teacher',
            'group__room'
        ).prefetch_related(
            'group__students'
        ),
        id=session_id
    )
    
    # Get attendance if exists
    from .models import Attendance
    attendance = Attendance.objects.filter(
        course_group=session.group,
        date=session.date
    ).select_related('student')
    
    students = session.group.students.all()
    attendance_dict = {a.student_id: a.is_present for a in attendance}
    
    student_list = []
    for student in students:
        student_list.append({
            'id': student.id,
            'name': student.name,
            'is_present': attendance_dict.get(student.id),
        })
    
    data = {
        'id': session.id,
        'group': {
            'name': session.group.name,
            'subject': session.group.subject,
            'level': session.group.level,
        },
        'date': session.date.strftime('%Y-%m-%d'),
        'start_time': session.start_time.strftime('%H:%M'),
        'end_time': session.end_time.strftime('%H:%M'),
        'duration': session.duration_hours(),
        'room': {
            'name': session.group.room.name,
            'capacity': session.group.room.capacity,
        },
        'teacher': {
            'name': session.group.teacher.name,
            'phone': session.group.teacher.phone,
        },
        'status': session.status,
        'status_display': session.get_status_display(),
        'students': student_list,
        'student_count': len(student_list),
        'notes': session.notes,
    }
    
    return JsonResponse(data)


@require_http_methods(['GET', 'POST'])
def session_generate_bulk(request):
	"""On-demand generate/update sessions for a date range."""
	from datetime import timedelta
	
	summary = None
	errors = []
	
	if request.method == 'POST':
		weeks = int(request.POST.get('weeks', 4))
		force = request.POST.get('force') == 'on'
		
		today = timezone.now().date()
		start_date = today
		end_date = today + timedelta(weeks=weeks)
		
		try:
			summary = generate_sessions_from_coursegroups(start_date, end_date, force=force)
		except Exception as e:
			errors.append(str(e))
	
	return render(request, 'core/session_generate.html', {
		'summary': summary,
		'errors': errors,
	})


@require_http_methods(['GET', 'POST'])
def session_exceptions_list(request):
	"""List and manage session exceptions."""
	from .models import Room
	
	exceptions = SessionException.objects.select_related('course_group', 'override_room').order_by('-date')
	
	# Filter by course_group if provided
	group_id = request.GET.get('group_id')
	if group_id:
		exceptions = exceptions.filter(course_group_id=group_id)
	
	# Form submission: create/edit exception
	if request.method == 'POST':
		action = request.POST.get('action')
		group_id = int(request.POST.get('group_id'))
		date_str = request.POST.get('date')
		from datetime import datetime as dt
		try:
			date_obj = dt.strptime(date_str, '%Y-%m-%d').date()
		except Exception:
			return HttpResponseBadRequest('Invalid date')
		
		group = get_object_or_404(CourseGroup, pk=group_id)
		
		if action == 'cancel':
			exc, created = SessionException.objects.update_or_create(
				course_group=group,
				date=date_obj,
				defaults={'cancelled': True, 'override_room': None, 'override_start_time': None, 'override_end_time': None}
			)
		elif action == 'override':
			override_room_id = request.POST.get('override_room_id')
			override_start = request.POST.get('override_start_time')
			override_end = request.POST.get('override_end_time')
			
			exc, created = SessionException.objects.update_or_create(
				course_group=group,
				date=date_obj,
				defaults={
					'cancelled': False,
					'override_room_id': override_room_id or None,
					'override_start_time': override_start or None,
					'override_end_time': override_end or None,
				}
			)
		elif action == 'delete':
			SessionException.objects.filter(course_group=group, date=date_obj).delete()
		
		# Regenerate sessions affected by this exception
		from datetime import timedelta
		start = date_obj - timedelta(days=1)
		end = date_obj + timedelta(days=1)
		generate_sessions_from_coursegroups(start, end, force=True)
		
		return render(request, 'core/session_exceptions_saved.html', {'group': group, 'date': date_obj})
	
	courses = CourseGroup.objects.filter(is_active=True).order_by('name')
	rooms = Room.objects.all()
	
	return render(request, 'core/session_exceptions_list.html', {
		'exceptions': exceptions,
		'courses': courses,
		'rooms': rooms,
		'selected_group_id': group_id,
	})


# =====================
# STUDENT CRUD VIEWS
# =====================

def student_create(request):
	"""Create a new student"""
	if request.method == 'POST':
		form = StudentForm(request.POST)
		if form.is_valid():
			student = form.save()
			messages.success(request, f'Élève {student.name} créé avec succès!')
			return redirect('core:student_page', student_id=student.id)
	else:
		form = StudentForm()
	
	return render(request, 'core/student_form.html', {
		'form': form,
		'title': 'Ajouter un nouvel élève',
		'button_text': 'Créer élève'
	})


def student_edit(request, student_id):
	"""Edit an existing student"""
	student = get_object_or_404(Student, pk=student_id)
	
	if request.method == 'POST':
		form = StudentForm(request.POST, instance=student)
		if form.is_valid():
			form.save()
			messages.success(request, f'Élève {student.name} mise à jour avec succès!')
			return redirect('core:student_page', student_id=student.id)
	else:
		form = StudentForm(instance=student)
	
	return render(request, 'core/student_form.html', {
		'form': form,
		'student': student,
		'title': f'Modifier - {student.name}',
		'button_text': 'Mettre à jour'
	})


@require_POST
def student_delete(request, student_id):
	"""Delete a student"""
	student = get_object_or_404(Student, pk=student_id)
	student_name = student.name
	student.delete()
	messages.success(request, f'Élève {student_name} supprimé avec succès!')
	return redirect('students_list')


def student_delete_confirm(request, student_id):
	"""Confirmation page before deleting a student"""
	student = get_object_or_404(Student, pk=student_id)
	
	# Get student's enrollments and related payments
	enrollments = student.enrollment_set.all()
	payments = student.payments.all()
	
	return render(request, 'core/student_delete_confirm.html', {
		'student': student,
		'enrollments': enrollments,
		'payment_count': payments.count(),
	})


@require_POST
def enrollment_add(request, student_id):
	"""Add an enrollment for a student"""
	student = get_object_or_404(Student, pk=student_id)
	course_group_id = request.POST.get('course_group_id')
	
	if not course_group_id:
		messages.error(request, 'Veuillez sélectionner un groupe de cours')
		return redirect('core:student_page', student_id=student_id)
	
	course_group = get_object_or_404(CourseGroup, pk=course_group_id)
	
	# Check if already enrolled
	if student.enrollment_set.filter(course_group=course_group).exists():
		messages.warning(request, f'{student.name} est déjà inscrit à {course_group.name}')
		return redirect('core:student_page', student_id=student_id)
	
	enrollment = Enrollment.objects.create(
		student=student,
		course_group=course_group,
		is_active=True
	)
	
	messages.success(request, f'Inscription à {course_group.name} ajoutée!')
	return redirect('core:student_page', student_id=student_id)


@require_POST
def enrollment_remove(request, enrollment_id):
    """Remove an enrollment (AJAX endpoint)"""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    student = enrollment.student
    course_name = enrollment.course_group.name
    
    # Store info before deletion
    student_id = student.id
    
    # Delete the enrollment
    enrollment.delete()
    
    # Return JSON response for AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'L\'inscription au cours "{course_name}" a été retirée avec succès.',
            'student_id': student_id,
            'new_total': float(student.total_monthly_fees())
        })
    
    # Fallback for non-AJAX requests
    messages.success(request, f'L\'inscription au cours "{course_name}" a été retirée avec succès.')
    return redirect('core:student_page', student_id=student_id)

