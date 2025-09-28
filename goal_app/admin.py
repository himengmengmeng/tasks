from django.contrib import admin
from django import forms
from .models import Goal, Task

class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    show_change_link = True
    exclude = ['creator']  # Hide creator field in the inline
    
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
    list_display = ['title', 'creator', 'status', 'created_time']
    list_filter = ['status', 'created_time', 'creator']
    search_fields = ['title', 'description', 'notes']  # 这里确保Goal有搜索字段
    readonly_fields = ['created_time']
    inlines = [TaskInline]
    
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
    list_display = ['name', 'goal', 'creator', 'status', 'created_time']
    list_filter = ['status', 'created_time', 'goal', 'creator']
    search_fields = ['name', 'description']
    readonly_fields = ['created_time']
    
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
