import json
from rest_framework import serializers
from .models import Article, ArticleVersion, ActivityLog, DoiRequest, ArticleSampleRequest, ArticleOperatorMessage
from apps.users.serializers import UserSerializer
from apps.users.models import User
from apps.journals.models import Journal


def _normalize_journal_lookup_string(value: str) -> str:
    """Unicode apostrof va variantlarini ASCII ga yaqinlashtirish (TA'LIM va DB mosligi)."""
    return (
        str(value)
        .strip()
        .replace('\u2019', "'")
        .replace('\u2018', "'")
        .replace('\u02bc', "'")
        .replace('\u0060', "'")
    )


def _issn_alnum(value: str) -> str:
    return ''.join(ch for ch in value if ch.isalnum())


class JournalPKField(serializers.PrimaryKeyRelatedField):
    """Bo'sh journal ID FormData/JSON da Journal.objects.get(pk='') ORM xatosini oldini oladi."""

    default_error_messages = {
        **serializers.PrimaryKeyRelatedField.default_error_messages,
        'blank_pk': 'Jurnal tanlanishi majburiy (ID bo\'sh).',
    }

    def to_internal_value(self, data):
        if data is None:
            self.fail('required')
        raw = str(data).strip()
        if not raw:
            self.fail('blank_pk')
        s = _normalize_journal_lookup_string(raw)
        first_exc = None
        for candidate in (s, raw):
            try:
                return super().to_internal_value(candidate)
            except serializers.ValidationError as exc:
                first_exc = exc
                continue

        # Frontend ba'zan UUID o'rniga jurnal nomi yoki "__str__" ko'rinishini yuborishi mumkin.
        # Masalan: "Jurnal nomi (1230-3494)". ISSN bazada chiziqli/chiziqsiz farq qilishi mumkin.
        for label in (s, raw):
            by_name = Journal.objects.filter(name__iexact=label).first()
            if by_name:
                return by_name

        display = s if (s.endswith(')') and ' (' in s) else None
        if display is None and raw.endswith(')') and ' (' in raw:
            display = raw
        if display:
            left, _, right = display.rpartition(' (')
            issn_raw = right[:-1].strip()
            name_part = left.strip()
            if name_part and issn_raw:
                issn_digits = _issn_alnum(issn_raw)
                exact = Journal.objects.filter(name__iexact=name_part, issn__iexact=issn_raw).first()
                if exact:
                    return exact
                only_name = Journal.objects.filter(name__iexact=name_part)
                if only_name.count() == 1:
                    return only_name.first()
                cand = Journal.objects.filter(name__icontains=name_part[:120])
                for j in cand:
                    if _issn_alnum(j.issn) == issn_digits:
                        return j
                if issn_digits:
                    found_j = None
                    for j in Journal.objects.only('id', 'issn').iterator(chunk_size=200):
                        if _issn_alnum(j.issn) != issn_digits:
                            continue
                        if found_j is not None:
                            found_j = None
                            break
                        found_j = j
                    if found_j is not None:
                        return found_j

        if first_exc:
            raise first_exc
        raise serializers.ValidationError('Jurnal identifikatori noto\'g\'ri yoki jurnal topilmadi.')


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
        if not obj.user:
            return 'System'
        try:
            return getattr(obj.user, 'get_full_name', lambda: str(obj.user))() or 'System'
        except Exception:
            return 'System'


class ArticleListSerializer(serializers.ModelSerializer):
    """Minimal serializer for list action only — avoids nested/expensive fields that can cause 500."""
    author_name = serializers.SerializerMethodField()
    journal_name = serializers.SerializerMethodField()
    publication_link = serializers.SerializerMethodField()
    certificate_download_link = serializers.SerializerMethodField()
    pending_payment_transaction_id = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'abstract', 'keywords', 'status', 'author', 'journal',
            'author_name', 'journal_name', 'doi', 'submission_date', 'views_count',
            'downloads_count', 'citations_count', 'page_count', 'fast_track',
            'plagiarism_percentage', 'ai_content_percentage', 'originality_percentage', 'plagiarism_checked_at',
            'publication_url', 'publication_link', 'certificate_download_link',
            'pending_payment_transaction_id',
        )

    def get_author_name(self, obj):
        if not obj.author:
            return ''
        try:
            return getattr(obj.author, 'get_full_name', lambda: str(obj.author))()
        except Exception:
            return ''

    def get_journal_name(self, obj):
        if not obj.journal:
            return ''
        try:
            return getattr(obj.journal, 'name', '') or ''
        except Exception:
            return ''

    def _build_absolute_url_list(self, value):
        if not value:
            return ''
        value_str = str(value)
        if value_str.startswith('http://') or value_str.startswith('https://'):
            return value_str
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(value_str)
        return value_str

    def get_publication_link(self, obj):
        if not getattr(obj, 'publication_url', None):
            return ''
        return self._build_absolute_url_list(obj.publication_url)

    def get_certificate_download_link(self, obj):
        if getattr(obj, 'publication_certificate_path', None) and obj.publication_certificate_path:
            return self._build_absolute_url_list(obj.publication_certificate_path.url)
        if getattr(obj, 'publication_certificate_url', None) and obj.publication_certificate_url:
            return self._build_absolute_url_list(obj.publication_certificate_url)
        if getattr(obj, 'certificate_url', None) and obj.certificate_url:
            return self._build_absolute_url_list(obj.certificate_url)
        return ''

    def get_pending_payment_transaction_id(self, obj):
        """Muallif: to'lov kutilayotgan Draft uchun Click sahifasiga qaytish."""
        if getattr(obj, 'status', None) != 'Draft':
            return None
        try:
            from apps.payments.models import Transaction
            tx = (
                Transaction.objects.filter(
                    article_id=obj.pk,
                    service_type='publication_fee',
                    status='pending',
                )
                .order_by('-created_at')
                .first()
            )
            return str(tx.id) if tx else None
        except Exception:
            return None


class ArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    journal_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['publication_link'] = self.get_publication_link(instance)
        data['certificate_download_link'] = self.get_certificate_download_link(instance)
        return data

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

    def get_publication_link(self, obj):
        return self._build_absolute_url(obj.publication_url) if obj.publication_url else ''

    def get_certificate_download_link(self, obj):
        if getattr(obj, 'publication_certificate_path', None) and obj.publication_certificate_path:
            return self._build_absolute_url(obj.publication_certificate_path.url)
        if getattr(obj, 'publication_certificate_url', None) and obj.publication_certificate_url:
            return self._build_absolute_url(obj.publication_certificate_url)
        return self._build_absolute_url(obj.certificate_url) if getattr(obj, 'certificate_url', None) else ''
    
    def get_file_url(self, obj):
        """Return absolute URL for main PDF so frontend can open/download."""
        if not obj.final_pdf_path:
            return None
        try:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.final_pdf_path.url)
            from django.conf import settings
            base = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/')
            path = str(obj.final_pdf_path).lstrip('/')
            return f"{base}/{path}" if path else None
        except Exception:
            return None
    
    def get_author_name(self, obj):
        if not obj.author:
            return ''
        return getattr(obj.author, 'get_full_name', lambda: str(obj.author))()

    def get_journal_name(self, obj):
        if not obj.journal:
            return ''
        return getattr(obj.journal, 'name', '') or ''
    
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
            'PlagiarismReview': 'Antiplagiat ko\'rib chiqish (bosh admin qarori)',
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
        author_name = ''
        if obj.author:
            author_name = getattr(obj.author, 'get_full_name', lambda: str(obj.author))()
        timeline = [{
            'status': 'Yangi topshirildi',
            'date': obj.submission_date,
            'comment': 'Maqola muallif tomonidan tizimga yuklandi.',
            'responsible': author_name or 'Muallif',
        }]

        status_labels = self._status_labels()
        logs = obj.activity_logs.all().order_by('-timestamp')[:50]
        for log in logs:
            if not log.action:
                continue
            responsible = 'Tizim'
            if log.user:
                responsible = getattr(log.user, 'get_full_name', lambda: str(log.user))() or 'Tizim'

            if 'Status changed from' in log.action:
                parts = log.action.split(' to ')
                new_status = parts[-1].strip() if parts else ''
                timeline.append({
                    'status': status_labels.get(new_status, new_status or 'Status yangilandi'),
                    'date': log.timestamp,
                    'comment': log.details or 'Status o‘zgartirildi',
                    'responsible': responsible,
                })
            elif self._is_book_submission(obj) and log.action in status_labels:
                timeline.append({
                    'status': status_labels.get(log.action, log.action),
                    'date': log.timestamp,
                    'comment': log.details or '',
                    'responsible': responsible,
                })

        return timeline


class CreateArticleSerializer(serializers.ModelSerializer):
    journal = JournalPKField(queryset=Journal.objects.all())
    co_author_contacts = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        write_only=True,
    )

    class Meta:
        model = Article
        fields = ('id', 'title', 'abstract', 'keywords', 'journal', 'final_pdf_path',
                  'additional_document_path', 'page_count', 'fast_track', 'co_author_contacts')
        read_only_fields = ('id',)
        extra_kwargs = {
            'abstract': {'required': False, 'allow_blank': True},
        }

    def validate_keywords(self, value):
        """Accept list, JSON string (e.g. from multipart), or comma-separated string; normalize to list."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            if (value.startswith('[') and value.endswith(']')) or value.startswith('{'):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except (ValueError, TypeError):
                    pass
            return [k.strip() for k in value.split(',') if k.strip()]
        return []

    def validate_title(self, value):
        """Title is required and must not be only a file name (e.g. ending with extension, no spaces)."""
        if not value or not str(value).strip():
            raise serializers.ValidationError('Maqola mavzusi (sarlavha) majburiy.')
        title = str(value).strip()
        if len(title) < 3:
            raise serializers.ValidationError('Maqola mavzusi kamida 3 ta belgidan iborat bo\'lishi kerak.')
        lower = title.lower()
        for ext in ('.pdf', '.docx', '.doc'):
            if lower.endswith(ext):
                stem = title[: -len(ext)].strip()
                # Reject only if it looks like a bare filename (no space or very short stem)
                if not stem or ' ' not in stem and len(stem) < 15:
                    raise serializers.ValidationError(
                        'Maqola mavzusi fayl nomi emas, balki maqolaning haqiqiy sarlavhasi bo\'lishi kerak.'
                    )
                break
        return title

    def validate_co_author_contacts(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Hammualliflar ro\'yxat ko\'rinishida yuborilishi kerak.')
        normalized = []
        for row in value:
            if not isinstance(row, dict):
                continue
            identifier = str(row.get('identifier') or row.get('id') or '').strip()
            email = str(row.get('email') or '').strip().lower()
            phone = str(row.get('phone') or '').strip()
            name = str(row.get('name') or '').strip()
            if not any([identifier, email, phone]):
                continue
            normalized.append({
                'identifier': identifier,
                'email': email,
                'phone': phone,
                'name': name,
            })
        return normalized

    def _resolve_co_author_user(self, entry):
        identifier = entry.get('identifier', '')
        email = entry.get('email', '')
        phone = entry.get('phone', '')

        if identifier:
            user_by_id = User.objects.filter(id=identifier).first()
            if user_by_id:
                return user_by_id
            if '@' in identifier:
                user_by_email = User.objects.filter(email__iexact=identifier).first()
                if user_by_email:
                    return user_by_email
            user_by_phone = User.objects.filter(phone=identifier).first()
            if user_by_phone:
                return user_by_phone

        if email:
            user_by_email = User.objects.filter(email__iexact=email).first()
            if user_by_email:
                return user_by_email

        if phone:
            user_by_phone = User.objects.filter(phone=phone).first()
            if user_by_phone:
                return user_by_phone
        return None

    def create(self, validated_data):
        co_author_contacts = validated_data.pop('co_author_contacts', [])
        validated_data['author'] = self.context['request'].user
        title = (validated_data.get('title') or '').strip()
        keywords = validated_data.get('keywords') or []
        is_antiplagiat = title.lower().startswith('plagiarism check') or any(
            str(k).lower() == 'plagiarism' for k in keywords
        )
        # Mustaqil antiplagiat: Draft — keyin to'lov (language_editing) va tekshiruv; jurnal topshirig'i Yangi
        if self.context.get('awaiting_publication_payment'):
            validated_data['status'] = 'Draft'
        else:
            validated_data['status'] = 'Draft' if is_antiplagiat else 'Yangi'
        article = super().create(validated_data)

        owner_id = str(self.context['request'].user.id)
        co_author_ids = set()
        for entry in co_author_contacts:
            co_author = self._resolve_co_author_user(entry)
            if co_author and str(co_author.id) != owner_id:
                co_author_ids.add(str(co_author.id))
        if co_author_ids:
            article.co_authors.set(User.objects.filter(id__in=list(co_author_ids)))
        return article


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
        # Uploaded file is primary for publication certificate
        if getattr(obj, 'publication_certificate_path', None) and obj.publication_certificate_path:
            return self._build_absolute_url(obj.publication_certificate_path.url)
        if obj.publication_certificate_url:
            return self._build_absolute_url(obj.publication_certificate_url)
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


class DoiRequestSerializer(serializers.ModelSerializer):
    """DOI so'rovi: muallif va taqrizchi uchun."""
    file_url = serializers.SerializerMethodField()
    author_short = serializers.SerializerMethodField()

    class Meta:
        model = DoiRequest
        fields = (
            'id', 'author_first_name', 'author_last_name', 'author_short',
            'file', 'file_url', 'status', 'doi_link', 'created_at', 'completed_at',
        )
        read_only_fields = fields

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return str(obj.file.url) if obj.file else None

    def get_author_short(self, obj):
        return f"{obj.author_last_name} {obj.author_first_name}"


class ArticleSampleRequestSerializer(serializers.ModelSerializer):
    """Maqola namuna so'rovi: taqrizchi barcha submitted ni ko'radi, muallif o'zini."""
    author_short = serializers.SerializerMethodField()

    class Meta:
        model = ArticleSampleRequest
        fields = (
            'id', 'author_first_name', 'author_last_name', 'author_short',
            'requirements', 'pages', 'topic', 'quality_level', 'amount', 'status', 'created_at',
        )
        read_only_fields = fields

    def get_author_short(self, obj):
        return f"{obj.author_last_name} {obj.author_first_name}"


class ArticleOperatorMessageSerializer(serializers.ModelSerializer):
    """Muallifga operator ismi yashirin; operatorlar o‘rtasida kim yozgani ko‘rinadi."""

    display_name = serializers.SerializerMethodField()
    is_from_author = serializers.SerializerMethodField()

    class Meta:
        model = ArticleOperatorMessage
        fields = ('id', 'body', 'created_at', 'display_name', 'is_from_author')
        read_only_fields = fields

    def get_is_from_author(self, obj):
        return getattr(obj.sender, 'role', None) == 'author'

    def get_display_name(self, obj):
        request = self.context.get('request')
        viewer = request.user if request and request.user.is_authenticated else None
        sender = obj.sender
        s_role = (getattr(sender, 'role', '') or '').lower()
        if s_role == 'author':
            name = (sender.get_full_name() or '').strip()
            return name or (getattr(sender, 'email', None) or getattr(sender, 'phone', None) or 'Muallif')
        if viewer and (getattr(viewer, 'role', '') or '').lower() == 'author':
            return 'Operator'
        name = (sender.get_full_name() or '').strip()
        return name or 'Operator'
