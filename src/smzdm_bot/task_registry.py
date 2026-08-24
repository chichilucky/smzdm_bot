"""任务注册器 - 使用装饰器管理任务。"""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any

from loguru import logger


class TaskPriority(Enum):
    """任务优先级。"""

    HIGH = 1  # 签到等核心任务
    NORMAL = 2  # VIP、奖励等
    LOW = 3  # 抽奖、每日任务等


@dataclass
class TaskInfo:
    """任务元信息。"""

    name: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    optional: bool = False  # 失败是否继续
    delay: tuple[int, int] = (1, 5)  # 延迟范围（秒）


@dataclass
class TaskResult:
    """任务执行结果。"""

    name: str
    success: bool
    data: Any = None
    error: str | None = None


class TaskRegistry:
    """任务注册器。

    用法:
        registry = TaskRegistry()

        @registry.task(name="签到", priority=TaskPriority.HIGH)
        def checkin(self):
            return self.client.post("/checkin")

        # 执行所有任务
        results = registry.run_all(runner_instance)
    """

    def __init__(self) -> None:
        self._tasks: list[tuple[TaskInfo, Callable]] = []

    def task(
        self,
        name: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        optional: bool = True,
        delay: tuple[int, int] = (1, 5),
    ) -> Callable:
        """任务装饰器。

        Args:
            name: 任务名称（用于日志）
            description: 任务描述
            priority: 优先级，决定执行顺序
            optional: 是否可选（失败时是否继续执行其他任务）
            delay: 执行前的随机延迟范围（秒）
        """
        info = TaskInfo(
            name=name,
            description=description or name,
            priority=priority,
            optional=optional,
            delay=delay,
        )

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(instance: Any, *args: Any, **kwargs: Any) -> Any:
                return func(instance, *args, **kwargs)

            self._tasks.append((info, wrapper))
            return wrapper

        return decorator

    def run_all(self, instance: Any) -> list[TaskResult]:
        """按优先级执行所有注册的任务。

        Args:
            instance: 任务执行器实例（self）

        Returns:
            所有任务的执行结果列表
        """
        # 按优先级排序
        sorted_tasks = sorted(self._tasks, key=lambda x: x[0].priority.value)
        results: list[TaskResult] = []

        for info, func in sorted_tasks:
            logger.info(f"执行: {info.name}")

            # 随机延迟
            if info.delay[1] > 0:
                time.sleep(random.randint(*info.delay))

            try:
                data = func(instance)
                results.append(TaskResult(name=info.name, success=True, data=data))
                logger.success(f"{info.name} 完成")

            except Exception as e:
                error_msg = str(e)
                results.append(TaskResult(name=info.name, success=False, error=error_msg))

                if info.optional:
                    logger.warning(f"{info.name} 失败: {error_msg}")
                else:
                    logger.error(f"{info.name} 失败: {error_msg}")
                    break  # 非可选任务失败，停止执行

        return results

    def clear(self) -> None:
        """清空所有注册的任务。"""
        self._tasks.clear()


# 全局任务注册器
tasks = TaskRegistry()
