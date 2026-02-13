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
    
    password = serializers.CharField(write_only=True, min_length=6)  # Osonlashtirilgan: 6 belgi kifoya
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    affiliation = serializers.CharField(required=False, allow_blank=True, default='N/A')  # Ixtiyoriy
    phone = serializers.CharField(required=True, max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True, max_length=255)  # Ixtiyoriy - avtomatik yaratiladi
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    
    class Meta:
        model = User
        fields = (
            'phone', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'patronymic', 'affiliation', 'orcid_id'
        )
    
    def validate_phone(self, value):
        """Normalize and validate phone number"""
        if not value:
            raise serializers.ValidationError('Telefon raqam kiritilishi shart')
        
        # Remove spaces and normalize
        cleaned_phone = str(value).strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Remove + sign if present
        if cleaned_phone.startswith('+'):
            cleaned_phone = cleaned_phone[1:]
        
        # Validate phone number format (should be 9-12 digits)
        if not cleaned_phone.isdigit():
            raise serializers.ValidationError('Telefon raqam faqat raqamlardan iborat bo\'lishi kerak')
        
        if len(cleaned_phone) < 9 or len(cleaned_phone) > 12:
            raise serializers.ValidationError('Telefon raqam noto\'g\'ri formatda')
        
        # Ensure it starts with 998 for Uzbekistan
        if not cleaned_phone.startswith('998') and len(cleaned_phone) == 9:
            cleaned_phone = '998' + cleaned_phone
        
        return cleaned_phone
    
    def validate_password(self, value):
        """Validate password strength - OSON PAROL TALABLARI"""
        if not value:
            raise serializers.ValidationError('Parol kiritilishi shart')
        
        # Minimal 6 ta belgi kifoya (osonlashtirilgan)
        if len(value) < 6:
            raise serializers.ValidationError('Parol kamida 6 ta belgidan iborat bo\'lishi kerak')
        
        # Raqam va harf talab qilinmaydi - har qanday belgilar kifoya
        # Bu ro'yxatdan o'tishni osonlashtiradi
        
        return value
    
    def validate_email(self, value):
        """Validate email format - Ixtiyoriy"""
        if not value or not value.strip():
            return ''  # Bo'sh bo'lishi mumkin, avtomatik yaratiladi
        
        # Basic email validation (Django's EmailField already does this, but add extra check)
        if '@' not in value or '.' not in value.split('@')[1]:
            raise serializers.ValidationError('Email noto\'g\'ri formatda')
        
        return value.lower().strip()
    
    def validate(self, attrs):
        """Cross-field validation"""
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        
        if password != password_confirm:
            raise serializers.ValidationError({"password": "Parollar mos kelmaydi"})
        
        # Ensure affiliation is not empty (can be optional but if provided, must be valid)
        affiliation = attrs.get('affiliation', '').strip()
        if not affiliation:
            attrs['affiliation'] = 'N/A'  # Default value if empty
        
        # Email bo'lmasa, avtomatik yaratish (telefon raqamdan + timestamp)
        email = attrs.get('email', '').strip()
        if not email:
            import time
            phone = attrs.get('phone', '').strip()
            timestamp = int(time.time())
            attrs['email'] = f"{phone}_{timestamp}@temp.phoenix.uz"  # Unique email
        
        # Validate first_name and last_name are not empty
        if not attrs.get('first_name', '').strip():
            raise serializers.ValidationError({"first_name": "Ism kiritilishi shart"})
        
        if not attrs.get('last_name', '').strip():
            raise serializers.ValidationError({"last_name": "Familiya kiritilishi shart"})
        
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
            raise serializers.ValidationError({'non_field_errors': ['Telefon raqam va parol kiritilishi shart']})
        
        if not password or not password.strip():
            raise serializers.ValidationError({'non_field_errors': ['Parol bo\'sh bo\'lishi mumkin emas']})
        
        # Normalize phone number - extract only digits
        phone_digits = ''.join(filter(str.isdigit, str(phone).strip()))
        
        if not phone_digits or len(phone_digits) < 9:
            raise serializers.ValidationError({'phone': ['Telefon raqam noto\'g\'ri formatda']})
        
        # Ensure phone number is in 998XXXXXXXXX format (12 digits)
        # Handle different phone number formats
        if len(phone_digits) == 9:
            # 9 digits: 901234567 -> 998901234567
            phone_digits = '998' + phone_digits
        elif len(phone_digits) == 10 and phone_digits.startswith('9'):
            # 10 digits starting with 9: 9901234567 -> 998901234567
            phone_digits = '998' + phone_digits
        elif len(phone_digits) == 11:
            # 11 digits: could be 99890123456 (missing last digit) or 99012345678
            if phone_digits.startswith('998'):
                # Already has 998 prefix, might be missing last digit
                pass
            else:
                # Add 998 prefix
                phone_digits = '998' + phone_digits[-9:]  # Take last 9 digits
        elif len(phone_digits) == 12:
            # 12 digits: should be 998901234567
            if not phone_digits.startswith('998'):
                # If doesn't start with 998, take last 9 digits and add 998
                phone_digits = '998' + phone_digits[-9:]
        elif len(phone_digits) > 12:
            # More than 12 digits: take last 12 digits
            phone_digits = phone_digits[-12:]
        
        # Final validation: should be 12 digits starting with 998
        if len(phone_digits) != 12 or not phone_digits.startswith('998'):
            raise serializers.ValidationError({'phone': ['Telefon raqam noto\'g\'ri formatda. Format: 998XXXXXXXXX']})
        
        # Try to authenticate with different phone formats
        # Database may store phone with + or without +
        user = None
        
        # Try 1: With + prefix (most common in database) - 998XXXXXXXXX format
        user = authenticate(request=self.context.get('request'),
                          username=f'+{phone_digits}', password=password)
        
        # Try 2: Without + prefix - 998XXXXXXXXX format
        if not user:
            user = authenticate(request=self.context.get('request'),
                              username=phone_digits, password=password)
        
        # Try 3: With + prefix but without country code - 9XXXXXXXX format (if phone_digits is 12, try last 9)
        if not user and len(phone_digits) == 12:
            last_9_digits = phone_digits[-9:]
            user = authenticate(request=self.context.get('request'),
                              username=f'+{last_9_digits}', password=password)
            if not user:
                user = authenticate(request=self.context.get('request'),
                                  username=last_9_digits, password=password)
        
        # Try 4: Original format if it was different
        if not user and phone != phone_digits and phone != f'+{phone_digits}':
            # Try original phone as-is
            user = authenticate(request=self.context.get('request'),
                              username=phone, password=password)
            # Try original phone with + prefix
            if not user and not phone.startswith('+'):
                user = authenticate(request=self.context.get('request'),
                                  username=f'+{phone}', password=password)
        
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
