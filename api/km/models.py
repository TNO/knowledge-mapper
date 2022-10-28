from django.db import models

# Create your models here.


class KnowledgeBase(models.Model):
    kb_id = models.CharField(max_length=512)
    name = models.CharField(max_length=512)
    description = models.CharField(max_length=512)
