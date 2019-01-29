from rest_framework.viewsets import ReadOnlyModelViewSet

from tasking.models import ModelTask
from tasking.serializers import TaskSerializerMonitorExtend


class TaskViewSetMonitor(ReadOnlyModelViewSet):
    queryset = ModelTask.objects.all()
    serializer_class = TaskSerializerMonitorExtend
    # filter_class = BookTaskFilter
