from django import template

register = template.Library()

@register.filter
def index(sequence, position):
    """
    Returns item at given index from a list/tuple.
    Usage: {{ my_list|index:0 }}
    """
    try:
        return sequence[position]
    except (IndexError, TypeError):
        return None
