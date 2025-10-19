from django.contrib import admin
from django import forms
from .models import Goal, Task, GoalAttachment, TaskAttachment

class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    show_change_link = True
    exclude = ['creator']  # Hide creator field in the inline
    
    # 新增：限制显示的字段，避免内联表单太长
    fields = ['name', 'priority', 'urgency', 'status', 'description']
    
    def get_formset(self, request, obj=None, **kwargs):
        """重写get_formset以确保在创建内联Task时设置creator"""
        formset = super().get_formset(request, obj, **kwargs)
        formset.request = request
        return formset
    
    def save_formset(self, request, form, formset, change):
        """重写保存表单集的方法，为每个内联Task设置creator"""
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.pk:  # 如果是新创建的Task
                instance.creator = request.user
            instance.save()
        formset.save_m2m()

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    # 修改：在列表显示中添加优先级和紧急性
    list_display = ['title', 'creator', 'priority', 'urgency', 'status', 'created_time']
    
    # 修改：在过滤器中添加优先级和紧急性
    list_filter = ['priority', 'urgency', 'status', 'created_time']
    
    # 修改：在搜索字段中添加优先级和紧急性
    search_fields = ['title', 'description', 'notes', 'priority', 'urgency']
    
    readonly_fields = ['created_time']
    inlines = [TaskInline]
    
    # 修改：字段显示顺序，将新字段放在合适的位置
    fields = [
        'title', 'priority', 'urgency', 'status', 
        'description', 'notes', 'created_time'
    ]
    
    # 完全排除创建者字段
    exclude = ['creator']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)
    
    def save_model(self, request, obj, form, change):
        # 确保创建者被设置
        if not change:  # 如果是新对象
            obj.creator = request.user
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        """处理内联表单集的保存，确保内联Task的creator被设置"""
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Task) and not instance.pk:
                instance.creator = request.user
            instance.save()
        formset.save_m2m()

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    # 修改：在列表显示中添加优先级和紧急性
    list_display = ['name', 'goal', 'creator', 'priority', 'urgency', 'status', 'created_time']
    
    # 修改：在过滤器中添加优先级和紧急性
    list_filter = ['priority', 'urgency', 'status', 'created_time']
    
    # 修改：在搜索字段中添加优先级和紧急性
    search_fields = ['name', 'description', 'priority', 'urgency']
    
    readonly_fields = ['created_time']
    
    # 修改：字段显示顺序，将新字段放在合适的位置
    fields = [
        'name', 'goal', 'priority', 'urgency', 'status',
        'description', 'created_time'
    ]
    
    # 完全排除创建者字段
    exclude = ['creator']
    
    # 新增：为goal字段启用搜索
    autocomplete_fields = ['goal']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)
    
    def save_model(self, request, obj, form, change):
        # 确保创建者被设置
        if not change:  # 如果是新对象
            obj.creator = request.user
        super().save_model(request, obj, form, change)

# 新增：注册附件模型到admin（可选）
'''
@admin.register(GoalAttachment)
class GoalAttachmentAdmin(admin.ModelAdmin):
    list_display = ['goal', 'file', 'uploaded_at']
    list_filter = ['uploaded_at']

@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ['task', 'file', 'uploaded_at']
    list_filter = ['uploaded_at']
'''

# 注释掉附件的Admin注册以完全隐藏附件模型
# @admin.register(GoalAttachment)
# class GoalAttachmentAdmin(admin.ModelAdmin):
#     list_display = ['goal', 'file', 'uploaded_at']
    
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         if request.user.is_superuser:
#             return qs
#         return qs.filter(goal__creator=request.user)

# @admin.register(TaskAttachment)
# class TaskAttachmentAdmin(admin.ModelAdmin):
#     list_display = ['task', 'file', 'uploaded_at']
    
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         if request.user.is_superuser:
#             return qs
#         return qs.filter(task__goal__creator=request.user)
