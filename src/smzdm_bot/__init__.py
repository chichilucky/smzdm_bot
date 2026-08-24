"""SMZDM Bot - 什么值得买每日签到.

Usage:
    export SMZDM_COOKIE="your_cookie"
    smzdm-bot run

Or in Python:
    >>> from smzdm_bot import SmzdmClient
    >>> from smzdm_bot.config import UserConfig
    >>> with SmzdmClient(UserConfig(cookie="...")) as client:
    ...     print(client.checkin().to_message())
"""

from smzdm_bot.client import SmzdmClient
from smzdm_bot.config import NotifyConfig, Settings, UserConfig, get_settings
from smzdm_bot.exceptions import APIError, ConfigurationError, SmzdmError
from smzdm_bot.models import CheckinResult, LotteryResult, RewardInfo, TaskResult, VipInfo

__version__ = "1.0.0"
__all__ = [
    "SmzdmClient",
    "Settings",
    "UserConfig",
    "NotifyConfig",
    "get_settings",
    "CheckinResult",
    "VipInfo",
    "RewardInfo",
    "LotteryResult",
    "TaskResult",
    "SmzdmError",
    "APIError",
    "ConfigurationError",
]
