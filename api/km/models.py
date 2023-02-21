from django.db import models

# Create your models here.


class KnowledgeBase(models.Model):
    id_url = models.CharField(max_length=512, unique=True)
    name = models.CharField(max_length=512)
    description = models.CharField(max_length=512)


MAPPING_TYPES = (("StaticTable", "StaticTable"),)


class MappingRule(models.Model):
    """
    In case of StaticTable, the `data` field is an array with all bindings. In
    the future, SQL rules can be added, and `data` will contain connection
    details and queries to produce the bindings
    """

    type = models.CharField(max_length=16, choices=MAPPING_TYPES)
    data = models.JSONField(null=True)


KI_TYPES = (
    ("ASK", "AskKnowledgeInteraction"),
    ("ANSWER", "AnswerKnowledgeInteraction"),
    ("POST", "PostKnowledgeInteraction"),
    ("REACT", "ReactKnowledgeInteraction"),
)


class DataSource(models.Model):
    name = models.CharField(max_length=512)
    ki_id = models.CharField(max_length=512, unique=True)
    ki_type = models.CharField(max_length=6, choices=KI_TYPES)

    kb = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE)
    mapping_rule = models.ForeignKey(MappingRule, on_delete=models.PROTECT)

    prefixes = models.JSONField(blank=True)
    pattern_1 = models.TextField()
    pattern_2 = models.TextField(blank=True, null=True)
