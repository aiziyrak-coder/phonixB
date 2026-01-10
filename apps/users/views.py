from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
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
        
        # Get user statistics
        total_users = User.objects.count()
        authors_count = User.objects.filter(role='author').count()
        reviewers_count = User.objects.filter(role='reviewer').count()
        
        # Get article statistics
        total_articles = Article.objects.count()
        new_submissions = Article.objects.filter(status__in=['Yangi', 'WithEditor']).count()
        in_review = Article.objects.filter(status='QabulQilingan').count()
        published = Article.objects.filter(status='Published').count()
        rejected = Article.objects.filter(status='Rejected').count()
        
        # Get financial statistics
        completed_transactions = Transaction.objects.filter(status='completed').exclude(service_type='top_up')
        total_revenue = sum(abs(float(t.amount)) for t in completed_transactions)
        
        # Get journal admin statistics
        journal_admins = User.objects.filter(role='journal_admin')
        journal_admin_stats = []
        for admin in journal_admins:
            managed_journals = Journal.objects.filter(journal_admin=admin.id)
            managed_journal_ids = list(managed_journals.values_list('id', flat=True))
            published_count = Article.objects.filter(
                journal__in=managed_journal_ids, 
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
                'total_transactions': completed_transactions.count()
            },
            'journal_admins': journal_admin_stats
        }
        
        return Response(stats_data)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login user"""
    serializer = LoginSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)