from functools import reduce

import dramatiq
import dramatiq.brokers.redis
from django.db.models import Q, Case, When, IntegerField, Value
from django.shortcuts import get_object_or_404
from dramatiq.results import Results
from dramatiq.results.errors import ResultTimeout
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product, Store
from .permissions import IsStoreManager
from .serializers import ProductSerializer, StoreSerializer, PriceFeedCSVUploadSerializer, ProductUpdateSerializer, \
    ProductCreateSerializer
from .tasks import process_csv_price_feed
from .filters import ProductFilter


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PriceFeedCSVUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated, IsStoreManager]

    def post(self, request, format=None):
        serializer = PriceFeedCSVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_obj = serializer.validated_data['file']
        try:
            # Read and decode content
            content = file_obj.read().decode('utf-8')
            message = process_csv_price_feed.send(content)

            return Response({'status': 'success', 'task_id': message.message_id}, status=status.HTTP_202_ACCEPTED)
        except (RedisConnectionError, ConnectionRefusedError):
            return Response({'status': 'error', 'error': 'Service unavailable. Could not connect to task queue.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PriceFeedView(APIView):
    permission_classes = [IsAuthenticated, IsStoreManager]

    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'success', 'data': serializer.data}, status=status.HTTP_201_CREATED)

    def put(self, request, pk=None):
        if pk:
            product = get_object_or_404(Product, pk=pk)
        else:
            serializer = ProductUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            product = get_object_or_404(Product, store_id=data['store_id'], sku=data['sku'])
        serializer = ProductUpdateSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'success', 'data': ProductSerializer(product).data})


class PriceFeedDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStoreManager]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product)
        return Response({'status': 'success', 'data': serializer.data})

    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductUpdateSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'success', 'data': ProductSerializer(product).data})

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response({'status': 'success', 'message': 'Product deleted successfully'},
                        status=status.HTTP_204_NO_CONTENT)


class PriceFeedSearchView(ListAPIView):
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related('store').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['product_name', 'sku']
    ordering_fields = ['price']
    ordering = ['price']


class StoreListCreateView(APIView):
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminUser()]
        return [AllowAny()]

    def get(self, request):
        stores = Store.objects.all()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(stores, request, view=self)
        if page is not None:
            serializer = StoreSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = StoreSerializer(stores, many=True)
        return Response({'status': 'success', 'data': serializer.data})

    def post(self, request):
        serializer = StoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'success', 'data': serializer.data}, status=status.HTTP_201_CREATED)


class StoreDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [AllowAny()]

    def get_object(self, pk):
        return get_object_or_404(Store, pk=pk)

    def get(self, request, pk):
        store = self.get_object(pk)
        serializer = StoreSerializer(store)
        return Response({'status': 'success', 'data': serializer.data})

    def put(self, request, pk):
        store = self.get_object(pk)
        serializer = StoreSerializer(store, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'success', 'data': serializer.data})


class CSVTaskStatusView(APIView):
    permission_classes = [IsAuthenticated, IsStoreManager]

    def get(self, request, task_id):
        broker = dramatiq.get_broker()
        results_middleware = next((m for m in broker.middleware if isinstance(m, Results)), None)

        if not results_middleware:
            return Response({'status': 'error', 'error': 'Results backend not configured'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        backend = results_middleware.backend
        try:
            from dramatiq import Message
            # Reconstruct message object
            dummy_message = Message(
                queue_name='default',
                actor_name='process_csv_price_feed',
                args=(), kwargs={}, options={},
                message_id=task_id,
                message_timestamp=0
            )

            # get_result blocks until result is available or timeout.
            result = backend.get_result(dummy_message, timeout=100)
            return Response({'status': 'completed', 'task_id': task_id, 'result': result}, status=status.HTTP_200_OK)

        except ResultTimeout:
            return Response({'status': 'pending', 'task_id': task_id}, status=status.HTTP_200_OK)
        except (RedisConnectionError, ConnectionRefusedError):
            return Response({'status': 'error', 'error': 'Service unavailable. Could not connect to results backend.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            error_msg = str(e)
            if not error_msg:
                error_msg = repr(e)
            return Response({'status': 'error', 'task_id': task_id, 'error': error_msg}, status=status.HTTP_200_OK)
