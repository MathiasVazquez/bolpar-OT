from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SalesOrderViewSet, OrderedItemViewSet,
    PlanningProductionViewSet, ConsumptionInputViewSet, MachineViewSet, MachineStatusLogViewSet,
    EmployeeViewSet,
)

router = DefaultRouter()
router.register(r'orders', SalesOrderViewSet, basename='order')
router.register(r'items', OrderedItemViewSet)
router.register(r'planificacion', PlanningProductionViewSet)
router.register(r'insumos', ConsumptionInputViewSet)
router.register(r'machines', MachineViewSet)
router.register(r'machine-status-logs', MachineStatusLogViewSet)
router.register(r'funcionarios', EmployeeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
