import logging

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.db.models import CharField
from model_utils import Choices
from model_utils.fields import StatusField
from django.core.exceptions import ValidationError

log = logging.getLogger(__name__)

ACTION_BASE_TEST = 'base_test'  # -> 'tasking.tasks.test_task'
TASK_BASE_TEST = 'tasking.tasks.test_task'


def validate_only_one_instance(obj):
    model = obj.__class__
    if (model.objects.count() > 0 and
            obj.id != model.objects.get().id):
        raise ValidationError(f'Can only create 1 {model.__name__} instance')


class ModelTask(models.Model):
    source_model = None
    do_run = False

    tasks: dict[str, str] = {}
    tasks_base = {
        ACTION_BASE_TEST: TASK_BASE_TEST,
        # **tasks_dict,
    }

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    action = CharField(max_length=100)
    celery_task = CharField(max_length=100)

    STATUS = Choices('created', 'start', 'active', 'done', 'del')
    status = StatusField()
    task_result = models.JSONField(default=dict, blank=True)

    closed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, null=True)

    def __init__(self, *args, do_run=False, queryset=None, params=None, **kwargs):
        self.do_run = do_run
        self.res = None
        self.task_params = params or {}
        if queryset is not None:
            self.queryset = queryset

        self.tasks.update(self.tasks_base)
        # self.tasks = {**self._actions, **self.tasks_dict}
        if params:
            self.task_params = params

        super().__init__(*args, **kwargs)

        # self._meta.get_field('action').choices = Choices(*self.tasks.keys())

        self.celery_task = self.tasks.get(self.action)
        assert self.action is not None
        # assert self.celery_task is not None, f"action = {self.action}, tasks = {self.tasks}, class = {self.__class__.__name__}"

    def __str__(self):
        return f"Model task '{self.action}', id={self.pk}"

    class Meta:
        ordering = ['created']

    def get_task_params(self):
        # return dict(kwargs=({'blog_task_id': self.id, 'task_name': self.task_name}))
        # return dict(kwargs=dict(name=self.collection.display_name, task_id=self.id))
        return dict(kwargs={'object_id': self.object_id,
                            'task_id': self.id,
                            'action': self.action,
                            **self.task_params,
                            })

    def run_task(self):
        """
        Запуск задачи
        В норме запускается при первом сохранении модели, если установлен флаг 'do_run'
        проверки, что задача такого типа исполняется в единственном экземпляре
        """
        print('do run_task')
        from celery import current_app

        log.info(f'run_task: {self.celery_task}')

        # task = self.get_celery_task()
        # log.info(f'run_task: {task.__name__}')

        params = self.get_task_params()

        # self.res = task.apply_async(**params)
        self.res = current_app.send_task(self.celery_task, **params)

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
            raise ValidationError(f'Only one open instance for this action, got {a.count()} exists')

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
