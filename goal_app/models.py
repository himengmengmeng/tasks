from django.db import models
from django.conf import settings
from django.utils import timezone

class Goal(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('blocked', 'Blocked'),
        ('resolved', 'Resolved'),
    ]
    
    # 新增：优先级选项
    PRIORITY_CHOICES = [
        ('very_high', 'very_high'),
        ('high', 'high'),
        ('medium', 'medium'),
        ('low', 'low'),
        ('very_low', 'very_low'),
    ]
    
    # 新增：紧急性选项
    URGENCY_CHOICES = [
        ('very_high', 'very_high'),
        ('high', 'high'),
        ('medium', 'medium'),
        ('low', 'low'),
        ('very_low', 'very_low'),
    ]
    
    title = models.CharField(max_length=255, verbose_name='Goal Title')
    description = models.TextField(blank=True, null=True, verbose_name='description')
    notes = models.TextField(blank=True, null=True, verbose_name='notes')
    created_time = models.DateTimeField(default=timezone.now, verbose_name='created time')
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name='Creator'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='not_started',
        verbose_name='Status'
    )
    # 新增：优先级字段
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='Priority'
    )
    # 新增：紧急性字段
    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='medium',
        verbose_name='Urgency'
    )
    
    class Meta:
        verbose_name = 'Goal'
        verbose_name_plural = 'Goals'
        ordering = ['-created_time']  # 新增：按创建时间倒序排列
    
    def __str__(self):
        return self.title

class Task(models.Model):
    STATUS_CHOICES = [
        ('not_done', 'Not Done'),
        ('done', 'Done'),
    ]
    
    # 新增：优先级选项（与Goal相同）
    PRIORITY_CHOICES = [
        ('very_high', 'very_high'),
        ('high', 'high'),
        ('medium', 'medium'),
        ('low', 'low'),
        ('very_low', 'very_low'),
    ]
    
    # 新增：紧急性选项（与Goal相同）
    URGENCY_CHOICES = [
        ('very_high', 'very_high'),
        ('high', 'high'),
        ('medium', 'medium'),
        ('low', 'low'),
        ('very_low', 'very low'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Task Title')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    goal = models.ForeignKey(
        Goal, 
        on_delete=models.SET_NULL,  # 修改为 SET_NULL
        null=True,                  # 允许数据库存储 NULL
        blank=True,                 # 允许表单提交空值
        related_name='tasks',
        verbose_name='Associated Goal'
    )
    # 新增：task创建者字段
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name='Task Creator'
    )
    created_time = models.DateTimeField(default=timezone.now, verbose_name='Creation Time')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='not_done',
        verbose_name='Status'
    )
    # 新增：优先级字段
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='Priority'
    )
    # 新增：紧急性字段
    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='medium',
        verbose_name='Urgency'
    )
    
    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
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
        verbose_name='attachment'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Goal Attachment'
        verbose_name_plural = 'Goal Attachments'

class TaskAttachment(models.Model):
    task = models.ForeignKey(
        Task, 
        on_delete=models.CASCADE, 
        related_name='attachments'
    )
    file = models.FileField(
        upload_to='task_attachments/%Y/%m/%d/',
        verbose_name='attachment'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Task Attachment'
        verbose_name_plural = 'Task Attachments'