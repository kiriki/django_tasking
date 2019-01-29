from django.conf.urls import include
from django.urls import path
from rest_framework_extensions.routers import ExtendedSimpleRouter

from tasking import views

router = ExtendedSimpleRouter()

router.register('', views.TaskViewSetMonitor)  # Для мониторинга задач без привязки к модели

urlpatterns = [
    path('', include(router.urls)),
]
