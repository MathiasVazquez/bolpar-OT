from django import forms
from django.forms import inlineformset_factory
from .models import SalesOrder, OrderedItem, PlanningProduction, ConsumptionInput

class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = '__all__'
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'fecha': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

OrderedItemFormSet = inlineformset_factory(
    SalesOrder, OrderedItem,
    fields=['quantity','created_by','description','discount','estado_op','tax','product_name','list_price'],
    extra=1, can_delete=True
)

PlanningProductionFormSet = inlineformset_factory(
    SalesOrder, PlanningProduction,
    fields=['cant','created_by','fecha','linea','linea_new','observacion','producto'],
    extra=1, can_delete=True
)

ConsumptionInputFormSet = inlineformset_factory(
    SalesOrder, ConsumptionInput,
    fields=['cantidad','created_by','insumo','linea','lote','unidad'],
    extra=1, can_delete=True
)
