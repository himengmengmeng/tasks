from admin_ordering.models import BaseOrdering
from .models import Tag, Goal, Task

class TagOrdering(BaseOrdering):
    class Meta:
        ordering = 1

class GoalOrdering(BaseOrdering):
    class Meta:
        ordering = 2

class TaskOrdering(BaseOrdering):
    class Meta:
        ordering = 3