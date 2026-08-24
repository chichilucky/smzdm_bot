"""Data models for SMZDM Bot."""

from dataclasses import dataclass

from pydantic import BaseModel, Field


class CheckinResult(BaseModel):
    """Check-in result with API field mapping."""

    consecutive_days: int = Field(alias="daily_num", default=0)
    gold: int = Field(alias="cgold", default=0)
    points: int = Field(alias="cpoints", default=0)
    experience: int = Field(alias="cexperience", default=0)
    level: int = Field(alias="rank", default=0)
    cards: int = Field(default=0)

    model_config = {"populate_by_name": True}

    def to_message(self) -> str:
        return (
            f"⭐ 签到成功 第{self.consecutive_days}天\n"
            f"🪙 金币: +{self.gold}\n"
            f"💎 积分: +{self.points}\n"
            f"📈 经验: +{self.experience}\n"
            f"🏆 等级: {self.level}\n"
            f"🎫 补签卡: {self.cards}"
        )


class VipInfo(BaseModel):
    """VIP membership info."""

    level: int = Field(alias="exp_level", default=0)
    experience: int = Field(alias="exp_current_level", default=0)
    expire_date: str = Field(alias="exp_level_expire", default="")

    model_config = {"populate_by_name": True}

    def to_message(self) -> str:
        return (
            f"👑 值会员: V{self.level}\n"
            f"✨ 经验: {self.experience}\n"
            f"📅 有效期: {self.expire_date}"
        )


class RewardInfo(BaseModel):
    """Daily reward info."""

    title: str = ""
    content: str = Field(alias="content_str", default="")
    sub_content: str = ""

    model_config = {"populate_by_name": True}

    @property
    def has_reward(self) -> bool:
        return bool(self.title or self.content)

    def to_message(self) -> str:
        if not self.has_reward:
            return "📦 今日无奖励"
        return f"🎁 {self.title or self.content}"


@dataclass
class LotteryResult:
    """Lottery draw result."""

    success: bool = False
    message: str = "没有抽奖机会"

    def to_message(self) -> str:
        return f"🎰 {self.message}"


@dataclass
class TaskResult:
    """Result of all tasks for a user."""

    user_id: str
    success: bool = True
    checkin: CheckinResult | None = None
    vip_info: VipInfo | None = None
    reward: RewardInfo | None = None
    lottery: LotteryResult | None = None
    error: str | None = None

    def to_message(self) -> str:
        lines = [f"📋 用户: {self.user_id}", "─" * 20]

        if self.checkin:
            lines.append(self.checkin.to_message())
        if self.vip_info:
            lines.append(self.vip_info.to_message())
        if self.reward:
            lines.append(self.reward.to_message())
        if self.lottery:
            lines.append(self.lottery.to_message())
        if self.error:
            lines.append(f"❌ {self.error}")

        return "\n".join(lines)


