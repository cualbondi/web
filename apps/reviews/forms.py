from django import forms
from django_comments.forms import CommentForm
from .models import Review
from django.conf import settings
from django.utils.translation import ungettext, ugettext, ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_str
from django.utils import timezone


DEFAULT_REVIEW_RATING_CHOICES = (
    ('1', _('Terrible')),
    ('2', _('Poor')),
    ('3', _('Average')),
    ('4', _('Very Good')),
    ('5', _('Excellent')),
)
REVIEW_RATING_CHOICES = getattr(settings, 'REVIEW_RATING_CHOICES', DEFAULT_REVIEW_RATING_CHOICES)

class ReviewForm(CommentForm):
    # remove following two fields from parent class
    email = None
    url = None

    rating_choices = (("", _("Select a rating")),) + REVIEW_RATING_CHOICES
    rating = forms.IntegerField(label=_('Rating'),
                                widget=forms.Select(choices=rating_choices, attrs={'class':'star-rating'}),
                                required=True)

    class Media:
        minified = '' if settings.DEBUG else '.min'
        css = {
            'all': ('reviews/css/star-rating{}.css'.format(minified),)
            }
        js = ('reviews/js/star-rating{}.js'.format(minified),)

    def get_comment_create_data(self, site_id=None):
        return dict(
            content_type=ContentType.objects.get_for_model(self.target_object),
            object_pk=force_str(self.target_object._get_pk_val()),
            user_name=self.cleaned_data["name"],
            comment=self.cleaned_data["comment"],
            submit_date=timezone.now(),
            site_id=site_id or getattr(settings, "SITE_ID", None),
            is_public=True,
            is_removed=False,
            rating=self.cleaned_data['rating'],
        )
