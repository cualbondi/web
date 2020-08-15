from django.db import models
from django_comments.abstracts import CommentAbstractModel

class Review(CommentAbstractModel):
    rating = models.PositiveSmallIntegerField()
