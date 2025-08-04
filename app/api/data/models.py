from django.db import models


class ConceptAncestor(models.Model):
    ancestor_concept_id = models.IntegerField(primary_key=True)
    descendant_concept_id = models.IntegerField()
    min_levels_of_separation = models.IntegerField()
    max_levels_of_separation = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'omop"."concept_ancestor'
        app_label = "data"
        unique_together = (("ancestor_concept_id", "descendant_concept_id"),)


class ConceptClass(models.Model):
    concept_class_id = models.CharField(primary_key=True, max_length=20)
    concept_class_name = models.CharField(max_length=255)
    concept_class_concept_id = models.IntegerField()

    class Meta:
        managed = False
        app_label = "data"
        db_table = 'omop"."concept_class'


class ConceptRelationship(models.Model):
    concept_id_1 = models.IntegerField(
        primary_key=True,
    )
    concept_id_2 = models.IntegerField()
    relationship_id = models.CharField(
        max_length=20,
    )
    valid_start_date = models.DateField()
    valid_end_date = models.DateField()
    invalid_reason = models.CharField(
        max_length=1,
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = 'omop"."concept_relationship'
        app_label = "data"
        unique_together = (("concept_id_1", "concept_id_2", "relationship_id"),)


class ConceptSynonym(models.Model):
    concept_id = models.IntegerField(primary_key=True)
    concept_synonym_name = models.CharField(max_length=1000)
    language_concept_id = models.IntegerField()

    class Meta:
        managed = False
        app_label = "data"
        db_table = 'omop"."concept_synonym'


class Concept(models.Model):
    concept_id = models.IntegerField(
        primary_key=True,
    )
    concept_name = models.CharField(
        max_length=255,
    )
    domain_id = models.CharField(
        max_length=20,
    )
    vocabulary_id = models.CharField(
        max_length=20,
    )
    concept_class_id = models.CharField(
        max_length=20,
    )
    standard_concept = models.CharField(
        max_length=1,
        blank=True,
        null=True,
    )
    concept_code = models.CharField(
        max_length=50,
    )
    valid_start_date = models.DateField()
    valid_end_date = models.DateField()
    invalid_reason = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        managed = False
        app_label = "data"
        db_table = 'omop"."concept'


class Domain(models.Model):
    domain_id = models.CharField(primary_key=True, max_length=20)
    domain_name = models.CharField(max_length=255)
    domain_concept_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'omop"."domain'
        app_label = "data"


class DrugStrength(models.Model):
    drug_concept_id = models.IntegerField(primary_key=True)
    ingredient_concept_id = models.IntegerField()
    amount_value = models.DecimalField(
        max_digits=65535, decimal_places=65535, blank=True, null=True
    )
    amount_unit_concept_id = models.IntegerField(blank=True, null=True)
    numerator_value = models.DecimalField(
        max_digits=65535, decimal_places=65535, blank=True, null=True
    )
    numerator_unit_concept_id = models.IntegerField(blank=True, null=True)
    denominator_value = models.DecimalField(
        max_digits=65535, decimal_places=65535, blank=True, null=True
    )
    denominator_unit_concept_id = models.IntegerField(blank=True, null=True)
    box_size = models.IntegerField(blank=True, null=True)
    valid_start_date = models.DateField()
    valid_end_date = models.DateField()
    invalid_reason = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'omop"."drug_strength'
        app_label = "data"
        unique_together = (("drug_concept_id", "ingredient_concept_id"),)


class Vocabulary(models.Model):
    vocabulary_id = models.CharField(primary_key=True, max_length=20)
    vocabulary_name = models.CharField(max_length=255)
    vocabulary_reference = models.CharField(max_length=255)
    vocabulary_version = models.CharField(max_length=255, blank=True, null=True)
    vocabulary_concept_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'omop"."vocabulary'
        app_label = "data"
