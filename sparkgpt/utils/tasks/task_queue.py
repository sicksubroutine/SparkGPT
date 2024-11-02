from queue import PriorityQueue
from concurrent.futures import ThreadPoolExecutor, Future
from task_class import Task
from attrs import define, field
import traceback
from typing import Any, Union
from datetime import datetime
from logging import getLogger, Logger

logger: Logger = getLogger(__name__)

from data_structures import SortedObjList, add_comparison_methods

TASK_RETURN_TYPE = Union[
    Any,
    str,
    None,
    bool,
    int,
    float,
    dict,
    list,
    tuple,
    set,
    frozenset,
    bytes,
    bytearray,
    memoryview,
    object,
]


def get_timestamp():
    return int(datetime.now().timestamp() * 1000)


@add_comparison_methods("start_timestamp")
@define
class WorkerObj:
    task_name: str
    start_timestamp: int = field(factory=get_timestamp)
    end_timestamp: int = 0
    retries: int = 0
    failed: bool = False
    return_value: Any = None
    completed: bool = False


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
        self.task_queue = PriorityQueue(maxsize=maxsize)
        self.retry_limit = retry_limit
        self.completed_tasks = SortedObjList(key=lambda x: x.start_timestamp)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def enqueue_task(self, task: Task) -> Future:
        if isinstance(task, Task):
            self.task_queue.put(task)
            future: Future = self.executor.submit(self._worker)
            return future
        else:
            logger.error("Invalid task type")

    def _get_task(self, timestamp: int) -> WorkerObj:
        return self.completed_tasks.find(timestamp)

    def _create_worker_obj(self, task: Task) -> Task:
        if not task.start_timestamp:
            start_timestamp = get_timestamp()
            task.start_timestamp = start_timestamp
            worker_obj = WorkerObj(task_name=task.task_name)
            self.completed_tasks.add(worker_obj)
        return task

    def _handle_work(self, task: Task) -> TASK_RETURN_TYPE:
        try:
            if task.task_func is None:
                raise ValueError("Task function is not defined")
            return_value = task()
            if return_value == "bypass_queue":
                # Task failed in a controlled manner and should be ignored from here.
                return return_value, True
            if return_value is None:
                raise ValueError("Task function did not return any value")
        except Exception as e:
            logger.error(
                f"Task failed, retrying: {e} {traceback.format_exc()}",
                extra={"task_name": task.task_name, "retry_num": task.retries},
            )
            return None, False
        l1 = ["return_value", "completed", "end_timestamp"]
        l2 = [return_value, True, get_timestamp()]
        self.completed_tasks.find_n_set(task.start_timestamp, l1, l2)
        self.task_queue.task_done()
        return return_value, True

    def _worker(self) -> Any | None:
        while not self.task_queue.empty():
            task: Task = self.task_queue.get()
            task = self._create_worker_obj(task)
            return_value, completed = self._handle_work(task)
            if completed:
                return return_value
            self._resubmit_task(task)
            self.task_queue.task_done()

    def _resubmit_task(self, task: Task):
        retry_task = self._get_task(task.start_timestamp)
        if task.retries < self.retry_limit:
            task.retries += 1
            retry_task.retries = task.retries
            self.enqueue_task(task)
        else:
            retry_task.failed = True
            logger.warn(f"{task.task_name} failed after {self.retry_limit} retries")
