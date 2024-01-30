import datetime
from django import template

from my_base import Logging

register = template.Library()
logger = Logging.setup_logger(__name__)


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
    if isinstance(seconds, str):
        return seconds
    return str(datetime.timedelta(seconds=seconds))


@register.filter
def convert_duration_hms(duration):
    """ Convert a timedelta from a models.DurationField to hours:mm:ss"""
    if duration is None:
        return ''
    hours, remainder = divmod(duration.seconds, 3600)
    hours += duration.days * 24
    minutes, seconds = divmod(remainder, 60)

    return f'{hours}:{minutes:02}:{seconds:02}'
