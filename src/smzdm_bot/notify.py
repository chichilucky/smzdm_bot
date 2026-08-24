"""Notification module for SMZDM Bot.

Simple functions to send notifications via various providers.
"""

import httpx
from loguru import logger

from smzdm_bot.config import NotifyConfig

TIMEOUT = 30.0


def send_pushplus(token: str, title: str, content: str) -> bool:
    """Send via PushPlus."""
    if not token:
        return False

    try:
        resp = httpx.post(
            "https://www.pushplus.plus/send",
            json={"token": token, "title": title, "content": content, "template": "html"},
            timeout=TIMEOUT,
        )
        if resp.json().get("code") == 200:
            logger.success("✅ PushPlus: sent")
            return True
        logger.warning(f"PushPlus failed: {resp.text}")
    except Exception as e:
        logger.warning(f"PushPlus error: {e}")
    return False


def send_serverchan(key: str, title: str, content: str) -> bool:
    """Send via ServerChan."""
    if not key:
        return False

    try:
        resp = httpx.post(
            f"https://sctapi.ftqq.com/{key}.send",
            data={"title": title, "desp": content},
            timeout=TIMEOUT,
        )
        if resp.json().get("code") == 0:
            logger.success("✅ ServerChan: sent")
            return True
        logger.warning(f"ServerChan failed: {resp.text}")
    except Exception as e:
        logger.warning(f"ServerChan error: {e}")
    return False


def send_wecom(webhook: str, title: str, content: str) -> bool:
    """Send via WeCom Bot."""
    if not webhook:
        return False

    try:
        resp = httpx.post(
            webhook,
            json={"msgtype": "text", "text": {"content": f"{title}\n{content}"}},
            timeout=TIMEOUT,
        )
        if resp.json().get("errcode") == 0:
            logger.success("✅ WeCom: sent")
            return True
        logger.warning(f"WeCom failed: {resp.text}")
    except Exception as e:
        logger.warning(f"WeCom error: {e}")
    return False


def send_telegram(token: str, chat_id: str, title: str, content: str, api_base: str = "") -> bool:
    """Send via Telegram Bot."""
    if not token or not chat_id:
        return False

    base = api_base.rstrip("/") if api_base else "https://api.telegram.org"
    url = f"{base}/bot{token}/sendMessage"

    try:
        resp = httpx.post(
            url,
            json={
                "chat_id": chat_id,
                "text": f"*{title}*\n\n{content}",
                "parse_mode": "Markdown",
            },
            timeout=TIMEOUT,
        )
        if resp.json().get("ok"):
            logger.success("✅ Telegram: sent")
            return True
        logger.warning(f"Telegram failed: {resp.text}")
    except Exception as e:
        logger.warning(f"Telegram error: {e}")
    return False


def send_notification(config: NotifyConfig, title: str, content: str) -> int:
    """Send notification via all configured providers.

    Returns:
        Number of successful sends.
    """
    if not config.has_any_provider:
        logger.info("No notification providers configured")
        return 0

    count = 0

    if config.push_plus_token:
        count += send_pushplus(config.push_plus_token, title, content)

    if config.sc_key:
        count += send_serverchan(config.sc_key, title, content)

    if config.wecom_webhook:
        count += send_wecom(config.wecom_webhook, title, content)

    if config.tg_bot_token and config.tg_user_id:
        count += send_telegram(
            config.tg_bot_token, config.tg_user_id, title, content, config.tg_api_base
        )

    logger.info(f"Notifications: {count} sent")
    return count

