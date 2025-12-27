from django import forms
from .models import Session, CourseGroup, Student, Enrollment


class StudentForm(forms.ModelForm):
    """Form for creating and editing students"""
    
    class Meta:
        model = Student
        fields = ['name', 'phone', 'parent_name', 'parent_contact', 'date_of_birth', 'address', 'is_active', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom complet de l\'élève'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Téléphone de l\'élève',
                'type': 'tel'
            }),
            'parent_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du parent/tuteur'
            }),
            'parent_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Téléphone du parent',
                'type': 'tel',
                'required': True
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Adresse',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Notes supplémentaires',
                'rows': 3
            }),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Le nom de l\'élève est requis')
        return name
    
    def clean_parent_contact(self):
        phone = self.cleaned_data.get('parent_contact', '').strip()
        if not phone:
            raise forms.ValidationError('Le téléphone du parent est requis')
        return phone


class EnrollmentForm(forms.ModelForm):
    """Form for enrolling students in course groups"""
    
    course_group = forms.ModelChoiceField(
        queryset=CourseGroup.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Groupe de cours'
    )
    
    class Meta:
        model = Enrollment
        fields = ['course_group', 'is_active']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['group', 'date', 'start_time', 'end_time', 'status']
        widgets = {
            'group': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned = super().clean()
        # Let model's clean handle room conflicts; just return cleaned data
        return cleaned
