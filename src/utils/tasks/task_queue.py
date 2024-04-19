from queue import Queue
from concurrent.futures import ThreadPoolExecutor, Future

from tasks.task_class import Task
from logging import getLogger, Logger


logger: Logger = getLogger(__name__)


class TaskQueue:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(TaskQueue, cls).__new__(cls)
        return cls.__instance

    @classmethod
    def get_task_queue(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = cls(*args, **kwargs)
        return cls.__instance

    def __init__(self, maxsize: int = 0, max_workers: int = 4, retry_limit: int = 3):
        self.max_workers = max_workers
        self.task_queue = Queue(maxsize=maxsize)
        self.retry_limit = retry_limit
        self.completed_tasks = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def enqueue_task(self, task: Task) -> Future:
        if isinstance(task, Task):
            self.task_queue.put(task)
            future = self.executor.submit(self._worker)
            return future
        else:
            logger.error("Invalid task type")

    def _worker(self):
        while not self.task_queue.empty():
            task: Task = self.task_queue.get()
            if task is None:
                break
            if not task.task_name in self.completed_tasks:
                self.completed_tasks[task.task_name] = {
                    "task_name": task.task_name,
                    "return_value": None,
                    "retries": task.retries,
                    "completed": False,
                    "failed": False,
                }
            return_value = task()
            if not return_value is None:
                self.completed_tasks[task.task_name]["completed"] = True
                self.completed_tasks[task.task_name]["return_value"] = return_value
                self.task_queue.task_done()
                return return_value
            self._resubmit_task(task)
            self.task_queue.task_done()

    def _resubmit_task(self, task: Task):
        if task.retries < self.retry_limit:
            task.retries += 1
            self.completed_tasks[task.task_name]["retries"] = task.retries
            self.enqueue_task(task)
        else:
            self.completed_tasks[task.task_name]["failed"] = True
            logger.warn(f"{task.task_name} failed after {self.retry_limit} retries")
