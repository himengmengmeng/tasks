from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.core.validators import FileExtensionValidator


class Tag(models.Model):
    """标签模型"""
    name = models.CharField(max_length=100, verbose_name="Tag Name")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="creator",
        related_name='main_app_tags'  # <font color="red">**修改点：设置唯一的related_name**</font>
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
        verbose_name="Creator",
        related_name='main_app_english_words'  # <font color="red">**修改点：设置唯一的related_name**</font>
    )
    # 新增点：添加多对多标签关系
    tags = models.ManyToManyField(
        Tag, 
        blank=True, 
        related_name='english_words',
        verbose_name="Tags"
    )
    
    class Meta:
        verbose_name = "English Word"
        verbose_name_plural = "Vocabulary"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    # 新增点：获取标签名称的便捷方法
    def get_tag_names(self):
        return ", ".join([tag.name for tag in self.tags.all()])
    get_tag_names.short_description = "Tags"

class EmailScheduleConfig(models.Model):
    """Per-user configuration for periodic vocabulary story emails."""

    LANGUAGE_CHOICES = [
        ('english', 'English'),
        ('bilingual', 'Bilingual (English + Chinese)'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_schedule',
        verbose_name="User",
    )
    is_active = models.BooleanField(default=False, verbose_name="Active")
    timezone = models.CharField(max_length=50, default='Asia/Shanghai', verbose_name="Timezone")
    send_times = models.JSONField(
        default=list,
        verbose_name="Send Times",
        help_text='List of "HH:MM" strings, e.g. ["08:00", "18:00"]',
    )
    words_per_email = models.PositiveIntegerField(default=3, verbose_name="Words Per Email")
    extra_recipients = models.JSONField(
        default=list,
        verbose_name="Extra Recipients",
        help_text="Up to 3 additional email addresses",
    )
    story_language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        default='english',
        verbose_name="Story Language",
    )
    exclude_word_ids = models.JSONField(
        default=list,
        verbose_name="Excluded Word IDs",
        help_text="Word IDs to exclude from random selection",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Email Schedule Config"
        verbose_name_plural = "Email Schedule Configs"

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.user.username} - {status} ({len(self.send_times)} slots/day)"

    def get_all_recipients(self):
        recipients = [self.user.email]
        if self.extra_recipients:
            recipients.extend(self.extra_recipients[:3])
        return recipients

    def save(self, *args, **kwargs):
        if not self.exclude_word_ids:
            self.exclude_word_ids = [22, 23]
        if self.extra_recipients:
            self.extra_recipients = self.extra_recipients[:3]
        super().save(*args, **kwargs)


class StoryEmail(models.Model):
    """Record of each story email sent to a user."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='story_emails',
        verbose_name="User",
    )
    words = models.ManyToManyField(
        EnglishWord,
        blank=True,
        related_name='story_emails',
        verbose_name="Words Used",
    )
    word_snapshots = models.JSONField(
        default=list,
        verbose_name="Word Snapshots",
        help_text='Snapshot of [{title, explanation}] at send time',
    )
    story_content = models.TextField(verbose_name="Story Content")
    subject = models.CharField(max_length=255, verbose_name="Subject")
    recipient_emails = models.JSONField(
        default=list,
        verbose_name="Recipient Emails",
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Sent At")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status",
    )
    error_message = models.TextField(blank=True, null=True, verbose_name="Error Message")

    class Meta:
        verbose_name = "Story Email"
        verbose_name_plural = "Story Emails"
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.subject} ({self.status}) - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"


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
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")
    
    class Meta:
        verbose_name = "media File"
        verbose_name_plural = "media Files"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.word.title} - {self.file.name}"








