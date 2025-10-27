from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.core.validators import FileExtensionValidator

class Tag(models.Model):
    """标签模型"""
    name = models.CharField(max_length=100, verbose_name="tag Name")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="created Time")
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="creator"
    )
    
    class Meta:
        verbose_name = "Tags"
        verbose_name_plural = "Tags"
        ordering = ['-created_at']
        # 确保同一用户不能创建重复的标签名称
        unique_together = ['name', 'creator']
    
    def __str__(self):
        return self.name

class EnglishWord(models.Model):
    
    title = models.CharField(max_length=255, verbose_name="Words")
    explanation = models.TextField(verbose_name="Word Explanation")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="Creator"
    )
    # <font color="red">**新增点：添加多对多标签关系**</font>
    tags = models.ManyToManyField(
        Tag, 
        blank=True, 
        related_name='english_words',
        verbose_name="Tags"
    )
    
    class Meta:
        verbose_name = "Words"
        verbose_name_plural = "Words"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    # <font color="red">**新增点：获取标签名称的便捷方法**</font>
    def get_tag_names(self):
        return ", ".join([tag.name for tag in self.tags.all()])
    get_tag_names.short_description = "Tags"

class EnglishWordMedia(models.Model):
    
    word = models.ForeignKey(
        EnglishWord, 
        on_delete=models.CASCADE, 
        related_name='media_files',
        verbose_name="associated Word"
    )
    file = models.FileField(
        upload_to='word_media/%Y/%m/%d/',
        validators=[FileExtensionValidator(
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'bmp', 'mp4', 'avi', 'mov', 
                               'pdf', 'doc', 'docx', 'xls', 'xlsx']
        )],
        verbose_name="attached File"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Uploaded At")
    
    class Meta:
        verbose_name = "media File"
        verbose_name_plural = "media Files"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.word.title} - {self.file.name}"








