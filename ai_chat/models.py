from django.db import models
from django.conf import settings


class Conversation(models.Model):
    """AI Chat conversation model"""
    name = models.CharField(max_length=255, blank=True, default="")
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="Creator"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ['-updated_at']

    def __str__(self):
        return self.name or f"Conversation {self.id}"


class Message(models.Model):
    """AI Chat message model"""
    ROLE_CHOICES = [
        ("human", "Human"),
        ("ai", "AI"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Conversation"
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name="Role"
    )
    content = models.TextField(verbose_name="Content")
    tool_calls = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Tool Calls"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}..."
