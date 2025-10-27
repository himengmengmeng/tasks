from django.contrib import admin
from django import forms
from .models import Goal, Task, GoalAttachment, TaskAttachment, Tag  # <font color="red">**新增点：导入Tag模型**</font>

# <font color="red">**新增点：标签过滤器**</font>
class TagFilter(admin.SimpleListFilter):
    """按标签过滤目标"""
    title = 'Tags'
    parameter_name = 'tag'

    def lookups(self, request, model_admin):
        # 根据用户权限返回不同的标签选项
        if request.user.is_superuser:
            tags = Tag.objects.all()
        else:
            tags = Tag.objects.filter(creator=request.user)
        return [(tag.id, tag.name) for tag in tags.distinct()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tags__id=self.value())
        return queryset

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
    # <font color="red">**修改点：在列表显示中添加标签**</font>
    list_display = ['title', 'creator', 'priority', 'urgency', 'status', 'created_time', 'get_tag_names']
    
    # <font color="red">**修改点：在过滤器中添加标签过滤器**</font>
    list_filter = ['priority', 'urgency', 'status', 'created_time', TagFilter]
    
    # <font color="red">**修改点：在搜索字段中添加标签**</font>
    search_fields = ['title', 'description', 'notes', 'priority', 'urgency', 'tags__name']
    
    readonly_fields = ['created_time']
    inlines = [TaskInline]
    
    # <font color="red">**修改点：在表单字段中添加标签**</font>
    filter_horizontal = ['tags']  # 水平多选标签
    
    # 修改：字段显示顺序，将新字段放在合适的位置
    fields = [
        'title', 'priority', 'urgency', 'status', 
        'description', 'notes', 'tags', 'created_time'  # <font color="red">**新增点：添加tags字段**</font>
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
    
    # <font color="red">**新增点：重写表单字段的queryset，限制标签选择范围**</font>
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "tags":
            # 根据用户权限过滤可选的标签
            if request.user.is_superuser:
                # 管理员可以看到所有标签
                kwargs["queryset"] = Tag.objects.all()
            else:
                # 普通用户只能看到自己创建的标签
                kwargs["queryset"] = Tag.objects.filter(creator=request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    # <font color="red">**修改点：在列表显示中添加标签**</font>
    list_display = ['name', 'goal', 'creator', 'priority', 'urgency', 'status', 'created_time', 'get_tag_names']
    
    # <font color="red">**修改点：在过滤器中添加标签过滤器**</font>
    list_filter = ['priority', 'urgency', 'status', 'created_time', TagFilter]
    
    # <font color="red">**修改点：在搜索字段中添加标签**</font>
    search_fields = ['name', 'description', 'priority', 'urgency', 'tags__name']
    
    readonly_fields = ['created_time']
    
    # <font color="red">**修改点：在表单字段中添加标签**</font>
    filter_horizontal = ['tags']  # 水平多选标签
    
    # 修改：字段显示顺序，将新字段放在合适的位置
    fields = [
        'name', 'goal', 'priority', 'urgency', 'status',
        'description', 'tags', 'created_time'  # <font color="red">**新增点：添加tags字段**</font>
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
    
    # <font color="red">**新增点：重写表单字段的queryset，限制标签选择范围**</font>
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "tags":
            # 根据用户权限过滤可选的标签
            if request.user.is_superuser:
                # 管理员可以看到所有标签
                kwargs["queryset"] = Tag.objects.all()
            else:
                # 普通用户只能看到自己创建的标签
                kwargs["queryset"] = Tag.objects.filter(creator=request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

# <font color="red">**新增点：注册Tag模型到Admin**</font>
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """标签管理"""
    list_display = ['name', 'creator', 'created_at', 'goal_count', 'task_count']
    list_filter = ['created_at']
    search_fields = ['name', 'creator__username']
    actions = None  # 禁用批量操作
    
    # 排除创建者字段，使其不在表单中显示
    exclude = ['creator']
    
    def save_model(self, request, obj, form, change):
        # 如果是新创建的标签，自动设置创建者为当前用户
        if not obj.pk:
            obj.creator = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('creator')
        # 如果是超级用户，显示所有标签
        if request.user.is_superuser:
            return qs
        # 否则只显示当前用户创建的标签
        return qs.filter(creator=request.user)
    
    def has_change_permission(self, request, obj=None):
        # 如果是超级用户，允许编辑所有标签
        if request.user.is_superuser:
            return True
        # 如果obj存在，只允许创建者编辑
        if obj is not None and obj.creator != request.user:
            return False
        return True
    
    def has_delete_permission(self, request, obj=None):
        # 同样应用编辑权限规则到删除权限
        return self.has_change_permission(request, obj)

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
