import datetime
from django import template

register = template.Library()


@register.filter
def replace(value, arg):
    """  Replacing filter
    Use {{ "someText"|replace:"a|b" }}
    """
    if len(arg.split('|')) != 2:
        return value

    what, to = arg.split('|')
    return value.replace(what, to)


@register.filter
def number_with_suffix(value):
    """ Add the correct suffix for a number
    Use {{ number|number_with_suffix }}
    """
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


@register.filter
def seconds_to_datetime(seconds):
    return str(datetime.timedelta(seconds=seconds))
