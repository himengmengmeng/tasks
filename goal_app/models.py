from django.db import models
from django.conf import settings
from django.utils import timezone

class Goal(models.Model):
    STATUS_CHOICES = [
        ('not_started', '未开启'),
        ('in_progress', '进行中'),
        ('blocked', '遇到阻碍'),
        ('resolved', '已解决'),
    ]
    
    # 新增：优先级选项
    PRIORITY_CHOICES = [
        ('very_high', '极高重要性'),
        ('high', '高重要性'),
        ('medium', '中等重要性'),
        ('low', '低重要性'),
        ('very_low', '极低/无关重要性'),
    ]
    
    # 新增：紧急性选项
    URGENCY_CHOICES = [
        ('very_high', '极急'),
        ('high', '高紧急性'),
        ('medium', '中等紧急性'),
        ('low', '低紧急性'),
        ('very_low', '极低/无时间限制'),
    ]
    
    title = models.CharField(max_length=255, verbose_name='标题')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    notes = models.TextField(blank=True, null=True, verbose_name='备注')
    created_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name='创建者'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='not_started',
        verbose_name='状态'
    )
    # 新增：优先级字段
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='优先级'
    )
    # 新增：紧急性字段
    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='medium',
        verbose_name='紧急性'
    )
    
    class Meta:
        verbose_name = '目标'
        verbose_name_plural = '目标'
        ordering = ['-created_time']  # 新增：按创建时间倒序排列
    
    def __str__(self):
        return self.title

class Task(models.Model):
    STATUS_CHOICES = [
        ('not_done', '未完成'),
        ('done', '已完成'),
    ]
    
    # 新增：优先级选项（与Goal相同）
    PRIORITY_CHOICES = [
        ('very_high', '极高重要性'),
        ('high', '高重要性'),
        ('medium', '中等重要性'),
        ('low', '低重要性'),
        ('very_low', '极低/无关重要性'),
    ]
    
    # 新增：紧急性选项（与Goal相同）
    URGENCY_CHOICES = [
        ('very_high', '极急'),
        ('high', '高紧急性'),
        ('medium', '中等紧急性'),
        ('low', '低紧急性'),
        ('very_low', '极低/无时间限制'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='任务名称')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    goal = models.ForeignKey(
        Goal, 
        on_delete=models.SET_NULL,  # 修改为 SET_NULL
        null=True,                  # 允许数据库存储 NULL
        blank=True,                 # 允许表单提交空值
        related_name='tasks',
        verbose_name='关联目标'
    )
    # 新增：task创建者字段
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name='任务创建者'
    )
    created_time = models.DateTimeField(default=timezone.now, verbose_name='建立时间')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='not_done',
        verbose_name='状态'
    )
    # 新增：优先级字段
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='优先级'
    )
    # 新增：紧急性字段
    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='medium',
        verbose_name='紧急性'
    )
    
    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务'
        ordering = ['-created_time']  # 新增：按创建时间倒序排列
    
    def __str__(self):
        return self.name

class GoalAttachment(models.Model):
    goal = models.ForeignKey(
        Goal, 
        on_delete=models.CASCADE, 
        related_name='attachments'
    )
    file = models.FileField(
        upload_to='goal_attachments/%Y/%m/%d/',
        verbose_name='附件'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '目标附件'
        verbose_name_plural = '目标附件'

class TaskAttachment(models.Model):
    task = models.ForeignKey(
        Task, 
        on_delete=models.CASCADE, 
        related_name='attachments'
    )
    file = models.FileField(
        upload_to='task_attachments/%Y/%m/%d/',
        verbose_name='附件'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '任务附件'
        verbose_name_plural = '任务附件'