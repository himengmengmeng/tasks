from django.apps import AppConfig


class GoalAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'goal_app'
# <font color="red">**修改点：设置verbose_name来控制显示顺序**</font>
   