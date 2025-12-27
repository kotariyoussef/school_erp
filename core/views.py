from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from django.utils import timezone
from datetime import datetime
from django.db.models import Q, Count, Sum
from decimal import Decimal

from .models import Student, Payment, Enrollment, Room
from .utils import get_dashboard_stats, generate_receipt_pdf, calculate_student_monthly_total, generate_sessions_from_coursegroups
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
	results = []
	
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
	"""List all students with basic info"""
	students = Student.objects.filter(is_active=True).prefetch_related('enrollment_set__course_group')
	student_filter = StudentFilter(request.GET, queryset=students)
	students = student_filter.qs
	return render(request, 'core/students_list.html', {'students': students, 'filter': student_filter})



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
	"""List all sessions scheduled for today."""
	today = timezone.now().date()
	sessions_qs = Session.objects.filter(date=today).select_related('group', 'group__teacher', 'group__room')
	session_filter = SessionFilter(request.GET, queryset=sessions_qs)
	sessions = session_filter.qs
	return render(request, 'core/sessions_today.html', {'sessions': sessions, 'today': today, 'filter': session_filter})


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
	"""Display sessions in a week view (schedule grid)."""
	from datetime import timedelta

	# Get the week starting date (Monday)
	today = timezone.now().date()
	week_start = today - timedelta(days=today.weekday())
	week_end = week_start + timedelta(days=6)

	# Get week parameter from request (e.g., ?week=2024-01-08 for that Monday)
	week_param = request.GET.get('week')
	if week_param:
		try:
			parsed = datetime.strptime(week_param, '%Y-%m-%d').date()
			# normalize to monday
			week_start = parsed - timedelta(days=parsed.weekday())
			week_end = week_start + timedelta(days=6)
		except Exception:
			# ignore invalid input and keep current week
			pass

	# Get all rooms
	from .models import Room
	rooms = Room.objects.all().order_by('name')

	# Build list of dates for the week (explicit list for templates)
	dates = [week_start + timedelta(days=i) for i in range(7)]

	# Base sessions queryset for the week; allow SessionFilter to refine
	base_sessions = Session.objects.filter(date__range=[week_start, week_end], status__in=['PLANNED', 'DONE']).select_related('group', 'group__teacher', 'group__room')
	session_filter = SessionFilter(request.GET, queryset=base_sessions)
	filtered_sessions = session_filter.qs

	# Build schedule grid: schedule[date][room.id] -> {room, sessions}
	schedule = {}
	for date in dates:
		schedule[date] = {}
		for room in rooms:
			# filter the already-filtered sessions for this specific room/day
			sessions_qs = filtered_sessions.filter(group__room=room, date=date).order_by('start_time')
			schedule[date][room.id] = {
				'room': room,
				'sessions': list(sessions_qs)
			}

	# Build rows per room to simplify template rendering: each row has 'room' and 'cells' list aligned with `dates`
	room_rows = []
	for room in rooms:
		cells = []
		for date in dates:
			sessions_for_cell = schedule.get(date, {}).get(room.id, {}).get('sessions', [])
			cells.append({'date': date, 'sessions': sessions_for_cell})
		room_rows.append({'room': room, 'cells': cells})

	# Day names (aligned with `dates` list)
	weekdays = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

	# build date labels to pair weekday names with dates for template
	date_labels = []
	for idx, date in enumerate(dates):
		label = weekdays[idx] if idx < len(weekdays) else date.strftime('%A')
		date_labels.append({'weekday': label, 'date': date})

	context = {
		'week_start': week_start,
		'week_end': week_end,
		'prev_week': week_start - timedelta(days=7),
		'next_week': week_start + timedelta(days=7),
		'weekdays': weekdays,
		'dates': dates,
		'date_labels': date_labels,
		'rooms': rooms,
		'schedule': schedule,
		'room_rows': room_rows,
		'filter': session_filter,
		'today': today,
	}

	return render(request, 'core/sessions_schedule.html', context)


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
def enrollment_remove(request, student_id, enrollment_id):
	"""Remove an enrollment"""
	student = get_object_or_404(Student, pk=student_id)
	enrollment = get_object_or_404(Enrollment, pk=enrollment_id, student=student)
	
	course_name = enrollment.course_group.name
	enrollment.delete()
	
	messages.success(request, f'Inscription à {course_name} supprimée!')
	return redirect('student_page', student_id=student_id)
