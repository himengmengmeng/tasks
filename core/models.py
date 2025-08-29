from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


class User(AbstractUser):
    email = models.EmailField(unique=True)
    position = models.CharField(max_length=255)  
    age = models.PositiveIntegerField(null=True, blank=True)  
    