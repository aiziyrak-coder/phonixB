from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import TranslationRequest
from .serializers import TranslationRequestSerializer


class TranslationRequestViewSet(viewsets.ModelViewSet):
    queryset = TranslationRequest.objects.all()
    serializer_class = TranslationRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['super_admin', 'reviewer']:
            return TranslationRequest.objects.all()
        return TranslationRequest.objects.filter(author=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
