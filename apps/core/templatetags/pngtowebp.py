from django import template

register = template.Library()


def pngtowebp(path):
    l = path.split('/')
    l[-2] = l[-2] + '.webp'
    l[-1] = l[-1][:-4] + '.webp'
    return '/'.join(l)


@register.filter
def pngorwebpurl(filefield):
    if filefield.storage.exists(pngtowebp(filefield.file.name)):
        return pngtowebp(filefield.url)
    else:
        return filefield.url
