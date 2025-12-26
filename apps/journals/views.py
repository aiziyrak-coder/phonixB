from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Journal, JournalCategory, Issue
from .serializers import JournalSerializer, JournalCategorySerializer, IssueSerializer


class JournalCategoryViewSet(viewsets.ModelViewSet):
    queryset = JournalCategory.objects.all()
    serializer_class = JournalCategorySerializer
    permission_classes = [AllowAny]


class JournalViewSet(viewsets.ModelViewSet):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer
    permission_classes = [AllowAny]


class IssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]
