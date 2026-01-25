from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q, Sum
from django.conf import settings
from apps.articles.models import Article
from apps.payments.models import Transaction
from apps.journals.models import Journal
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer, UserProfileSerializer
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'profile':
            return UserProfileSerializer
        return UserSerializer
    
    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """Get current user profile"""
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """Update current user profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        """Get platform statistics for super admin dashboard"""
        if request.user.role != 'super_admin':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Optimize queries - use select_related and prefetch_related where possible
        # Get user statistics (optimized with single query)
        user_stats = User.objects.aggregate(
            total=Count('id'),
            authors=Count('id', filter=Q(role='author')),
            reviewers=Count('id', filter=Q(role='reviewer'))
        )
        total_users = user_stats['total'] or 0
        authors_count = user_stats['authors'] or 0
        reviewers_count = user_stats['reviewers'] or 0
        
        # Get article statistics (optimized with single query)
        article_stats = Article.objects.aggregate(
            total=Count('id'),
            new_submissions=Count('id', filter=Q(status__in=['Yangi', 'WithEditor'])),
            in_review=Count('id', filter=Q(status='QabulQilingan')),
            published=Count('id', filter=Q(status='Published')),
            rejected=Count('id', filter=Q(status='Rejected'))
        )
        total_articles = article_stats['total'] or 0
        new_submissions = article_stats['new_submissions'] or 0
        in_review = article_stats['in_review'] or 0
        published = article_stats['published'] or 0
        rejected = article_stats['rejected'] or 0
        
        # Get financial statistics (optimized)
        financial_stats = Transaction.objects.filter(
            status='completed'
        ).exclude(
            service_type='top_up'
        ).aggregate(
            total_revenue=Sum('amount'),
            total_count=Count('id')
        )
        total_revenue = abs(float(financial_stats['total_revenue'] or 0))
        total_transactions = financial_stats['total_count'] or 0
        
        # Get journal admin statistics (optimized with select_related)
        journal_admins = User.objects.filter(role='journal_admin').select_related()
        journal_admin_stats = []
        for admin in journal_admins:
            # Use optimized query with select_related
            published_count = Article.objects.filter(
                journal__journal_admin=admin,
                status='Published'
            ).count()
            journal_admin_stats.append({
                'id': str(admin.id),
                'first_name': admin.first_name or '',
                'last_name': admin.last_name or '',
                'avatar_url': admin.avatar_url.url if (admin.avatar_url and hasattr(admin.avatar_url, 'url')) else None,
                'published_count': published_count
            })
        
        stats_data = {
            'users': {
                'total': total_users,
                'authors': authors_count,
                'reviewers': reviewers_count
            },
            'articles': {
                'total': total_articles,
                'new_submissions': new_submissions,
                'in_review': in_review,
                'published': published,
                'rejected': rejected
            },
            'finance': {
                'total_revenue': total_revenue,
                'total_transactions': total_transactions
            },
            'journal_admins': journal_admin_stats
        }
        
        return Response(stats_data)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def register(request):
    """Register a new user"""
    import logging
    import json
    logger = logging.getLogger(__name__)
    
    try:
        # Log incoming request data
        logger.info(f"=== Registration request received ===")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Method: {request.method}")
        logger.info(f"Has request.data: {hasattr(request, 'data')}")
        
        # Parse request data - DRF should handle this, but ensure it works
        data = None
        if hasattr(request, 'data') and request.data:
            data = request.data
            logger.info(f"Using request.data: {data}")
        elif hasattr(request, 'body') and request.body:
            try:
                data = json.loads(request.body.decode('utf-8'))
                logger.info(f"Parsed from body: {data}")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"JSON decode error: {e}, body: {request.body[:200]}")
                return Response({'detail': 'Invalid JSON format', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.error("No request data found - both request.data and request.body are empty")
            return Response({'detail': 'No data provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not data:
            logger.error("Data is None or empty after parsing")
            return Response({'detail': 'No data provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"Processing registration with data: {list(data.keys())}")
        serializer = RegisterSerializer(data=data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                refresh = RefreshToken.for_user(user)
                logger.info(f"✅ User registered successfully: {user.phone}, {user.email}")
                return Response({
                    'user': UserSerializer(user, context={'request': request}).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }, status=status.HTTP_201_CREATED)
            except Exception as db_error:
                import traceback
                from django.db import IntegrityError
                error_trace = traceback.format_exc()
                logger.error(f"❌ Database error during registration: {str(db_error)}")
                logger.error(f"Traceback: {error_trace}")
                
                # Handle unique constraint violations
                if isinstance(db_error, IntegrityError):
                    error_msg = str(db_error)
                    if 'phone' in error_msg.lower() or 'users_user.phone' in error_msg:
                        return Response({
                            'phone': ['Bu telefon raqam allaqachon ro\'yxatdan o\'tgan']
                        }, status=status.HTTP_400_BAD_REQUEST)
                    elif 'email' in error_msg.lower() or 'users_user.email' in error_msg:
                        return Response({
                            'email': ['Bu email allaqachon ro\'yxatdan o\'tgan']
                        }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({
                            'detail': 'Bu ma\'lumotlar allaqachon mavjud',
                            'error': error_msg
                        }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # Don't expose internal error details to user
                    logger.error(f"Database error (non-IntegrityError): {str(db_error)}")
                    return Response({
                        'detail': 'Ro\'yxatdan o\'tishda xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.',
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.warning(f"Registration validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Registration exception: {str(e)}")
        logger.error(f"Traceback: {error_trace}")
        # Don't expose internal error details to user
        return Response({
            'detail': 'Ro\'yxatdan o\'tishda xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def login(request):
    """Login user"""
    import logging
    import json
    logger = logging.getLogger(__name__)
    
    try:
        # Parse request data - handle both request.data and request.body
        data = None
        if hasattr(request, 'data') and request.data:
            data = request.data
        elif hasattr(request, 'body') and request.body:
            try:
                data = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"JSON decode error in login: {e}, body: {request.body[:200] if hasattr(request, 'body') else 'N/A'}")
                return Response({
                    'detail': 'Invalid JSON format',
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if not data:
            logger.error("No data provided in login request")
            return Response({
                'detail': 'No data provided. Please send phone and password.',
                'non_field_errors': ['Telefon raqam va parol kiritilishi shart']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"Login attempt - phone: {str(data.get('phone', 'N/A'))[:15]}..., has password: {bool(data.get('password'))}")
        
        serializer = LoginSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            logger.info(f"Login successful for user: {user.phone}")
            return Response({
                'user': UserSerializer(user, context={'request': request}).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        else:
            logger.warning(f"Login validation failed: {serializer.errors}")
            # Return detailed validation errors
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Login exception: {str(e)}", exc_info=True)
        return Response({
            'non_field_errors': ['Tizimga kirishda xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.'],
            'detail': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)