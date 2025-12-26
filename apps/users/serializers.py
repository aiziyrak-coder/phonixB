from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    gamification_profile = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = (
            'id', 'phone', 'email', 'first_name', 'last_name', 'patronymic',
            'role', 'orcid_id', 'affiliation', 'avatar_url', 'telegram_username',
            'gamification_profile', 'specializations', 'reviews_completed',
            'average_review_time', 'acceptance_rate', 'password', 'is_active',
            'date_joined'
        )
        read_only_fields = ('id', 'date_joined', 'gamification_profile')
    
    def get_gamification_profile(self, obj):
        return {
            'level': obj.gamification_level,
            'badges': obj.gamification_badges,
            'points': obj.gamification_points
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = User
        fields = (
            'phone', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'patronymic', 'affiliation', 'orcid_id'
        )
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        phone = attrs.get('phone')
        password = attrs.get('password')
        
        if phone and password:
            user = authenticate(request=self.context.get('request'),
                              username=phone, password=password)
            if not user:
                raise serializers.ValidationError('Invalid phone or password')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
        else:
            raise serializers.ValidationError('Must include phone and password')
        
        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Detailed serializer for user profile"""
    
    gamification_profile = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'phone', 'email', 'first_name', 'last_name', 'patronymic',
            'full_name', 'role', 'orcid_id', 'affiliation', 'avatar_url',
            'telegram_username', 'gamification_profile', 'specializations',
            'reviews_completed', 'average_review_time', 'acceptance_rate',
            'is_active', 'date_joined', 'last_login'
        )
        read_only_fields = fields
    
    def get_gamification_profile(self, obj):
        return {
            'level': obj.gamification_level,
            'badges': obj.gamification_badges,
            'points': obj.gamification_points
        }
    
    def get_full_name(self, obj):
        return obj.get_full_name()
