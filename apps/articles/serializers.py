from rest_framework import serializers
from .models import Article, ArticleVersion, ActivityLog
from apps.users.serializers import UserSerializer


class ArticleVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleVersion
        fields = '__all__'


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ActivityLog
        fields = '__all__'
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else 'System'


class ArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    journal_name = serializers.SerializerMethodField()
    versions = ArticleVersionSerializer(many=True, read_only=True)
    activity_logs = ActivityLogSerializer(many=True, read_only=True)
    analytics = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    workflow_stage = serializers.SerializerMethodField()
    workflow_steps = serializers.SerializerMethodField()
    status_timeline = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = '__all__'
        read_only_fields = ('id', 'submission_date', 'views_count', 'downloads_count', 'citations_count')
    
    def get_author_name(self, obj):
        return obj.author.get_full_name()
    
    def get_journal_name(self, obj):
        return obj.journal.name
    
    def get_analytics(self, obj):
        return {
            'views': obj.views_count,
            'downloads': obj.downloads_count,
            'citations': obj.citations_count
        }

    def _is_book_submission(self, obj):
        return (obj.title or '').strip().startswith('[KITOB]')

    def _status_labels(self):
        return {
            'Draft': 'Yangi topshirildi',
            'Yangi': 'Yangi topshirildi',
            'WithEditor': 'Tekshiruvda',
            'Revision': 'To‘ldirish talab qilinadi',
            'QabulQilingan': 'Ko‘rib chiqilmoqda',
            'WritingInProgress': 'Tuzatish kiritilmoqda',
            'Accepted': 'Qabul qilindi',
            'NashrgaYuborilgan': 'Nashrga tayyorlanmoqda',
            'Published': 'Nashr etildi',
            'Rejected': 'Jarayon to‘xtatildi',
            # Book-specific extension statuses
            'ContractProcessing': 'Shartnoma rasmiylashtirilmoqda',
            'IsbnProcessing': 'ISBN olinmoqda',
            'AuthorDataVerified': 'Muallif ma’lumotlari tasdiqlandi',
            'PaymentCompleted': 'To‘lov jarayoni yakunlandi',
            'SentToPrint': 'Bosmaga berildi',
            'Printing': 'Chop etilmoqda',
            'Ready': 'Tayyor',
            'Packaging': 'Qadoqlanmoqda',
            'Shipping': 'Yuborilmoqda (pochta)',
            'Delivered': 'Yetkazildi',
            'ProcessPaused': 'Jarayon to‘xtatildi',
        }

    def _workflow_steps_by_type(self, is_book):
        article_steps = ['Topshirildi', 'Tekshiruv', 'Muharrirlik', 'Nashr']
        if not is_book:
            return article_steps
        return article_steps + ['Yetkazish']

    def _stage_index_by_status(self, status_value, is_book):
        common_map = {
            'Draft': 0,
            'Yangi': 0,
            'WithEditor': 1,
            'Revision': 1,
            'QabulQilingan': 2,
            'WritingInProgress': 2,
            'Accepted': 2,
            'NashrgaYuborilgan': 3,
            'Published': 3,
            'Rejected': 3,
            'ProcessPaused': 3,
        }

        if is_book:
            book_map = {
                'ContractProcessing': 1,
                'IsbnProcessing': 1,
                'AuthorDataVerified': 1,
                'PaymentCompleted': 1,
                'SentToPrint': 3,
                'Printing': 3,
                'Ready': 3,
                'Packaging': 4,
                'Shipping': 4,
                'Delivered': 4,
            }
            common_map.update(book_map)

        return common_map.get(status_value, 0)

    def get_status_label(self, obj):
        return self._status_labels().get(obj.status, obj.status)

    def get_workflow_stage(self, obj):
        is_book = self._is_book_submission(obj)
        current_idx = self._stage_index_by_status(obj.status, is_book)
        steps = self._workflow_steps_by_type(is_book)
        return steps[min(current_idx, len(steps) - 1)]

    def get_workflow_steps(self, obj):
        is_book = self._is_book_submission(obj)
        steps = self._workflow_steps_by_type(is_book)
        current_idx = self._stage_index_by_status(obj.status, is_book)

        items = []
        for idx, step in enumerate(steps):
            items.append({
                'name': step,
                'done': idx < current_idx,
                'current': idx == current_idx,
            })
        return items

    def get_status_timeline(self, obj):
        timeline = [{
            'status': 'Yangi topshirildi',
            'date': obj.submission_date,
            'comment': 'Maqola muallif tomonidan tizimga yuklandi.',
            'responsible': obj.author.get_full_name() if obj.author else 'Muallif',
        }]

        status_labels = self._status_labels()
        logs = obj.activity_logs.all().order_by('-timestamp')[:50]
        for log in logs:
            if not log.action:
                continue

            if 'Status changed from' in log.action:
                parts = log.action.split(' to ')
                new_status = parts[-1].strip() if parts else ''
                timeline.append({
                    'status': status_labels.get(new_status, new_status or 'Status yangilandi'),
                    'date': log.timestamp,
                    'comment': log.details or 'Status o‘zgartirildi',
                    'responsible': log.user.get_full_name() if log.user else 'Tizim',
                })
            elif self._is_book_submission(obj) and log.action in status_labels:
                timeline.append({
                    'status': status_labels.get(log.action, log.action),
                    'date': log.timestamp,
                    'comment': log.details or '',
                    'responsible': log.user.get_full_name() if log.user else 'Tizim',
                })

        return timeline


class CreateArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ('title', 'abstract', 'keywords', 'journal', 'final_pdf_path', 
                  'additional_document_path', 'page_count', 'fast_track')
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['status'] = 'Draft'
        return super().create(validated_data)


class PublicArticleShareSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    journal_name = serializers.SerializerMethodField()
    publication_link = serializers.SerializerMethodField()
    certificate_download_link = serializers.SerializerMethodField()
    plagiarism_history = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            'id',
            'title',
            'status',
            'doi',
            'submission_date',
            'author_name',
            'journal_name',
            'publication_link',
            'certificate_download_link',
            'plagiarism_history',
        )

    def _build_absolute_url(self, value):
        if not value:
            return ''

        value_str = str(value)
        if value_str.startswith('http://') or value_str.startswith('https://'):
            return value_str

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(value_str)

        return value_str

    def get_author_name(self, obj):
        return obj.author.get_full_name() if obj.author else ''

    def get_journal_name(self, obj):
        return obj.journal.name if obj.journal else ''

    def get_publication_link(self, obj):
        return self._build_absolute_url(obj.publication_url)

    def get_certificate_download_link(self, obj):
        # publication_certificate_url is primary for publication certificate sharing
        if obj.publication_certificate_url:
            return self._build_absolute_url(obj.publication_certificate_url)

        # fallback to certificate_url if publication-specific one is not provided
        return self._build_absolute_url(obj.certificate_url)

    def get_plagiarism_history(self, obj):
        import re

        history = []
        logs = obj.activity_logs.filter(action='Plagiarism check completed').order_by('-timestamp')[:20]

        for log in logs:
            plagiarism_percentage = None
            ai_content_percentage = None

            if log.details:
                plagiarism_match = re.search(r'Plagiarism:\s*([\d.]+)%', log.details)
                ai_match = re.search(r'AI\s*Content:\s*([\d.]+)%', log.details)

                if plagiarism_match:
                    plagiarism_percentage = float(plagiarism_match.group(1))
                if ai_match:
                    ai_content_percentage = float(ai_match.group(1))

            history.append({
                'checked_at': log.timestamp,
                'plagiarism_percentage': plagiarism_percentage,
                'ai_content_percentage': ai_content_percentage,
                'details': log.details or '',
            })

        return history
