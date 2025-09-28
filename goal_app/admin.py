from django.contrib import admin
from django import forms
from .models import Goal, Task, GoalAttachment, TaskAttachment
from django.contrib.auth.models import User

class GoalAttachmentInline(admin.TabularInline):
    model = GoalAttachment
    extra = 1

class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 1

class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    show_change_link = True

class GoalAdminForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = '__all__'

class TaskAdminForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = '__all__'

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    form = GoalAdminForm
    list_display = ['title', 'creator', 'status', 'created_time']
    list_filter = ['status', 'created_time', 'creator']
    search_fields = ['title', 'description', 'notes']
    readonly_fields = ['created_time']
    inlines = [GoalAttachmentInline, TaskInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creator = request.user
        super().save_model(request, obj, form, change)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    form = TaskAdminForm
    list_display = ['name', 'goal', 'status', 'created_time']
    list_filter = ['status', 'created_time', 'goal']
    search_fields = ['name', 'description']
    readonly_fields = ['created_time']
    inlines = [TaskAttachmentInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(goal__creator=request.user)

@admin.register(GoalAttachment)
class GoalAttachmentAdmin(admin.ModelAdmin):
    list_display = ['goal', 'file', 'uploaded_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(goal__creator=request.user)

@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ['task', 'file', 'uploaded_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(task__goal__creator=request.user)

