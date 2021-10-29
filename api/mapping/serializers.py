from rest_framework import serializers
from drf_dynamic_fields import DynamicFieldsMixin
from django.contrib.auth.models import User
from data.models import (
    Concept,
    Vocabulary,
    ConceptRelationship,
    ConceptAncestor,
    ConceptClass,
    ConceptSynonym,
    Domain,
    DrugStrength,
) 
from mapping.models import (
    ScanReportField, 
    ScanReportValue,
    ScanReport,
    ScanReportTable,
    ScanReportConcept,
    Mapping,
    ClassificationSystem,
    DataDictionary,
    Document,
    DocumentFile,
    DataPartner,
    OmopField,
    OmopTable,
    StructuralMappingRule,
    Source,
    DocumentType,
    )

from .services_rules import get_mapping_rules_json,get_mapping_rules_list

class ConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concept
        fields = '__all__'

class VocabularySerializer(serializers.ModelSerializer):
    class Meta:
        model=Vocabulary
        fields='__all__'
        
class ConceptRelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model=ConceptRelationship
        fields='__all__'
        
class ConceptAncestorSerializer(serializers.ModelSerializer):
    class Meta:
        model=ConceptAncestor
        fields='__all__'      
                  
class ConceptClassSerializer(serializers.ModelSerializer):
    class Meta:
        model=ConceptClass
        fields='__all__'                        

class ConceptSynonymSerializer(serializers.ModelSerializer):
    class Meta:
        model=ConceptSynonym
        fields='__all__'     
                           
class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model=Domain
        fields='__all__'  
              
class DrugStrengthSerializer(serializers.ModelSerializer):
    class Meta:
        model=DrugStrength
        fields='__all__'  
        
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id','username')
        
class ScanReportSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=ScanReport
        fields='__all__'        

class ScanReportTableSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=ScanReportTable
        fields='__all__'        

class ScanReportFieldSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    name=serializers.CharField(max_length=512, allow_blank=True, trim_whitespace=False)
    description_column=serializers.CharField(max_length=512, allow_blank=True, trim_whitespace=False)
    class Meta:
        model=ScanReportField
        fields='__all__' 

class ScanReportValueSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    value=serializers.CharField(max_length=128, allow_blank=True, trim_whitespace=False)
    class Meta:
        model=ScanReportValue
        fields='__all__'        

class ScanReportConceptSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=ScanReportConcept
        fields='__all__'        
        
class MappingSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=Mapping
        fields='__all__'      

class ClassificationSystemSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=ClassificationSystem
        fields='__all__'               

class DataDictionarySerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=DataDictionary
        fields='__all__'               

class DocumentSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=Document
        fields='__all__'               

class DocumentFileSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=DocumentFile
        fields='__all__'               

class DataPartnerSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model=DataPartner
        fields='__all__'               

class OmopFieldSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model=OmopField
        fields='__all__'               

class OmopTableSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=OmopTable
        fields='__all__'               

class StructuralMappingRuleSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=StructuralMappingRule
        fields='__all__' 

class GetRulesJSON(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=ScanReport
        fields='__all__'

    def to_representation(self, scan_report):
        qs = StructuralMappingRule.objects.filter(scan_report=scan_report)
        rules = get_mapping_rules_json(qs)
        return rules

class GetRulesList(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=ScanReport
        fields='__all__'

    def to_representation(self, scan_report):
        qs = StructuralMappingRule.objects.filter(scan_report=scan_report)
        rules = get_mapping_rules_list(qs)
        for rule in rules:
            rule['destination_table'] = {
                'id':int(str(rule['destination_table'])),
                'name':rule['destination_table'].table
            }
            
            rule['destination_field'] = {
                'id':int(str(rule['destination_field'])),
                'name':rule['destination_field'].field
            }
            
            rule['source_table'] = {
                'id':int(str(rule['source_table'])),
                'name':rule['source_table'].name
            }
            
            rule['source_field'] = {
                'id':int(str(rule['source_field'])),
                'name':rule['source_field'].name
            }

        
        return rules


class SourceSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=Source
        fields='__all__'         
        
class DocumentTypeSerializer(DynamicFieldsMixin,serializers.ModelSerializer):
    class Meta:
        model=DocumentType
        fields='__all__'                 
