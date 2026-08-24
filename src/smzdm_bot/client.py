"""SMZDM HTTP 客户端 - 只负责请求和签名。"""

import base64
import hashlib
import json
import random
import re
import string
import time
from urllib.parse import unquote

import httpx
from loguru import logger

from smzdm_bot.config import UserConfig
from smzdm_bot.exceptions import APIError

# 常量
SIGN_KEY = "apr1$AwP!wRRT$gJ/q.X24poeBInlUJC"
SK_KEY = "geZm53XAspb02exN"  # DES 加密密钥
DEFAULT_VERSION = "10.4.26"
DEFAULT_VERSION_CODE = "866"


def parse_cookies(cookie_str: str) -> dict[str, str]:
    """解析 cookie 字符串。"""
    if not cookie_str.endswith(";"):
        cookie_str += ";"
    return {k.strip(): unquote(v.strip()) for k, v in re.findall(r"([^=;]+)=([^;]*);", cookie_str)}


def sign_data(data: dict) -> str:
    """MD5 签名。"""
    # 过滤空值，排序，并删除值中的空白字符
    parts = []
    for k, v in sorted(data.items()):
        v_str = str(v).replace(" ", "").replace("\t", "").replace("\n", "")
        if v_str:  # 只包含非空值
            parts.append(f"{k}={v_str}")
    sign_str = "&".join(parts) + f"&key={SIGN_KEY}"
    return hashlib.md5(sign_str.encode()).hexdigest().upper()


def parse_jsonp(text: str) -> dict | None:
    """解析 JSONP 响应。"""
    match = re.search(r"\{.*\}", text)
    return json.loads(match.group()) if match else None


def generate_sk(user_id: str, device_id: str) -> str:
    """使用 DES-ECB 加密生成 SK。"""
    try:
        from Crypto.Cipher import DES
        from Crypto.Util.Padding import pad

        key = SK_KEY.encode()[:8]  # DES 密钥 8 字节
        plaintext = (user_id + device_id).encode()
        cipher = DES.new(key, DES.MODE_ECB)
        encrypted = cipher.encrypt(pad(plaintext, DES.block_size))
        return base64.b64encode(encrypted).decode()
    except ImportError:
        logger.warning("pycryptodome 未安装，SK 自动生成不可用")
        return ""


def random_string(length: int = 32) -> str:
    """生成随机字符串。"""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


class SmzdmClient:
    """SMZDM HTTP 客户端。"""

    API_BASE = "https://user-api.smzdm.com"
    WEB_BASE = "https://zhiyou.smzdm.com"
    DINGYUE_API = "https://dingyue-api.smzdm.com"
    TIMEOUT = 30.0

    def __init__(self, config: UserConfig) -> None:
        self._cookie = config.cookie.strip()
        self._cookies = parse_cookies(self._cookie)

        if not self._cookies.get("sess"):
            raise APIError("Cookie 缺少 sess 字段")

        self.user_id = self._cookies.get("smzdm_id", "unknown")
        self._http = httpx.Client(timeout=self.TIMEOUT)

        # 设备信息
        self._version = self._cookies.get("device_smzdm_version") or self._cookies.get(
            "v", DEFAULT_VERSION
        )
        self._platform = self._cookies.get("device_smzdm", "android")
        self._device_id = (
            self._cookies.get("device_id")
            or self._cookies.get("pr_device_id")
            or self._cookies.get("pr_new_device_id")
            or self._cookies.get("device_rid")
            or random_string(32)
        )

        # SK: 优先使用配置，否则自动生成
        if config.sk:
            self._sk = config.sk
        else:
            self._sk = generate_sk(self.user_id, self._device_id)
            if self._sk:
                logger.debug("SK 自动生成成功")

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "SmzdmClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ========== 请求头 ==========

    def _app_headers(self) -> dict[str, str]:
        """APP 请求头。"""
        vc = self._cookies.get("device_smzdm_version_code", DEFAULT_VERSION_CODE)
        m = self._cookies.get("device_type", "Redmi")
        s = self._cookies.get("device_system_version", "10")
        p = self._platform.capitalize()
        ua = f"smzdm_{self._platform}_V{self._version} rv:{vc} ({m};{p}{s};zh)smzdmapp"
        return {
            "User-Agent": ua,
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": self._cookie,
            "request_key": str(random.randint(10**15, 10**16)),
        }

    def _web_headers(self, referer: str | None = None) -> dict[str, str]:
        """Web 请求头。"""
        vc = self._cookies.get("device_smzdm_version_code", DEFAULT_VERSION_CODE)
        ua = (
            f"Mozilla/5.0 (Linux; Android 10; Redmi) AppleWebKit/537.36 "
            f"Chrome/95.0.4638.74 Mobile Safari/537.36 "
            f"smzdm_android_V{self._version} rv:{vc} smzdmapp"
        )
        headers = {
            "Cookie": self._cookie,
            "User-Agent": ua,
        }
        if referer:
            headers["Referer"] = referer
            headers["Origin"] = referer.rsplit("/", 1)[0]
        return headers

    # ========== 请求方法 ==========

    def _build_form(self, extra: dict | None = None) -> dict:
        """构建签名表单。"""
        data = {
            "weixin": "1",
            "basic_v": "0",
            "f": self._platform,
            "v": self._version,
            "time": f"{int(time.time())}000",
            "token": self._cookies.get("sess", ""),
        }
        if self._sk:
            data["sk"] = self._sk
        if extra:
            data.update(extra)
        data["sign"] = sign_data(data)
        return data

    def post(self, endpoint: str, extra: dict | None = None, base: str | None = None) -> dict:
        """发送签名 POST 请求。"""
        url = (base or self.API_BASE) + endpoint
        resp = self._http.post(url, data=self._build_form(extra), headers=self._app_headers())
        resp.raise_for_status()

        data = resp.json()
        code = data.get("error_code")
        if code is not None and int(code) != 0:
            raise APIError(data.get("error_msg", "API错误"), error_code=int(code))
        return data

    def post_web(self, url: str, data: dict, referer: str | None = None) -> dict:
        """发送 Web POST 请求（不签名）。"""
        resp = self._http.post(url, data=data, headers=self._web_headers(referer))
        resp.raise_for_status()
        return resp.json()

    def get_web(self, url: str, params: dict | None = None) -> httpx.Response:
        """发送 Web GET 请求。"""
        return self._http.get(url, params=params, headers=self._web_headers())

    def get_jsonp(self, url: str, params: dict | None = None) -> dict | None:
        """发送请求并解析 JSONP。"""
        resp = self.get_web(url, params)
        return parse_jsonp(resp.text)

    def get_html(self, url: str) -> str:
        """获取网页 HTML。"""
        resp = self.get_web(url)
        return resp.text
