from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from django.core.exceptions import ValidationError

class Room(models.Model):
    """Salle de classe"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Nom de la salle")
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Capacité"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    class Meta:
        verbose_name = "Salle"
        verbose_name_plural = "Salles"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.capacity} places)"


class Teacher(models.Model):
    """Professeur"""
    name = models.CharField(max_length=100, verbose_name="Nom complet")
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")
    hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Tarif horaire (DH)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Professeur"
        verbose_name_plural = "Professeurs"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.hourly_rate} DH/h)"


class CourseGroup(models.Model):
    """Groupe de cours"""
    DAYS_CHOICES = [
        ('MON', 'Lundi'),
        ('TUE', 'Mardi'),
        ('WED', 'Mercredi'),
        ('THU', 'Jeudi'),
        ('FRI', 'Vendredi'),
        ('SAT', 'Samedi'),
        ('SUN', 'Dimanche'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nom du groupe")
    subject = models.CharField(max_length=100, verbose_name="Matière")
    level = models.CharField(max_length=50, verbose_name="Niveau")
    
    monthly_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Prix mensuel (DH)"
    )
    
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name='course_groups',
        verbose_name="Professeur"
    )
    
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='course_groups',
        verbose_name="Salle"
    )
    
    # Horaire
    schedule_day = models.CharField(
        max_length=3,
        choices=DAYS_CHOICES,
        verbose_name="Jour"
    )
    start_time = models.TimeField(verbose_name="Heure de début")
    end_time = models.TimeField(verbose_name="Heure de fin")
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Groupe de cours"
        verbose_name_plural = "Groupes de cours"
        ordering = ['schedule_day', 'start_time', 'name']
        # Éviter les conflits de salle
        unique_together = [['room', 'schedule_day', 'start_time']]
    
    def __str__(self):
        return f"{self.name} - {self.get_schedule_day_display()} {self.start_time.strftime('%H:%M')}"
    
    def duration_hours(self):
        """Calcule la durée en heures"""
        from datetime import datetime, timedelta
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        duration = end - start
        return duration.total_seconds() / 3600
    
    def check_room_conflict(self):
        """Vérifie s'il y a un conflit de salle"""
        conflicts = CourseGroup.objects.filter(
            room=self.room,
            schedule_day=self.schedule_day,
            is_active=True
        ).exclude(pk=self.pk)
        
        for course in conflicts:
            # Vérifier chevauchement horaire
            if (self.start_time < course.end_time and 
                self.end_time > course.start_time):
                return True, course
        return False, None


class Student(models.Model):
    """Élève"""
    name = models.CharField(max_length=100, verbose_name="Nom complet")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone élève")
    parent_contact = models.CharField(max_length=20, verbose_name="Téléphone parent")
    parent_name = models.CharField(max_length=100, blank=True, verbose_name="Nom du parent")
    
    address = models.TextField(blank=True, verbose_name="Adresse")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    
    # Relation Many-to-Many avec les groupes
    enrollments = models.ManyToManyField(
        CourseGroup,
        through='Enrollment',
        related_name='students',
        verbose_name="Groupes inscrits"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def total_monthly_fees(self):
        """Calcule le total des frais mensuels"""
        active_enrollments = self.enrollment_set.filter(is_active=True)
        # Ensure Decimal result even when no enrollments
        total = sum((e.course_group.monthly_price for e in active_enrollments), Decimal('0.00'))
        return total
     
    def payment_status(self):
        current_month = timezone.now().date().replace(day=1)

        required = self.total_monthly_fees()

        paid = (
            self.payments
            .filter(month_covered=current_month, status='PAID')
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0')
        )

        if required == 0:
            return 'OK'  # No courses = nothing to pay

        if paid >= required:
            return 'OK'
        elif paid > 0:
            return 'PARTIAL'
        return 'UNPAID'



class Enrollment(models.Model):
    """Inscription d'un élève dans un groupe (table intermédiaire)"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course_group = models.ForeignKey(CourseGroup, on_delete=models.CASCADE)
    enrolled_date = models.DateField(auto_now_add=True, verbose_name="Date d'inscription")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        unique_together = [['student', 'course_group']]
    
    def __str__(self):
        return f"{self.student.name} → {self.course_group.name}"


class Payment(models.Model):
    """Paiement"""
    STATUS_CHOICES = [
        ('PAID', 'Payé'),
        ('PENDING', 'En attente'),
        ('CANCELLED', 'Annulé'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Espèces'),
        ('TRANSFER', 'Virement'),
        ('CHECK', 'Chèque'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Élève"
    )
    
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant (DH)"
    )
    
    payment_date = models.DateField(verbose_name="Date de paiement")
    month_covered = models.DateField(
        verbose_name="Mois couvert",
        help_text="Premier jour du mois couvert par ce paiement"
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PAID',
        verbose_name="Statut"
    )
    
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default='CASH',
        verbose_name="Mode de paiement"
    )
    
    receipt_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="N° de reçu"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, blank=True, verbose_name="Créé par")
    
    # Verrou numérique : empêcher modification
    is_locked = models.BooleanField(default=False, verbose_name="Verrouillé")
    
    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-payment_date', '-created_at']
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=['student', 'month_covered'],
        #         condition=models.Q(status='PAID'),
        #         name='unique_paid_payment_per_month'
        #     )
        # ]
    
    def __str__(self):
        return f"Reçu {self.receipt_number} - {self.student.name} - {self.amount} DH"
    
    def save(self, *args, **kwargs):
        # Générer automatiquement le numéro de reçu
        if self.month_covered:
            self.month_covered = self.month_covered.replace(day=1)

        if not self.receipt_number:
            from django.utils import timezone
            year = timezone.now().year
            last_payment = Payment.objects.filter(
                receipt_number__startswith=f"REC{year}"
            ).order_by('-receipt_number').first()
            
            if last_payment:
                last_num = int(last_payment.receipt_number[-4:])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.receipt_number = f"REC{year}{new_num:04d}"
        
        super().save(*args, **kwargs)


class Attendance(models.Model):
    """Présence aux cours"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="Élève")
    course_group = models.ForeignKey(CourseGroup, on_delete=models.CASCADE, verbose_name="Groupe")
    date = models.DateField(verbose_name="Date")
    is_present = models.BooleanField(default=True, verbose_name="Présent")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Présence"
        verbose_name_plural = "Présences"
        unique_together = [['student', 'course_group', 'date']]
        ordering = ['-date']
    
    def __str__(self):
        status = "✓" if self.is_present else "✗"
        return f"{status} {self.student.name} - {self.course_group.name} - {self.date}"


class Session(models.Model):
    """Instance of a group meeting (used for scheduling & payroll)

    Business rules:
    - The session's room (inferred from `group.room`) cannot be double-booked
      at overlapping times on the same date.
    """
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('DONE', 'Done'),
        ('CANCELLED', 'Cancelled'),
    ]

    group = models.ForeignKey(CourseGroup, on_delete=models.CASCADE, related_name='sessions')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    # Optional per-session room override. If null, uses group.room
    room = models.ForeignKey(
        Room,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name='Salle (override)'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PLANNED')
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'
        ordering = ['-date', 'start_time']
        indexes = [
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.group.name} - {self.date} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    def clean(self):
        """Validate that the room is not double-booked for overlapping times on same date."""
        # ensure times make sense
        if self.end_time <= self.start_time:
            raise ValidationError('End time must be after start time')
        # effective room: allow per-session override (new `room` field) in future
        room = getattr(self, 'room', None) or self.group.room
        # find sessions on same date
        conflicts = Session.objects.filter(date=self.date)
        if self.pk:
            conflicts = conflicts.exclude(pk=self.pk)

        for s in conflicts:
            # determine effective room for other session
            other_room = getattr(s, 'room', None) or s.group.room
            if other_room != room:
                continue
            # overlap check: start < s.end and end > s.start
            if (self.start_time < s.end_time and self.end_time > s.start_time):
                raise ValidationError(f"Room {room.name} is already booked by {s.group.name} {s.start_time}-{s.end_time}")

    def save(self, *args, **kwargs):
        # run full_clean to enforce clean() on save
        self.full_clean()
        super().save(*args, **kwargs)

    def duration_hours(self):
        from datetime import datetime
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        return (end - start).total_seconds() / 3600


class SessionException(models.Model):
    """Per-date exception / override for a CourseGroup's regular session.

    Use this to cancel a particular occurrence or to move it to another time/room.
    """
    course_group = models.ForeignKey(CourseGroup, on_delete=models.CASCADE, related_name='exceptions')
    date = models.DateField()

    # If True, this occurrence is cancelled (no session will be generated)
    cancelled = models.BooleanField(default=False)

    # Optional overrides — if provided they replace the group's default for that date
    override_room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.PROTECT)
    override_start_time = models.TimeField(null=True, blank=True)
    override_end_time = models.TimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['course_group', 'date']]
        verbose_name = 'Exception de session'
        verbose_name_plural = 'Exceptions de sessions'
        ordering = ['-date']

    def __str__(self):
        flag = 'CANCELLED' if self.cancelled else 'OVERRIDE' if (self.override_start_time or self.override_end_time or self.override_room) else 'NOTE'
        return f"{self.course_group.name} - {self.date} ({flag})"

    def effective_room(self):
        return self.override_room or self.course_group.room

    def effective_start(self):
        return self.override_start_time or self.course_group.start_time

    def effective_end(self):
        return self.override_end_time or self.course_group.end_time