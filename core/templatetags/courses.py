from django import template
from core.models import CourseGroup

register = template.Library()


@register.simple_tag
def load_courses(student=None):
    """
    Usage:
        {% load_courses student as courses %}
        {% load_courses as courses %}
    """
    courses = (
        CourseGroup.objects
        .filter(is_active=True)
        .select_related('teacher', 'room')
    )

    if student:
        enrolled_ids = student.enrollment_set.values_list(
            'course_group_id', flat=True
        )
        courses = courses.exclude(id__in=enrolled_ids)

    return courses.order_by('name')
