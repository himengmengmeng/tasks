from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from rest_framework import serializers
from core.models import User
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import generics  # 确保导入了 generics





class UserCreateSerializer(BaseUserCreateSerializer):
    position = serializers.CharField(max_length=255, required=False)
    age = serializers.IntegerField(required=False)

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'position', 'age', 'password']

class UserSerializer(BaseUserSerializer):
    position = serializers.CharField(max_length=255, required=False)
    age = serializers.IntegerField(required=False)

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'position', 'age']

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.position = validated_data.get('position', instance.position)
        instance.age = validated_data.get('age', instance.age)
        instance.save()
        return instance


