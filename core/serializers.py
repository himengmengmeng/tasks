from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.validators import UniqueValidator

User = get_user_model()

class UserCreateSerializer(BaseUserCreateSerializer):
    position = serializers.CharField(max_length=255, required=False, default="")
    age = serializers.IntegerField(required=False, allow_null=True)
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'position', 'age', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}
        }

    def create(self, validated_data):
        # 确保邮箱被设置
        if 'email' not in validated_data:
            raise serializers.ValidationError({"email": "This field is required."})
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            position=validated_data.get('position', ''),
            age=validated_data.get('age', None)
        )
        return user

class UserSerializer(BaseUserCreateSerializer):
    position = serializers.CharField(max_length=255, required=False)
    age = serializers.IntegerField(required=False, allow_null=True)

    class Meta(BaseUserCreateSerializer.Meta):
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




