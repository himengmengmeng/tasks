import collections
from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.viewsets import ModelViewSet
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from django_filters.rest_framework import FilterSet
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import OrderingFilter
from rest_framework.exceptions import ValidationError
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework import viewsets
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework import generics
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
















