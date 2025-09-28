from django.contrib import admin
from django import forms
from .models import Goal, Task, GoalAttachment, TaskAttachment

# 注释掉附件Inline以隐藏附件
# class GoalAttachmentInline(admin.TabularInline):
#     model = GoalAttachment
#     extra = 1

# class TaskAttachmentInline(admin.TabularInline):
#     model = TaskAttachment
#     extra = 1

class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    show_change_link = True
    # 在Inline中隐藏创建者字段，因为会自动设置
    exclude = ['creator']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'status', 'created_time']
    list_filter = ['status', 'created_time', 'creator']
    search_fields = ['title', 'description', 'notes']
    readonly_fields = ['created_time']
    # 移除附件Inline以隐藏目标附件
    inlines = [TaskInline]  # 移除了 GoalAttachmentInline
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # 如果是新创建的目标
            obj.creator = request.user  # 自动设置为当前用户
        super().save_model(request, obj, form, change)
    
    # 在创建/编辑表单中隐藏创建者字段，因为会自动设置:cite[3]
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            # 对于非超级用户，隐藏创建者字段
            form.base_fields['creator'].widget = forms.HiddenInput()
        return form

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'goal', 'creator', 'status', 'created_time']  # 添加creator到列表显示
    list_filter = ['status', 'created_time', 'goal', 'creator']
    search_fields = ['name', 'description']
    readonly_fields = ['created_time']
    # 移除附件Inline以隐藏任务附件
    # inlines = [TaskAttachmentInline]  # 注释掉这行
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # 如果是新创建的任务
            obj.creator = request.user  # 自动设置为当前用户
        super().save_model(request, obj, form, change)
    
    # 在创建/编辑表单中隐藏创建者字段，因为会自动设置:cite[3]
    def get_form(self, request, obj=None, **kwargs):
        from django import forms
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            # 对于非超级用户，隐藏创建者字段
            form.base_fields['creator'].widget = forms.HiddenInput()
        return form

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
