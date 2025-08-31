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
    list_filter = ['created_at', 'creator']
    search_fields = ['title', 'explanation']
    inlines = [EnglishWordMediaInline]
    
    def media_count(self, obj):
        return obj.media_files.count()
    media_count.short_description = '附件数量'




@admin.register(models.EnglishWordMedia)
class EnglishWordMediaAdmin(admin.ModelAdmin):
    """英文单词多媒体文件管理"""
    list_display = ['word', 'file', 'uploaded_at']
    list_filter = ['uploaded_at', 'word']
    search_fields = ['word__title', 'file']
    actions = None  # 禁用批量操作
    
    def has_delete_permission(self, request, obj=None):
        # 禁止删除多媒体文件
        return False
    
    def get_readonly_fields(self, request, obj=None):
        # 在编辑页面中，将word字段设置为只读
        if obj:  # obj存在表示正在编辑现有对象
            return ['word'] + list(super().get_readonly_fields(request, obj))
        return super().get_readonly_fields(request, obj)

















