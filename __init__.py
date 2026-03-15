
import asyncio
from typing import Annotated, Union

import nonebot
from nonebot import Bot, on_command
from nonebot.adapters import Event
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from .api import MoviepilotApi
from .config import plugin_config
__plugin_meta__ = PluginMetadata(
    name="moviepilot",
    description="mp订阅插件",
    usage="""/sub 剧名 订阅电视剧/电影
    """,
    extra={},
    type="application",
    homepage="",
)
sub = on_command("sub", block=True, priority=5,force_whitespace=True,permission=SUPERUSER)
  
moviepilot = MoviepilotApi(plugin_config)
state = {}
@sub.handle()
async def _(
    event: Event,
    args=CommandArg(),
):
    user_id = event.user_id
    media_name = args.extract_plain_text()
    movies = await moviepilot.search_media_info(media_name)  # 使用 self.api 访问实例属性
    if movies:
        movie_list = "\n".join([f"{i + 1}. {movie['title']} ({movie['year']})" for i, movie in enumerate(movies)])
        logger.debug(movie_list)
        media_list = "\n查询到的影片如下\n/select 0 退出选择\n/select 序号 进行订阅：\n" + movie_list
        if 'wxid' in str(user_id):
            await sub.send(media_list)
        else:
            await sub.send(media_list)
        state[user_id] = {"movies": movies}  # 保存用户状态
    else:
        await sub.finish("没有查询到影片，请检查名字。")

    select = on_command("select", block=True, priority=5,force_whitespace=True,permission=SUPERUSER)
    
    @select.handle()
    async def _(
        event: Event,
        args=CommandArg(),
    ):
        new_user_id = getattr(event,'user_id', None)
        if new_user_id and 'wxid' in new_user_id:
            new_user_id = event.user_id
        else:
            user = event.from_
            new_user_id = user.id
        if not user_id == new_user_id:
            await select.finish()
        user_state = state.get(user_id)
        if user_state and "movies" in user_state:
            try:
                index = int(args) - 1
                if index == -1:  # 用户输入0
                    del state[user_id]  # 清除用户状态
                    await sub.finish("操作已取消。")
                if 0 <= index < len(user_state["movies"]):
                    selected_movie = user_state["movies"][index]
                    if selected_movie['type'] == "电视剧":
                        # 如果是电视剧，获取所有季数
                        seasons = await moviepilot.list_all_seasons(selected_movie['tmdb_id'])
                        if seasons:
                            season_list = "\n".join(
                                [f"第 {season['season_number']} 季 {season['name']}" for season in seasons])
                            season_list = "\n查询到的季如下\n/season 序号 进行选择：\n请选择季数：\n" + season_list
                            await select.send(season_list)
                            season = on_command("season", block=True, priority=5,force_whitespace=True,permission=SUPERUSER)
                            user_state["selected_movie"] = selected_movie
                            user_state["seasons"] = seasons
                        else:
                            await sub.finish("没有找到可用的季数。")
                    else:
                        # 如果是电影，直接订阅
                        success = await moviepilot.subscribe_movie(selected_movie)
                        if success:
                            del state[user_id]  # 清除用户状态
                            await sub.finish(f"\n订阅类型：{selected_movie['type']}\n订阅影片：{selected_movie['title']} ({selected_movie['year']})\n订阅成功！")
                        else:
                            await sub.finish("订阅失败。")
                else:
                    await select.finish("无效的序号，请重新输入。")
            except ValueError:
                await select.finish("请输入一个数字。")
            except Exception:
                raise
        else:
            await sub.finish("请先使用 /sub 命令搜索影片。")
        
        @season.handle()
        async def _(
            event: Event,
            args=CommandArg(),
        ):
            new_user_id = getattr(event,'user_id', None)
            if new_user_id and 'wxid' in new_user_id:
                new_user_id = event.user_id
            else:
                user = event.from_
                new_user_id = user.id
            if not user_id == new_user_id:
                await season.finish()

            user_state = state.get(user_id)
            if user_state and "selected_movie" in user_state and "seasons" in user_state:
                try:
                    season_number = int(args)
                    seasons = user_state["seasons"]
                    selected_movie = user_state["selected_movie"]
                    for season in seasons:
                        if season['season_number'] == season_number:
                            success = await moviepilot.subscribe_series(selected_movie, season_number)
                            if success:
                                del state[user_id]  # 清除用户状态
                                await sub.finish(f"\n订阅类型：{selected_movie['type']}\n订阅影片：{selected_movie['title']} ({selected_movie['year']})\n订阅第 {season_number} 季成功！")
                                
                            else:
                                await sub.finish("订阅失败。")
                            return
                    await season.finish("无效的季数，请重新输入。")
                except ValueError:
                    await season.finish("请输入一个数字。")
                except Exception:
                    raise
            else:
                await season.finish("请先使用 /sub 和 /select 命令选择电视剧和季数。")
