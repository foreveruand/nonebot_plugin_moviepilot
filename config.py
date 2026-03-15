from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from nonebot import get_driver, logger

class Config(BaseModel):
    # Pydantic V2 的配置项：忽略多余字段
    model_config = ConfigDict(extra="ignore")

    # MoviePilot Plugin 配置 (增加 moviepilot_ 前缀别名)
    mp_url: Optional[str] = Field("", alias="moviepilot_mp_url")
    mp_username: Optional[str] = Field("admin", alias="moviepilot_mp_username")
    mp_password: Optional[str] = Field("", alias="moviepilot_mp_password")

class ConfigError(Exception):
    pass

# --- 初始化逻辑 ---
global_config = get_driver().config

try:
    # 优先尝试 model_validate (V2)，如果 NoneBot 版本较低则回退
    config_data = global_config.model_dump() if hasattr(global_config, "model_dump") else global_config.dict()
    # validation_alias=True 允许通过别名从字典中读取数据
    plugin_config = Config.model_validate(config_data)
except Exception as e:
    logger.error(f"MoviePilot 配置解析失败，请检查 .env 变量类型: {e}")
    plugin_config = Config()  # 兜底返回默认配置