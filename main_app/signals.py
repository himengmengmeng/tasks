

import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import EnglishWordMedia

@receiver(post_delete, sender=EnglishWordMedia)
def delete_upload_files(sender, instance, **kwargs):
    """
    当 EnglishWordMedia 对象被删除时，自动删除其对应的文件。
    """
    if instance.file:  # 检查是否有文件
        file_path = os.path.join(settings.MEDIA_ROOT, str(instance.file))
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                # 可选：尝试删除空的上级目录（根据需要决定）
                # dir_path = os.path.dirname(file_path)
                # if not os.listdir(dir_path): # 如果目录为空
                #     os.rmdir(dir_path)
        except (OSError, Exception) as e:
            # 最好使用日志记录异常，而不是直接抛出
            # 例如：logger.error(f"Error deleting file {file_path}: {e}")
            print(f"Error deleting file {file_path}: {e}")