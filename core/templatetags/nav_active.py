from django import template
from ..models import CourseGroup, Enrollment

register = template.Library()

@register.simple_tag(takes_context=True)
def active_if(context, *names):
    request = context.get("request")
    if not request or not request.resolver_match:
        return ""

    return "active" if request.resolver_match.url_name in names else ""

@register.simple_tag(takes_context=True)
def active_prefix(context, prefix):
    request = context["request"]
    return "active" if request.resolver_match.url_name.startswith(prefix) else ""



