import logging

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db import models
from django.db.models import CharField

if connection.vendor == 'postgresql':
    from django.contrib.postgres.fields import JSONField
else:
    from jsonfield import JSONField

from model_utils import Choices
from model_utils.fields import StatusField
from rest_framework.exceptions import ValidationError  # from django.core.exceptions import ValidationError

log = logging.getLogger(__name__)

ACTION_BASE_TEST = 'base_test'  # -> 'tasking.tasks.test_task'
TASK_BASE_TEST = 'tasking.tasks.test_task'


def validate_only_one_instance(obj):
    model = obj.__class__
    if (model.objects.count() > 0 and
            obj.id != model.objects.get().id):
        raise ValidationError(f'Can only create 1 {model.__name_} instance')


class ModelTask(models.Model):
    STATUS = Choices('created', 'start', 'active', 'done', 'del')

    tasks_dict = {}
    _actions = {
        ACTION_BASE_TEST: TASK_BASE_TEST,
        # 'init': 'tumblr.tasks.init_blog',
    }

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    action = CharField(max_length=100)
    celery_task = CharField(max_length=100)

    status = StatusField()
    task_result = JSONField(default=dict, blank=True)

    closed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, null=True)

    do_run = False

    source_model = None

    def __init__(self, *args, do_run=False, queryset=None, **kwargs):
        self.do_run = do_run
        self.res = None
        if queryset:
            self.queryset = queryset

        self._tasks_dict = {**self._actions, **self.tasks_dict}

        self._meta.get_field('action').choices = Choices(*self._tasks_dict.keys())

        super().__init__(*args, **kwargs)

        self.celery_task = self.get_celery_task_name()

    def __str__(self):
        return f"Model task '{self.action}', id={self.pk}"

    class Meta:
        ordering = ['created']

    def get_celery_task_name(self):
        return self._tasks_dict.get(self.action)

    def get_task_params(self):
        # return dict(kwargs=({'blog_task_id': self.id, 'task_name': self.task_name}))
        # return dict(kwargs=dict(name=self.collection.display_name, task_id=self.id))
        return dict(kwargs={'object_id': self.object_id, 'task_id': self.id, 'action': self.action})

    def run_task(self):
        """
        Запуск задачи
        В норме запускается при первом сохранении модели, если установлен флаг 'do_run'
        проверки что задача такого типа исполняется в единственном экземпляре
        """
        print('do run_task')
        from celery import current_app

        task_name = self.get_celery_task_name()
        log.info(f'run_task: {task_name}')

        # task = self.get_celery_task()
        # log.info(f'run_task: {task.__name__}')

        params = self.get_task_params()

        # self.res = task.apply_async(**params)
        self.res = current_app.send_task(task_name, **params)

        self.status = 'start'
        self.save()

    def sync(self, celery_id):
        """
        Обновление состояния задачи и всех полей на основе статуса задания celery
        когда обновлять статус закрытия у задач? момент синхронизации состояний задания celery и данной задачи
        :param celery_id: id задачи celery, строка вида 'ee35a4a7-b580-4187-9db1-436f9574738d'
        """
        from celery.result import AsyncResult
        from celery.states import READY_STATES

        assert celery_id is not None

        result = AsyncResult(celery_id)
        self.closed = result.status in READY_STATES
        if self.closed:
            self.status = 'done'

        if result.result:
            self.task_result = result.result

        self.save()

    def clean(self):
        return
        model = self.__class__
        a = model.objects.filter(task_name=self.task_name,
                                 status__in=['created', 'start'],
                                 closed=False)

        if a.exists() & self._state.adding:
            raise ValidationError("Only one open instance for this action, got {} exists".format(a.count()))

    def save(self, *args, **kwargs):
        self.full_clean(exclude=['collection'])

        is_created = not self.pk or kwargs.get('force_insert', False)
        super().save(*args, **kwargs)

        if is_created and self.do_run:
            self.run_task()

# @receiver(models.signals.post_save, sender=ModelTask)
# def execute_after_save(sender, instance, created, *args, **kwargs):
#     if created and instance.do_run:
#         instance.run_task()
