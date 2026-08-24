"""SMZDM 任务执行 - 使用装饰器管理任务。"""

import random
import re
import time

from loguru import logger

from smzdm_bot.client import SmzdmClient
from smzdm_bot.models import CheckinResult, LotteryResult, RewardInfo, TaskResult, VipInfo
from smzdm_bot.task_registry import TaskPriority, TaskRegistry

# 创建任务注册器
tasks = TaskRegistry()


class TaskRunner:
    """任务执行器。

    使用装饰器注册任务，自动管理执行顺序和错误处理。

    用法:
        with SmzdmClient(config) as client:
            runner = TaskRunner(client)
            results = runner.run_all()
    """

    def __init__(self, client: SmzdmClient) -> None:
        self.client = client
        self.user_id = client.user_id

    # ==================== 核心任务 ====================

    @tasks.task(name="签到", priority=TaskPriority.HIGH, optional=False)
    def checkin(self) -> CheckinResult:
        """每日签到。"""
        data = self.client.post("/checkin")
        result = CheckinResult(**data.get("data", {}))
        logger.info(f"连续签到 {result.consecutive_days} 天")
        return result

    @tasks.task(name="VIP信息", priority=TaskPriority.HIGH)
    def get_vip_info(self) -> VipInfo:
        """获取 VIP 信息。"""
        data = self.client.post("/vip")
        result = VipInfo(**data.get("data", {}).get("vip", {}))
        logger.info(f"VIP 等级: {result.level}")
        return result

    # ==================== 奖励任务 ====================

    @tasks.task(name="签到奖励", priority=TaskPriority.NORMAL)
    def get_all_reward(self) -> RewardInfo:
        """获取签到奖励。"""
        try:
            data = self.client.post("/checkin/all_reward")
            gift = data.get("data", {}).get("normal_reward", {}).get("gift", {})
            result = RewardInfo(**gift)
            if result.has_reward:
                logger.info(f"奖励: {result.title or result.content}")
            return result
        except Exception:
            # 忽略 "今日已领取" 等错误
            return RewardInfo()

    @tasks.task(name="额外奖励", priority=TaskPriority.NORMAL)
    def claim_extra_reward(self) -> bool:
        """领取连续签到额外奖励。"""
        data = self.client.post("/checkin/show_view_v2")
        for row in data.get("data", {}).get("rows", []):
            if row.get("cell_type") == "18001":
                checkin_data = row.get("cell_data", {}).get("checkin_continue", {})
                if checkin_data.get("continue_checkin_reward_show"):
                    self.client.post("/checkin/extra_reward")
                    logger.info("额外奖励已领取!")
                    return True
        logger.info("无额外奖励")
        return False

    # ==================== 抽奖任务 ====================

    @tasks.task(name="抽奖转盘", priority=TaskPriority.LOW, delay=(2, 5))
    def draw_lottery(self) -> LotteryResult:
        """抽奖转盘。"""
        ts = int(time.time())
        params = {"callback": f"jQuery_{ts}", "active_id": "A6X1veWE2O", "_": ts}

        data = self.client.get_jsonp(
            f"{self.client.WEB_BASE}/user/lottery/jsonp_get_current", params
        )
        if not data or data.get("remain_free_lottery_count", 0) < 1:
            return LotteryResult(success=False, message="没有抽奖机会")

        time.sleep(random.randint(1, 3))
        data = self.client.get_jsonp(f"{self.client.WEB_BASE}/user/lottery/jsonp_draw", params)
        if data:
            msg = data.get("error_msg", "抽奖完成")
            return LotteryResult(success=True, message=msg)

        return LotteryResult(success=False, message="抽奖失败")

    @tasks.task(name="幸运屋抽奖", priority=TaskPriority.LOW, delay=(2, 5))
    def draw_crowd(self) -> int:
        """幸运屋免费抽奖。"""
        # 获取免费抽奖 ID
        try:
            html = self.client.get_html(f"{self.client.WEB_BASE}/user/crowd/")
            pattern = (
                r'data-crowd_id="(\d+)"[^>]*>[^<]*<div[^>]*>\s*'
                r"免费抽奖?\s*</div>\s*<span[^>]*>-0</span>"
            )
            crowd_ids = re.findall(pattern, html, re.I)
        except Exception:
            crowd_ids = []

        if not crowd_ids:
            logger.info("无免费抽奖")
            return 0

        count = 0
        for crowd_id in crowd_ids:
            try:
                referer = f"{self.client.WEB_BASE}/user/crowd/p/{crowd_id}/"
                data = self.client.post_web(
                    f"{self.client.WEB_BASE}/user/crowd/ajax_participate",
                    data={
                        "crowd_id": crowd_id,
                        "sourcePage": referer,
                        "client_type": "android",
                        "price_id": 1,
                    },
                    referer=referer,
                )
                if data.get("error_code") == 0:
                    msg = re.sub(r"<[^>]+>", "", data.get("data", {}).get("msg", ""))
                    logger.info(f"幸运屋: {msg}")
                    count += 1
            except Exception as e:
                logger.debug(f"幸运屋抽奖失败: {e}")
            time.sleep(random.randint(3, 8))

        return count

    # ==================== 每日任务 ====================

    @tasks.task(name="每日任务", priority=TaskPriority.LOW, delay=(2, 5))
    def run_daily_tasks(self) -> int:
        """执行每日任务。"""
        try:
            data = self.client.post("/task/list_v2")
            rows = data.get("data", {}).get("rows", [])
            if not rows or not rows[0]:
                logger.info("无任务活动")
                return 0

            activity = rows[0].get("cell_data", {}).get("activity_task", {})
            task_groups = activity.get("accumulate_list", {}).get("task_list_v2", [])

            completed = 0
            for group in task_groups:
                for task in group.get("task_list", []):
                    completed += self._process_task(task)

            logger.info(f"完成任务: {completed}")
            return completed

        except Exception as e:
            logger.warning(f"每日任务失败: {e}")
            return 0

    # ==================== 任务处理辅助方法 ====================

    def _process_task(self, task: dict) -> int:
        """处理单个任务，返回完成数量（0或1）。"""
        status = int(task.get("task_status", 0))
        task_id = task.get("task_id", "")
        name = task.get("task_name", "")
        task_type = task.get("task_redirect_url", {}).get("link_type", "")
        event_type = task.get("task_event_type", "")

        # 未完成 (status=2)
        if status == 2:
            logger.info(f"执行: {name}")
            task_done = False

            # 浏览类任务
            if task_type in ("faxian", "haojia", "article", "yuanchuang"):
                task_done = self._do_view_task(task)
            # 关注任务
            elif (
                event_type in ("interactive.follow.user", "interactive.follow.tag")
                or task_type in ("guanzhu", "lanmu")
            ):
                task_done = self._do_follow_task(task)
            else:
                logger.debug(f"跳过: {task_type}")

            if task_done:
                time.sleep(random.randint(3, 8))
                return 1 if self._claim_task_reward(task_id, name) else 0

            time.sleep(random.randint(3, 8))

        # 待领取 (status=3)
        elif status == 3:
            logger.info(f"领取: {name}")
            if self._claim_task_reward(task_id, name):
                time.sleep(random.randint(3, 8))
                return 1

        return 0

    def _do_view_task(self, task: dict) -> bool:
        """执行浏览任务。"""
        redirect = task.get("task_redirect_url", {})
        article_id = redirect.get("link_val") or task.get("article_id")
        task_id = task.get("task_id", "")
        channel_id = task.get("channel_id", "1")
        view_seconds = int(task.get("view_seconds", 15))

        if not article_id or article_id == "0":
            return False

        logger.info(f"浏览文章 {article_id}...")
        time.sleep(view_seconds + random.randint(5, 15))

        try:
            self.client.post(
                "/task/event_view_article_sync",
                {
                    "article_id": article_id,
                    "channel_id": channel_id,
                    "task_id": task_id,
                },
            )
            return True
        except Exception:
            return False

    def _do_follow_task(self, task: dict) -> bool:
        """执行关注任务（关注后取关）。"""
        redirect = task.get("task_redirect_url", {})
        link_type = redirect.get("link_type", "")
        link_val = redirect.get("link_val", "")

        # 关注用户
        if link_type == "guanzhu" or task.get("task_event_type") == "interactive.follow.user":
            user = self._get_random_user()
            if not user:
                return False

            user_id = user.get("smzdm_id", "")
            nickname = user.get("nickname", "")

            if self._follow(user_id, nickname, "user", "follow"):
                time.sleep(random.randint(5, 10))
                self._follow(user_id, nickname, "user", "unfollow")
                return True

        # 关注栏目
        elif link_type == "lanmu" and link_val:
            keyword = redirect.get("link_title", link_val)
            if self._follow(link_val, keyword, "tag", "follow"):
                time.sleep(random.randint(5, 10))
                self._follow(link_val, keyword, "tag", "unfollow")
                return True

        return False

    def _follow(self, keyword_id: str, keyword: str, follow_type: str, action: str) -> bool:
        """关注/取关操作。"""
        try:
            self.client.post(
                f"/dingyue/{action}",
                {"keyword_id": keyword_id, "keyword": keyword, "type": follow_type},
                base=self.client.DINGYUE_API,
            )
            return True
        except Exception:
            return False

    def _get_random_user(self) -> dict | None:
        """获取随机推荐用户。"""
        try:
            data = self.client.post(
                "/tuijian/search_result",
                {"nav_id": 0, "page": 1, "type": "user", "time_code": ""},
                base=self.client.DINGYUE_API,
            )
            users = data.get("data", {}).get("rows", [])
            return random.choice(users) if users else None
        except Exception:
            return None

    def _claim_task_reward(self, task_id: str, name: str) -> bool:
        """领取任务奖励。"""
        try:
            self.client.post("/task/activity_task_receive", {"task_id": task_id})
            logger.success(f"奖励: {name}")
            return True
        except Exception:
            return False

    # ==================== 执行入口 ====================

    def run_all(self) -> TaskResult:
        """执行所有注册的任务。"""
        logger.info(f"===== 用户: {self.user_id} =====")

        # 使用任务注册器执行所有任务
        task_results = tasks.run_all(self)

        # 汇总结果
        result = TaskResult(user_id=self.user_id)

        # 提取具体结果
        for r in task_results:
            if r.data:
                if isinstance(r.data, CheckinResult):
                    result.checkin = r.data
                elif isinstance(r.data, VipInfo):
                    result.vip_info = r.data
                elif isinstance(r.data, RewardInfo):
                    result.reward = r.data
                elif isinstance(r.data, LotteryResult):
                    result.lottery = r.data

        # 只有签到失败才标记整体失败
        checkin_result = next((r for r in task_results if r.name == "签到"), None)
        result.success = checkin_result is not None and checkin_result.success

        if not result.success and checkin_result:
            result.error = checkin_result.error

        return result
