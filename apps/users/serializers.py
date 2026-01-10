from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    gamification_profile = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
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
        read_only_fields = ('id', 'date_joined', 'gamification_profile', 'avatar_url')
    
    def get_gamification_profile(self, obj):
        return {
            'level': obj.gamification_level,
            'badges': obj.gamification_badges,
            'points': obj.gamification_points
        }
    
    def get_avatar_url(self, obj):
        if obj.avatar_url and hasattr(obj.avatar_url, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar_url.url)
            return obj.avatar_url.url
        return None
    
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
    
    def validate_phone(self, value):
        """Normalize phone number - remove + sign and spaces, but keep original for validation"""
        if not value:
            raise serializers.ValidationError('Phone number is required')
        
        # Remove spaces and other non-digit characters except + and digits
        cleaned_phone = str(value).strip()
        
        if not cleaned_phone or len(cleaned_phone.replace('+', '').replace(' ', '')) < 9:
            raise serializers.ValidationError('Invalid phone number format')
        
        # Return cleaned phone (keep + sign for now, will handle in validate method)
        return cleaned_phone
    
    def validate(self, attrs):
        phone = attrs.get('phone')
        password = attrs.get('password')
        
        if not phone or not password:
            raise serializers.ValidationError({'non_field_errors': ['Must include phone and password']})
        
        if not password or not password.strip():
            raise serializers.ValidationError({'non_field_errors': ['Password cannot be empty']})
        
        # Normalize phone number - extract only digits
        phone_digits = ''.join(filter(str.isdigit, str(phone).strip()))
        
        if not phone_digits or len(phone_digits) < 9:
            raise serializers.ValidationError({'non_field_errors': ['Invalid phone number format']})
        
        # Try to authenticate with different phone formats
        # Database may store phone with + or without +
        user = None
        
        # Try 1: With + prefix (most common in database)
        user = authenticate(request=self.context.get('request'),
                          username=f'+{phone_digits}', password=password)
        
        # Try 2: Without + prefix
        if not user:
            user = authenticate(request=self.context.get('request'),
                              username=phone_digits, password=password)
        
        # Try 3: Original format if it was different
        if not user and phone != phone_digits and phone != f'+{phone_digits}':
            user = authenticate(request=self.context.get('request'),
                              username=phone, password=password)
        
        if not user:
            raise serializers.ValidationError({'non_field_errors': ['Telefon raqam yoki parol noto\'g\'ri']})
        
        if not user.is_active:
            raise serializers.ValidationError({'non_field_errors': ['Foydalanuvchi hisobi o\'chirilgan']})
        
        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Detailed serializer for user profile"""
    
    gamification_profile = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    
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
    
    def get_avatar_url(self, obj):
        if obj.avatar_url and hasattr(obj.avatar_url, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar_url.url)
            return obj.avatar_url.url
        return None
