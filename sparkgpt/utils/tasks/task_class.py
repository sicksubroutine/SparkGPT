from typing import Callable, Tuple, Dict
from functools import wraps
from attrs import define, field
from logging import getLogger, Logger

logger: Logger = getLogger(__name__)


class RecursiveTaskDecoratorError(Exception):
    def __init__(self, func_name=None):
        msg = f"Cannot decorate recursive functions ({func_name}), please a use direct instance of Task class."
        super().__init__(msg)


@define
class Task:
    task_name: str = field()
    task_func: Callable = field()
    priority: int = field(default=0)
    start_timestamp: float = field(default=None)
    args: Tuple = field(default=())
    kwargs: Dict = field(default={})

    @classmethod
    def create(cls, *args, **kwargs):
        known_keys = {
            "task_name",
            "task_func",
            "priority",
            "start_timestamp",
            "args",
            "kwargs",
        }
        init_kwargs = {
            key: kwargs.pop(key) for key in list(kwargs) if key in known_keys
        }
        obj = cls(**init_kwargs)
        obj.kwargs = kwargs
        obj.args = args
        return obj

    def __call__(self, *args, **kwargs):
        try:
            final_args = self.args + args
            final_kwargs = {**self.kwargs, **kwargs}
            return self.task_func(*final_args, **final_kwargs)
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

    def __str__(self):
        return f"{self.task_name}"


def task_make(name=None, **mods) -> Task:
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            if func_name in func.__code__.co_names:
                raise RecursiveTaskDecoratorError(func_name=func_name)
            kwargs.update(mods)
            task_name = name if name else func_name
            return Task(task_name, func, *args, **kwargs)

        return wrapper

    return decorator
