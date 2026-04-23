"""DRF pagination — mualliflar ro'yxati kabi endpointlarda page_size so'rovi bilan yig'ish."""

from rest_framework.pagination import PageNumberPagination


class PhoenixPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 500
