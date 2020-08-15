from django import template
from django_comments.templatetags.comments import BaseCommentNode, RenderCommentListNode, RenderCommentFormNode
from django.db.models import Avg
from django.template.loader import render_to_string

register = template.Library()


class RatingAvgNode(BaseCommentNode):
    """Insert a count of reviews into the context."""

    def get_context_value_from_queryset(self, context, qs):
        return qs.aggregate(Avg('rating'))['rating__avg']


@register.tag
def get_rating_avg(parser, token):
    """
    Gets the review rating average for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.
    Syntax::
        {% get_rating_avg for [object] as [varname]  %}
        {% get_rating_avg for [app].[model] [object_id] as [varname]  %}
    Example usage::
        {% get_rating_avg for event as review_count %}
        {% get_rating_avg for calendar.event event.id as review_count %}
        {% get_rating_avg for calendar.event 17 as review_count %}
    """
    return RatingAvgNode.handle_token(parser, token)


class RenderReviewAggregateNode(RenderCommentListNode):
    """Render the review aggregate directly"""

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "reviews/%s/%s/aggregate.html" % (ctype.app_label, ctype.model),
                "reviews/%s/aggregate.html" % ctype.app_label,
                "reviews/aggregate.html"
            ]
            qs = self.get_queryset(context)
            context_dict = context.flatten()
            context_dict['count'] = qs.count()
            context_dict['avg'] = qs.aggregate(v=Avg('rating'))['v']
            liststr = render_to_string(template_search_list, context_dict)
            return liststr
        else:
            return ''


@register.tag
def render_review_aggregate(parser, token):
    return RenderReviewAggregateNode.handle_token(parser, token)


class RenderReviewListNode(RenderCommentListNode):
    """Render the review list directly"""

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "reviews/%s/%s/list.html" % (ctype.app_label, ctype.model),
                "reviews/%s/list.html" % ctype.app_label,
                "reviews/list.html"
            ]
            qs = self.get_queryset(context)
            context_dict = context.flatten()
            context_dict['review_list'] = self.get_context_value_from_queryset(context, qs)
            liststr = render_to_string(template_search_list, context_dict)
            return liststr
        else:
            return ''

    def get_context_value_from_queryset(self, context, qs):
        return qs.order_by('-submit_date')


@register.tag
def render_review_list(parser, token):
    """
    Render the review list (as returned by ``{% get_review_list %}``)
    through the ``reviews/list.html`` template
    Syntax::
        {% render_review_list for [object] %}
        {% render_review_list for [app].[model] [object_id] %}
    Example usage::
        {% render_review_list for event %}
    """
    return RenderReviewListNode.handle_token(parser, token)


class RenderReviewFormNode(RenderCommentFormNode):
    """Render the review form directly"""

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "reviews/%s/%s/form.html" % (ctype.app_label, ctype.model),
                "reviews/%s/form.html" % ctype.app_label,
                "reviews/form.html"
            ]
            context_dict = context.flatten()
            context_dict['form'] = self.get_form(context)
            formstr = render_to_string(template_search_list, context_dict)
            return formstr
        else:
            return ''


@register.tag
def render_review_form(parser, token):
    """
    Render the review form (as returned by ``{% render_review_form %}``) through
    the ``reviews/form.html`` template.
    Syntax::
        {% render_review_form for [object] %}
        {% render_review_form for [app].[model] [object_id] %}
    """
    return RenderReviewFormNode.handle_token(parser, token)
