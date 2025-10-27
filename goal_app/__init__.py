# goal_app/__init__.py
from django.contrib.admin import sites
from django.apps import apps

# 获取原始方法
original_get_app_list = sites.AdminSite.get_app_list

def custom_get_app_list(self, request):
    """自定义应用列表排序"""
    app_list = original_get_app_list(self, request)
    
    # 查找 goal_app
    for app in app_list:
        if app['app_label'] == 'goal_app':
            # 定义模型顺序
            model_order = ['tag', 'task', 'goal', 'goalattachment', 'taskattachment']
            
            # 创建新的模型列表，按照指定顺序
            ordered_models = []
            for model_name in model_order:
                for model in app['models']:
                    if model['object_name'].lower() == model_name:
                        ordered_models.append(model)
                        break
            
            # 更新应用中的模型顺序
            app['models'] = ordered_models
    
    return app_list

# 应用自定义方法
sites.AdminSite.get_app_list = custom_get_app_list