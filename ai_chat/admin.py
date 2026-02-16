from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('role', 'content', 'tool_calls', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'creator', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'creator__username')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'short_content', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content',)

    def short_content(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
    short_content.short_description = "Content"
