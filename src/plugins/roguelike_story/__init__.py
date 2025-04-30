"""
@Author         : Ailitonia
@Date           : 2025/2/15 10:30
@FileName       : roguelike_story
@Project        : omega-miya
@Description    : 肉鸽故事插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='RoguelikeStory',
    description='【肉鸽故事插件】\n'
                '基于AI的肉鸽故事，快来开始你的冒险吧!',
    usage='/故事肉鸽启动\n'
          '/结束故事肉鸽\n'
          '/快速行动检定',
    extra={'author': 'Ailitonia'},
)

from . import command as command

__all__ = []
