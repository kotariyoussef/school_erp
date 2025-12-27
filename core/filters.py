import django_filters
from django import forms
from django.db.models import Q

from .models import Student, CourseGroup, Teacher, Room, Session


class StudentFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method='filter_q', 
        label='Recherche', 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Nom, téléphone ou parent...'
        })
    )
    
    payment_status = django_filters.ChoiceFilter(
        method='filter_payment_status',
        label='Statut de paiement',
        choices=[
            ('', '-- Tous les statuts --'),
            ('ok', '✓ À jour'),
            ('partial', '⚠ Partiel'),
            ('unpaid', '✗ Impayé'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    course_group = django_filters.ModelChoiceFilter(
        field_name='enrollments',
        queryset=CourseGroup.objects.filter(is_active=True),
        label='Groupe de cours',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='-- Tous les groupes --'
    )
    
    is_active = django_filters.BooleanFilter(
        field_name='is_active', 
        label='Actif', 
        widget=forms.Select(
            choices=[('', 'Tous'), (True, 'Actifs'), (False, 'Inactifs')],
            attrs={'class': 'form-select'}
        )
    )

    class Meta:
        model = Student
        fields = ['q', 'payment_status', 'course_group', 'is_active']

    def filter_q(self, queryset, name, value):
        """Search across name, parent name, and contact info"""
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | 
            Q(parent_contact__icontains=value) | 
            Q(parent_name__icontains=value) |
            Q(phone__icontains=value)
        )
    
    def filter_payment_status(self, queryset, name, value):
        """Filter by payment status (requires calculating status for each student)"""
        if not value:
            return queryset
        
        # We need to filter in Python since payment_status is a method
        # Get all students and filter by their payment status
        student_ids = []
        for student in queryset:
            status = student.payment_status()
            if value == 'ok' and status == 'OK':
                student_ids.append(student.id)
            elif value == 'partial' and status == 'PARTIAL':
                student_ids.append(student.id)
            elif value == 'unpaid' and status == 'UNPAID':
                student_ids.append(student.id)
        
        return queryset.filter(id__in=student_ids)


class CourseGroupFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains', label='Nom', widget=forms.TextInput(attrs={'class':'form-control'}))
    teacher = django_filters.ModelChoiceFilter(queryset=Teacher.objects.all(), label='Professeur', widget=forms.Select(attrs={'class':'form-select'}))
    room = django_filters.ModelChoiceFilter(queryset=Room.objects.all(), label='Salle', widget=forms.Select(attrs={'class':'form-select'}))

    class Meta:
        model = CourseGroup
        fields = ['name', 'teacher', 'room']


class TeacherFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains', label='Nom', widget=forms.TextInput(attrs={'class':'form-control'}))
    min_rate = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='gte', label='Min tarif', widget=forms.NumberInput(attrs={'class':'form-control'}))
    max_rate = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='lte', label='Max tarif', widget=forms.NumberInput(attrs={'class':'form-control'}))

    class Meta:
        model = Teacher
        fields = ['name', 'min_rate', 'max_rate']


class RoomFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains', label='Nom', widget=forms.TextInput(attrs={'class':'form-control'}))
    min_capacity = django_filters.NumberFilter(field_name='capacity', lookup_expr='gte', label='Min capacité', widget=forms.NumberInput(attrs={'class':'form-control'}))

    class Meta:
        model = Room
        fields = ['name', 'min_capacity']


class SessionFilter(django_filters.FilterSet):
    date_after = django_filters.DateFilter(field_name='date', lookup_expr='gte', label='Date depuis', widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))
    date_before = django_filters.DateFilter(field_name='date', lookup_expr='lte', label='Date jusqu\'à', widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))
    room = django_filters.ModelChoiceFilter(field_name='group__room', queryset=Room.objects.all(), label='Salle', widget=forms.Select(attrs={'class':'form-select'}))
    teacher = django_filters.ModelChoiceFilter(field_name='group__teacher', queryset=Teacher.objects.all(), label='Professeur', widget=forms.Select(attrs={'class':'form-select'}))
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact', label='Statut', widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'PLANNED, DONE, CANCELLED'}))

    class Meta:
        model = Session
        fields = ['date_after', 'date_before', 'room', 'teacher', 'status']
