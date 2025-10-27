from django.db import models
from django.conf import settings
from django.utils import timezone

# <font color="red">**新增点：创建Tag模型**</font>
class Tag(models.Model):
    """标签模型"""
    name = models.CharField(max_length=100, verbose_name="Tag Name")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created Time")
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="Creator",
        related_name='goal_app_tags'  # <font color="red">**修改点：设置唯一的related_name**</font>
    )
    
    class Meta:
        verbose_name = "Tags"
        verbose_name_plural = "Tags"
        ordering = ['-created_at']
        # 确保同一用户不能创建重复的标签名称
        unique_together = ['name', 'creator']
    
    def __str__(self):
        return self.name
    
    # 新增：获取关联目标数量的便捷方法
    def goal_count(self):
        return self.goals.count()
    goal_count.short_description = '关联目标数量'
    
    # 新增：获取关联任务数量的便捷方法
    def task_count(self):
        return self.tasks.count()
    task_count.short_description = '关联任务数量'

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
        verbose_name='Creator',
        related_name='goal_app_goals'  # <font color="red">**修改点：设置唯一的related_name**</font>
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
    # <font color="red">**新增点：添加多对多标签关系**</font>
    tags = models.ManyToManyField(
        Tag, 
        blank=True, 
        related_name='goals',
        verbose_name="Tags"
    )
    
    class Meta:
        verbose_name = 'Goal'
        verbose_name_plural = 'Goals'
        ordering = ['-created_time']
    
    def __str__(self):
        return self.title
    
    # <font color="red">**新增点：获取标签名称的便捷方法**</font>
    def get_tag_names(self):
        return ", ".join([tag.name for tag in self.tags.all()])
    get_tag_names.short_description = "Tags"

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
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Associated Goal',
        related_name='goal_app_tasks'  
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
    # <font color="red">**新增点：添加多对多标签关系**</font>
    tags = models.ManyToManyField(
        Tag, 
        blank=True, 
        related_name='tasks',
        verbose_name="Tags"
    )
    
    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['-created_time']
    
    def __str__(self):
        return self.name
    
    # <font color="red">**新增点：获取标签名称的便捷方法**</font>
    def get_tag_names(self):
        return ", ".join([tag.name for tag in self.tags.all()])
    get_tag_names.short_description = "Tags"

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