"""
Custom template filters for currency formatting
"""
from django import template
from decimal import Decimal

register = template.Library()


@register.filter(name='currency')
def currency(value):
    """
    Format a number as Russian Ruble with Russian formatting.
    - Thousands separator: space
    - Decimal separator: comma
    - Currency symbol: ₽

    Example: 1000000.50 → "1 000 000,50 ₽"
    """
    if value is None or value == '':
        return '—'

    try:
        # Convert to Decimal for precision
        if isinstance(value, str):
            value = Decimal(value)
        elif not isinstance(value, Decimal):
            value = Decimal(str(value))

        # Format with 2 decimal places
        formatted = f"{value:,.2f}"

        # Replace comma with temporary marker
        formatted = formatted.replace(',', '|')

        # Replace dot with comma (Russian decimal separator)
        formatted = formatted.replace('.', ',')

        # Replace marker with space (Russian thousands separator)
        formatted = formatted.replace('|', ' ')

        # Add Ruble symbol
        return f"{formatted} ₽"

    except (ValueError, TypeError, ArithmeticError):
        return str(value)


@register.filter(name='currency_short')
def currency_short(value):
    """
    Format currency in short form for tables/cards.
    Abbreviates millions/thousands.

    Example: 1500000 → "1,5 млн ₽"
    """
    if value is None or value == '':
        return '—'

    try:
        if isinstance(value, str):
            value = Decimal(value)
        elif not isinstance(value, Decimal):
            value = Decimal(str(value))

        if value >= 1_000_000:
            # Millions
            short = value / Decimal('1000000')
            formatted = f"{short:.1f}".replace('.', ',')
            return f"{formatted} млн ₽"
        elif value >= 1_000:
            # Thousands
            short = value / Decimal('1000')
            formatted = f"{short:.1f}".replace('.', ',')
            return f"{formatted} тыс ₽"
        else:
            # Less than 1000, show full amount
            formatted = f"{value:,.2f}".replace(',', ' ').replace('.', ',')
            return f"{formatted} ₽"

    except (ValueError, TypeError, ArithmeticError):
        return str(value)
