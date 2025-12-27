"""
Utilitaires pour le système de gestion d'école
"""
from .models import Session, CourseGroup, SessionException  # Import necessary models
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from datetime import date
from typing import List, Dict, Tuple, Optional
import calendar
from io import BytesIO
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas
from .models import Student, Payment

PAID_STATUSES = ('PAID', 'OK', 'CONFIRMED', 'COMPLETED', 'SETTLED')


# ==================== GESTION DES DATES ====================

def get_current_month_period() -> Tuple[date, date]:
    """Retourne le premier et dernier jour du mois en cours"""
    today = timezone.now().date()
    first_day = today.replace(day=1)
    last_day = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    return first_day, last_day


def get_month_period(year: int, month: int) -> Tuple[date, date]:
    """Retourne le premier et dernier jour d'un mois donné"""
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day


def get_next_month(reference_date: date) -> date:
    """Retourne le premier jour du mois suivant"""
    if reference_date.month == 12:
        return date(reference_date.year + 1, 1, 1)
    return date(reference_date.year, reference_date.month + 1, 1)


def get_previous_month(reference_date: date) -> date:
    """Retourne le premier jour du mois précédent"""
    if reference_date.month == 1:
        return date(reference_date.year - 1, 12, 1)
    return date(reference_date.year, reference_date.month - 1, 1)


def month_name_fr(month_number: int) -> str:
    """Retourne le nom du mois en français"""
    months = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
        5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
        9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }
    return months.get(month_number, "")


# ==================== CALCULS FINANCIERS ====================

def calculate_student_monthly_total(student) -> Decimal:
    """
    Calcule le total mensuel qu'un élève doit payer
    Basé sur ses inscriptions actives
    """
    from .models import Enrollment
    
    active_enrollments = Enrollment.objects.filter(
        student=student,
        is_active=True
    ).select_related('course_group')
    
    total = Decimal('0.00')
    for enrollment in active_enrollments:
        total += enrollment.course_group.monthly_price
    
    return total


def get_student_payment_status(student, month_date: Optional[date] = None) -> Dict:

    def generate_sessions_from_coursegroups(start_date: date, end_date: date, force: bool = False) -> Dict:
        """
        Crée, met à jour ou supprime des objets Session basés sur les horaires des CourseGroups
        et les exceptions de session par date.
        """
        from .models import Session, CourseGroup, SessionException
        sessions = []
    
        # Logique pour créer, mettre à jour ou supprimer des sessions
        # ...
    
        return {
            'created': len(sessions),
            'updated': 0,  # Placeholder for updated sessions count
            'deleted': 0   # Placeholder for deleted sessions count
        }
    """
    Retourne le statut de paiement détaillé d'un élève pour un mois
    
    Returns:
        {
            'required': Decimal,
            'paid': Decimal,
            'remaining': Decimal,
            'status': 'OK' | 'PARTIAL' | 'UNPAID',
            'percentage': float
        }
    """
    from .models import Payment
    
    if month_date is None:
        month_date = timezone.now().date().replace(day=1)
    
    required = calculate_student_monthly_total(student)
    
    paid = Payment.objects.filter(
        student=student,
        month_covered=month_date,
        status='PAID'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    remaining = required - paid
    
    if required > 0:
        percentage = float((paid / required) * 100)
    else:
        percentage = 0.0
    
    if paid >= required:
        status = 'OK'
    elif paid > 0:
        status = 'PARTIAL'
    else:
        status = 'UNPAID'
    
    return {
        'required': required,
        'paid': paid,
        'remaining': remaining,
        'status': status,
        'percentage': percentage
    }


def get_daily_revenue(target_date: Optional[date] = None) -> Decimal:
    """Calcule la recette du jour"""
    from .models import Payment
    
    if target_date is None:
        target_date = timezone.now().date()
    
    revenue = Payment.objects.filter(
        payment_date=target_date,
        status='PAID'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    return revenue


def get_monthly_revenue(year: int, month: int) -> Decimal:
    """Calcule la recette du mois"""
    from .models import Payment
    
    first_day, last_day = get_month_period(year, month)
    
    revenue = Payment.objects.filter(
        payment_date__range=[first_day, last_day],
        status='PAID'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    return revenue


def get_unpaid_students(month_date: Optional[date] = None) -> List[dict]:
    """
    Retourne la liste des élèves actifs non à jour pour un mois donné
    """
    if month_date is None:
        month_date = timezone.now().date()
    month_date = month_date.replace(day=1)

    students = Student.objects.filter(is_active=True).prefetch_related('payments')

    unpaid_students = []

    for student in students:
        required = student.total_monthly_fees()

        paid = Payment.objects.filter(
            student=student,
            month_covered=month_date,
            status__in=PAID_STATUSES
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')


        remaining = max(required - paid, Decimal('0'))

        if paid >= required and required > 0:
            status = 'OK'
        elif paid > 0:
            status = 'PARTIAL'
        else:
            status = 'UNPAID'

        if status in ['UNPAID', 'PARTIAL']:
            unpaid_students.append({
                'student': student,
                'required': required,
                'paid': paid,
                'remaining': remaining,
                'status': status,
            })

    return unpaid_students


# ==================== CALCULS PROFESSEURS ====================

def calculate_teacher_hours(teacher, start_date: date, end_date: date) -> Dict:
    """
    Calcule les heures travaillées par un professeur sur une période
    Basé sur le planning et les présences effectives
    """
    from .models import CourseGroup, Attendance
    
    # Récupérer tous les cours du professeur
    courses = CourseGroup.objects.filter(
        teacher=teacher,
        is_active=True
    )
    
    total_scheduled_hours = Decimal('0.00')
    total_taught_hours = Decimal('0.00')
    
    # Compter les jours entre start_date et end_date
    days_count = (end_date - start_date).days + 1
    weeks_count = days_count / 7
    
    for course in courses:
        # Heures prévues par semaine
        hours_per_session = course.duration_hours()
        scheduled = Decimal(str(hours_per_session)) * Decimal(str(weeks_count))
        total_scheduled_hours += scheduled
        
        # Heures réellement données (basé sur présences)
        sessions_count = Attendance.objects.filter(
            course_group=course,
            date__range=[start_date, end_date]
        ).values('date').distinct().count()
        
        taught = Decimal(str(hours_per_session)) * Decimal(str(sessions_count))
        total_taught_hours += taught
    
    salary_scheduled = total_scheduled_hours * teacher.hourly_rate
    salary_taught = total_taught_hours * teacher.hourly_rate
    
    return {
        'scheduled_hours': total_scheduled_hours,
        'taught_hours': total_taught_hours,
        'salary_scheduled': salary_scheduled,
        'salary_taught': salary_taught,
        'courses': courses.count()
    }


def generate_teacher_payslip_data(teacher, month: int, year: int) -> Dict:
    """
    Génère les données complètes pour une fiche de paie professeur
    """
    first_day, last_day = get_month_period(year, month)
    hours_data = calculate_teacher_hours(teacher, first_day, last_day)
    
    return {
        'teacher': teacher,
        'month': month_name_fr(month),
        'year': year,
        'period': f"{first_day.strftime('%d/%m/%Y')} - {last_day.strftime('%d/%m/%Y')}",
        'hourly_rate': teacher.hourly_rate,
        **hours_data
    }


# ==================== DÉTECTION DE CONFLITS ====================

def check_schedule_conflicts(room, schedule_day: str, start_time, end_time, exclude_course_id: Optional[int] = None) -> List:
    """
    Vérifie s'il y a des conflits d'horaire dans une salle
    
    Returns:
        Liste des cours en conflit
    """
    from .models import CourseGroup
    
    conflicts = CourseGroup.objects.filter(
        room=room,
        schedule_day=schedule_day,
        is_active=True
    )
    
    if exclude_course_id:
        conflicts = conflicts.exclude(id=exclude_course_id)
    
    conflicting_courses = []
    
    for course in conflicts:
        # Vérifier chevauchement horaire
        if (start_time < course.end_time and end_time > course.start_time):
            conflicting_courses.append(course)
    
    return conflicting_courses


def get_room_availability(room, target_day: str) -> List[Dict]:
    """
    Retourne les créneaux disponibles d'une salle pour un jour donné
    
    Returns:
        [{'start': '08:00', 'end': '10:00', 'available': True}, ...]
    """
    from .models import CourseGroup
    from datetime import time
    
    # Créneaux typiques (8h-20h)
    all_slots = []
    current_time = time(8, 0)
    end_of_day = time(20, 0)
    
    occupied_courses = CourseGroup.objects.filter(
        room=room,
        schedule_day=target_day,
        is_active=True
    ).order_by('start_time')
    
    availability = []
    
    for course in occupied_courses:
        availability.append({
            'start': course.start_time.strftime('%H:%M'),
            'end': course.end_time.strftime('%H:%M'),
            'available': False,
            'course': course
        })
    
    return availability


def generate_sessions_from_coursegroups(start_date: date, end_date: date, force: bool = False) -> Dict:
    """Create/update/delete Session objects based on CourseGroup schedules and per-date exceptions.

    Args:
        start_date: inclusive start date
        end_date: inclusive end date
        force: if True, update existing sessions when times/room differ

    Returns a summary dict: {'created', 'updated', 'deleted', 'skipped', 'errors'}
    """
    from .models import CourseGroup, Session, SessionException
    from datetime import timedelta
    from django.core.exceptions import ValidationError

    DAY_MAP = {
        'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3,
        'FRI': 4, 'SAT': 5, 'SUN': 6
    }

    summary = {'created': 0, 'updated': 0, 'deleted': 0, 'skipped': 0, 'errors': []}

    courses = CourseGroup.objects.filter(is_active=True).select_related('room', 'teacher')

    for course in courses:
        target_weekday = DAY_MAP.get(course.schedule_day)
        if target_weekday is None:
            continue

        # first date in range matching the group's weekday
        days_ahead = (target_weekday - start_date.weekday()) % 7
        current = start_date + timedelta(days=days_ahead)

        while current <= end_date:
            try:
                exception = SessionException.objects.filter(course_group=course, date=current).first()
            except Exception:
                exception = None

            # cancelled exception -> delete existing session if present
            if exception and exception.cancelled:
                existing = Session.objects.filter(group=course, date=current).first()
                if existing:
                    try:
                        existing.delete()
                        summary['deleted'] += 1
                    except Exception as e:
                        summary['errors'].append(str(e))
                else:
                    summary['skipped'] += 1
                current += timedelta(days=7)
                continue

            # determine effective values
            eff_room = exception.effective_room() if exception else course.room
            eff_start = exception.effective_start() if exception else course.start_time
            eff_end = exception.effective_end() if exception else course.end_time

            existing = Session.objects.filter(group=course, date=current).first()
            if existing:
                needs_update = (
                    existing.start_time != eff_start or
                    existing.end_time != eff_end or
                    (getattr(existing, 'room', None) != eff_room)
                )
                if needs_update and force:
                    existing.start_time = eff_start
                    existing.end_time = eff_end
                    existing.room = eff_room
                    try:
                        existing.save()
                        summary['updated'] += 1
                    except ValidationError as ve:
                        summary['errors'].append(f"{course.name} {current}: {ve}")
                else:
                    summary['skipped'] += 1
            else:
                # create
                try:
                    new = Session(group=course, date=current, start_time=eff_start, end_time=eff_end)
                    if eff_room and eff_room != course.room:
                        new.room = eff_room
                    new.save()
                    summary['created'] += 1
                except ValidationError as ve:
                    summary['errors'].append(f"{course.name} {current}: {ve}")
                except Exception as e:
                    summary['errors'].append(f"{course.name} {current}: {e}")

            current += timedelta(days=7)

    return summary


# ==================== GÉNÉRATION DE STATISTIQUES ====================

def get_dashboard_stats() -> Dict:
    """
    Génère toutes les statistiques pour le dashboard principal
    """
    from .models import Student, Teacher, CourseGroup, Payment, Room
    
    today = timezone.now().date()
    current_month = today.replace(day=1)
    
    # Statistiques générales
    active_students = Student.objects.filter(is_active=True).count()
    active_teachers = Teacher.objects.filter(is_active=True).count()
    active_courses = CourseGroup.objects.filter(is_active=True).count()
    active_rooms = Room.objects.filter(is_active=True).count()
    
    # Statistiques financières
    today_revenue = get_daily_revenue(today)
    month_revenue = get_monthly_revenue(today.year, today.month)
    
    # Élèves impayés
    unpaid = get_unpaid_students(current_month)
    unpaid_count = len(unpaid)
    unpaid_amount = sum([u['remaining'] for u in unpaid])
    
    # Conflits de planning
    conflicts = []
    for course in CourseGroup.objects.filter(is_active=True):
        course_conflicts = check_schedule_conflicts(
            course.room,
            course.schedule_day,
            course.start_time,
            course.end_time,
            course.id
        )
        if course_conflicts:
            conflicts.append({
                'course': course,
                'conflicts_with': course_conflicts
            })
    
    return {
        'counts': {
            'students': active_students,
            'teachers': active_teachers,
            'courses': active_courses,
            'rooms': active_rooms
        },
        'revenue': {
            'today': today_revenue,
            'month': month_revenue,
        },
        'alerts': {
            'unpaid_count': unpaid_count,
            'unpaid_amount': unpaid_amount,
            'conflicts': conflicts,
            'unpaid_students': unpaid[:5]  # Top 5 pour affichage
        }
    }


# ==================== GÉNÉRATION DE REÇUS PDF ====================

def generate_receipt_pdf(payment) -> BytesIO:
    """
    Génère un reçu de paiement en format PDF (A5 ou thermique)
    """
    buffer = BytesIO()
    
    # Créer le PDF en format A5 (148 x 210 mm)
    p = canvas.Canvas(buffer, pagesize=A5)
    width, height = A5
    
    # En-tête
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width/2, height - 30, "REÇU DE PAIEMENT")
    
    # Numéro de reçu
    p.setFont("Helvetica", 10)
    p.drawString(30, height - 60, f"Reçu N° : {payment.receipt_number}")
    p.drawString(30, height - 75, f"Date : {payment.payment_date.strftime('%d/%m/%Y')}")
    
    # Ligne séparatrice
    p.line(30, height - 85, width - 30, height - 85)
    
    # Informations élève
    y_position = height - 110
    p.setFont("Helvetica-Bold", 11)
    p.drawString(30, y_position, "ÉLÈVE :")
    
    p.setFont("Helvetica", 10)
    y_position -= 20
    p.drawString(40, y_position, f"Nom : {payment.student.name}")
    y_position -= 15
    p.drawString(40, y_position, f"Contact Parent : {payment.student.parent_contact}")
    
    # Ligne séparatrice
    y_position -= 10
    p.line(30, y_position, width - 30, y_position)
    
    # Détails du paiement
    y_position -= 25
    p.setFont("Helvetica-Bold", 11)
    p.drawString(30, y_position, "DÉTAILS DU PAIEMENT :")
    
    p.setFont("Helvetica", 10)
    y_position -= 20
    p.drawString(40, y_position, f"Mois couvert : {payment.month_covered.strftime('%B %Y')}")
    y_position -= 15
    p.drawString(40, y_position, f"Mode de paiement : {payment.get_payment_method_display()}")
    
    # Montant (en gros)
    y_position -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y_position, "MONTANT PAYÉ :")
    p.setFont("Helvetica-Bold", 18)
    p.drawString(width - 150, y_position, f"{payment.amount} DH")
    
    # Ligne séparatrice
    y_position -= 15
    p.line(30, y_position, width - 30, y_position)
    
    # Groupes inscrits
    y_position -= 25
    p.setFont("Helvetica-Bold", 10)
    p.drawString(30, y_position, "Groupes inscrits :")
    
    p.setFont("Helvetica", 9)
    enrollments = payment.student.enrollment_set.filter(is_active=True)
    for enrollment in enrollments[:5]:  # Max 5 pour ne pas déborder
        y_position -= 12
        p.drawString(40, y_position, f"• {enrollment.course_group.name} - {enrollment.course_group.monthly_price} DH")
    
    # Pied de page
    p.setFont("Helvetica-Oblique", 8)
    p.drawCentredString(width/2, 40, "Merci pour votre confiance")
    p.drawCentredString(width/2, 28, f"École de Soutien Scolaire - {settings.SCHOOL_NAME if hasattr(settings, 'SCHOOL_NAME') else ''}")
    
    # Finaliser
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer


def generate_thermal_receipt(payment) -> str:
    """
    Génère un reçu format texte pour imprimante thermique (58mm)
    Format simple pour WhatsApp ou impression ticket
    """
    receipt = f"""
{'='*32}
   REÇU DE PAIEMENT
{'='*32}
Reçu N° : {payment.receipt_number}
Date    : {payment.payment_date.strftime('%d/%m/%Y %H:%M')}
{'='*32}

ÉLÈVE : {payment.student.name}
Parent: {payment.student.parent_contact}

{'='*32}
Mois   : {payment.month_covered.strftime('%B %Y')}
Mode   : {payment.get_payment_method_display()}

{'='*32}
MONTANT : {payment.amount} DH
{'='*32}

Groupes inscrits :
"""
    
    enrollments = payment.student.enrollment_set.filter(is_active=True)
    for enrollment in enrollments:
        receipt += f"• {enrollment.course_group.name}\n"
        receipt += f"  {enrollment.course_group.monthly_price} DH/mois\n"
    
    receipt += f"""
{'='*32}
Merci pour votre confiance!
{'='*32}
"""
    
    return receipt


# ==================== NOTIFICATIONS ====================

def send_payment_reminder_sms(student, amount: Decimal) -> bool:
    """
    Envoie un SMS de rappel de paiement (à intégrer avec API SMS)
    """
    message = f"""
Bonjour,
Rappel : Un montant de {amount} DH reste à régler pour {student.name}.
École de Soutien Scolaire
    """.strip()
    
    # TODO: Intégrer avec une API SMS (Twilio, etc.)
    print(f"SMS envoyé à {student.parent_contact}: {message}")
    
    return True


def generate_whatsapp_link(phone: str, receipt_text: str) -> str:
    """
    Génère un lien WhatsApp Web avec le reçu pré-rempli
    """
    import urllib.parse
    
    # Nettoyer le numéro (enlever espaces, tirets)
    clean_phone = phone.replace(' ', '').replace('-', '').replace('+', '')
    
    # Encoder le message
    encoded_text = urllib.parse.quote(receipt_text)
    
    # Générer le lien
    whatsapp_link = f"https://wa.me/{clean_phone}?text={encoded_text}"
    
    return whatsapp_link


# ==================== VALIDATION ====================

def validate_payment_amount(student, amount: Decimal, month_date: date) -> Dict:
    """
    Valide qu'un montant de paiement est cohérent
    
    Returns:
        {'valid': bool, 'message': str, 'suggestion': Decimal}
    """
    required = calculate_student_monthly_total(student)
    status = get_student_payment_status(student, month_date)
    
    if amount <= 0:
        return {
            'valid': False,
            'message': "Le montant doit être supérieur à 0",
            'suggestion': required
        }
    
    if amount > (status['remaining'] * Decimal('1.5')):  # 50% de marge
        return {
            'valid': False,
            'message': f"Le montant semble trop élevé. Reste à payer : {status['remaining']} DH",
            'suggestion': status['remaining']
        }
    
    return {
        'valid': True,
        'message': "Montant valide",
        'suggestion': required
    }