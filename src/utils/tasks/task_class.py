# from pydantic import BaseModel, Field, ConfigDict
# from typing import Callable, Tuple, Dict
# from functools import wraps

# from logging import getLogger, Logger

# logger: Logger = getLogger(__name__)


# class RecursiveTaskDecoratorError(Exception):
#     def __init__(self, func_name=None):
#         msg = f"Cannot decorate recursive functions ({func_name}), please a use direct instance of Task class."
#         super().__init__(msg)


# class TaskModel(BaseModel):
#     task_name: str = Field(..., title="Task Name", required=True)
#     task_func: Callable = Field(..., title="Task Function", required=True)
#     args: Tuple = Field(None, title="Task Arguments", required=False)
#     kwargs: Dict = Field(None, title="Task Keyword Arguments", required=False)
#     retries: int = Field(default=0, title="Task Retries", required=False)
#     decorator: bool = Field(default=False, title="Decorator", required=False)

#     model_config = ConfigDict(
#         title="Task Model",
#         description="Task Model for Task Class",
#         arbitrary_types_allowed=True,
#         extra="forbid",
#     )


# class Task(TaskModel):
#     def __init__(self, task_name: str, task_func: Callable = None, *args, **kwargs):
#         super().__init__(
#             task_name=task_name,
#             task_func=task_func,
#             args=args,
#             kwargs=kwargs,
#         )
#         self.decorator = kwargs.get("decorator", False)

#     def __call__(self, *args, **kwargs):
#         try:
#             final_args = self.args + args
#             final_kwargs = {**self.kwargs, **kwargs}
#             # sig = inspect.signature(self.task_func)
#             # accepted_kwargs = {
#             #     k: v for k, v in final_kwargs.items() if k in sig.parameters
#             # }
#             # print(accepted_kwargs)
#             return self.task_func(*final_args, **final_kwargs)
#         except Exception as e:
#             logger.error(f"Error: {e}")
#             return None

#     def __str__(self):
#         return f"{self.task_name}"


# def task_make(name=None, **mods) -> TaskModel:
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             func_name = func.__name__
#             if func_name in func.__code__.co_names:
#                 raise RecursiveTaskDecoratorError(func_name=func_name)
#             kwargs["decorator"] = True
#             kwargs.update(mods)
#             task_name = name if name else func_name
#             return Task(task_name, func, *args, **kwargs)

#         return wrapper

#     return decorator
