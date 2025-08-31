from functools import partial, partialmethod
from typing import Any
from unittest import case
from django.db.models import Count, Sum, Case, When, IntegerField
from django.contrib import admin
from django.db.models.query import QuerySet
from django.forms import IntegerField
from django.http.request import HttpRequest
from . import models
from django.db.models.aggregates import Count, Max, Min, Sum
from django.db.models import F
from django.utils.html import format_html
from urllib.parse import urlencode
from django.urls import reverse
from django.db.models.functions import Concat
from django.db.models.fields import CharField
from django.db.models import F, Count, Sum, Value
from django.utils.translation import gettext_lazy as _
from django.db.models.functions import Concat

class EnglishWordMediaInline(admin.TabularInline):
    """单词多媒体文件内联管理"""
    model = models.EnglishWordMedia
    extra = 1
    fields = ['file', 'uploaded_at']
    readonly_fields = ['uploaded_at']
    can_delete = False  # 禁止删除已上传的附件

@admin.register(models.EnglishWord)
class EnglishWordAdmin(admin.ModelAdmin):
    """英文单词管理"""
    list_display = ['title', 'creator', 'created_at', 'media_count']
    list_filter = ['created_at']
    search_fields = ['title', 'explanation', 'creator__username', 'creator__first_name', 'creator__last_name']
    inlines = [EnglishWordMediaInline]
    
    # 排除创建者字段，使其不在表单中显示
    exclude = ['creator']
    
    def media_count(self, obj):
        return obj.media_files.count()
    media_count.short_description = '附件数量'
    
    def save_model(self, request, obj, form, change):
        # 如果是新创建的单词，自动设置创建者为当前用户
        if not obj.pk:
            obj.creator = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('creator')
        # 如果是超级用户，显示所有单词
        if request.user.is_superuser:
            return qs
        # 否则只显示当前用户创建的单词
        return qs.filter(creator=request.user)
    
    def has_change_permission(self, request, obj=None):
        # 如果是超级用户，允许编辑所有单词
        if request.user.is_superuser:
            return True
        # 如果obj存在，只允许创建者编辑
        if obj is not None and obj.creator != request.user:
            return False
        return True
    
    def has_delete_permission(self, request, obj=None):
        # 同样应用编辑权限规则到删除权限
        return self.has_change_permission(request, obj)

@admin.register(models.EnglishWordMedia)
class EnglishWordMediaAdmin(admin.ModelAdmin):
    """英文单词多媒体文件管理"""
    list_display = ['word', 'file', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['word__title', 'file']
    actions = None  # 禁用批量操作

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # 如果是超级用户，显示所有文件
        if request.user.is_superuser:
            return qs
        # 否则只显示当前用户创建的文件（通过关联的单词的创建者来过滤）
        return qs.filter(word__creator=request.user)

    def has_delete_permission(self, request, obj=None):
        # 超级用户拥有删除权限
        if request.user.is_superuser:
            return True
        # 如果obj存在，检查其关联的单词是否是当前用户创建的
        if obj is not None and obj.word.creator != request.user:
            return False
        return True

    def has_change_permission(self, request, obj=None):
        return self.has_delete_permission(request, obj)
    
    def get_readonly_fields(self, request, obj=None):
        # 在编辑页面中，将word字段设置为只读
        if obj:  # obj存在表示正在编辑现有对象
            return ['word'] + list(super().get_readonly_fields(request, obj))
        return super().get_readonly_fields(request, obj)

















