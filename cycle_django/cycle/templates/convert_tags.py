from django import template

register = template.Library()

@register.filter()
def add_table(value: str):
    """ Add double quotes to a string value """
    return f'<th>{value}</th>'