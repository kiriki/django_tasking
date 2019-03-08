import logging
import time

from celery import shared_task, Task

from tasking.models import ModelTask

log = logging.getLogger(__name__)


class CallbackTaskNew(Task):
    ModelTaskClz = ModelTask

    @property
    def task_model(self):
        try:
            return self.ModelTaskClz.objects.get(id=self.model_task_id)
        except self.ModelTaskClz.DoesNotExist:
            print('self.ModelTaskClz.DoesNotExist')
            raise

    def run(self, *args, **kwargs):
        print('run CallbackTask')

    def do_sync_task(self, source='caller'):
        """
        Синхронизация статуса ModelTask с задачей Celery ()
        Вызывается после окончания фактического выполнения задачи, а также
        в процессе при полученни новой порции данных внутри on_progress
        """
        # print("run 'do_sync_task' for '{}' on '{}'".format(task_id, source))

        try:
            self.task_model.sync(self.request.id)
        except self.ModelTaskClz.DoesNotExist as e:
            log.error('can\'t sync - {model}.DoesNotExist')
            log.exception(e)
        except Exception as e:
            print(e)

    def on_success(self, retval, task_id, args, kwargs):
        log.info('on_success')
        self.do_sync_task(source='on_success')

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        log.error('on_failure', einfo)
        self.do_sync_task(source='on_fail')


@shared_task(bind=True, base=CallbackTaskNew)
def test_task(self, task_id, arg=None, steps=10, **kwargs):
    print('Executing task id {0.id}, args: {0.args!r} kwargs: {0.kwargs!r}'.format(self.request))

    self.model_task_id = task_id

    k = 0
    total = steps
    while k < total:
        k += 1
        time.sleep(3)

        log.info(f'long running task {k}')

        self.update_state(state='PROGRESS', meta={'current': k, 'total': total})
        self.do_sync_task(source='on_prorgess')

    return k
