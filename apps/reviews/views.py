from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import PeerReview
from .serializers import PeerReviewSerializer


class PeerReviewViewSet(viewsets.ModelViewSet):
    queryset = PeerReview.objects.all()
    serializer_class = PeerReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role == 'reviewer':
            return PeerReview.objects.filter(reviewer=self.request.user)
        elif self.request.user.role in ['super_admin', 'journal_admin']:
            return PeerReview.objects.all()
        return PeerReview.objects.filter(article__author=self.request.user)
