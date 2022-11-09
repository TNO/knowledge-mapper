from django.db import models

# Create your models here.


class KnowledgeBase(models.Model):
    id_url = models.CharField(max_length=512, unique=True)
    name = models.CharField(max_length=512)
    description = models.CharField(max_length=512)


KI_TYPES = (
    ("ASK", "AskKnowledgeInteraction"),
    ("ANSWER", "AnswerKnowledgeInteraction"),
    ("POST", "PostKnowledgeInteraction"),
    ("REACT", "ReactKnowledgeInteraction"),
)


class KnowledgeInteraction(models.Model):
    id_url = models.CharField(max_length=512, unique=True)
    name = models.CharField(max_length=512)

    kb = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE)

    type = models.CharField(max_length=6, choices=KI_TYPES)

    prefixes = models.JSONField(blank=True)
    pattern_1 = models.TextField()
    pattern_2 = models.TextField(blank=True, null=True)
