from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class MainAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main_app'

    def ready(self):
        # 导入信号处理器
        import main_app.signals
        logger.info("Main app signals imported")    
