from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.core.validators import FileExtensionValidator

class EnglishWord(models.Model):
    """英文单词模型"""
    title = models.CharField(max_length=255, verbose_name="单词")
    explanation = models.TextField(verbose_name="单词解释")
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="创建者"
    )
    
    class Meta:
        verbose_name = "英文单词"
        verbose_name_plural = "英文单词"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class EnglishWordMedia(models.Model):
    """英文单词的多媒体文件模型"""
    word = models.ForeignKey(
        EnglishWord, 
        on_delete=models.CASCADE, 
        related_name='media_files',
        verbose_name="关联单词"
    )
    file = models.FileField(
        upload_to='word_media/%Y/%m/%d/',
        validators=[FileExtensionValidator(
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'bmp', 'mp4', 'avi', 'mov', 
                               'pdf', 'doc', 'docx', 'xls', 'xlsx']
        )],
        verbose_name="附件"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")
    
    class Meta:
        verbose_name = "单词多媒体文件"
        verbose_name_plural = "单词多媒体文件"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.word.title} - {self.file.name}"








