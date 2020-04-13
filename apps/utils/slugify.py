from django.template.defaultfilters import slugify as djslugify
from unidecode import unidecode


def slugify(value: str) -> str:
    return djslugify(unidecode(value))
