from functools import reduce

import dramatiq
import dramatiq.brokers.redis
from django.db.models import Q, Case, When, IntegerField, Value
from django.shortcuts import get_object_or_404
from dramatiq.results import Results
from dramatiq.results.errors import ResultTimeout
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product, Store
from .permissions import IsStoreManager
from .serializers import ProductSerializer, StoreSerializer, PriceFeedCSVUploadSerializer, ProductUpdateSerializer, \
    ProductCreateSerializer
from .tasks import process_csv_price_feed


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PriceFeedCSVUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated, IsStoreManager]

    def post(self, request, format=None):
        serializer = PriceFeedCSVUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        file_obj = serializer.validated_data['file']

        try:
            # Read and decode content
            content = file_obj.read().decode('utf-8')
            message = process_csv_price_feed.send(content)

            return Response({'status': 'success', 'task_id': message.message_id}, status=status.HTTP_202_ACCEPTED)
        except (RedisConnectionError, ConnectionRefusedError) as e:
            return Response({'status': 'error', 'error': 'Service unavailable. Could not connect to task queue.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PriceFeedView(APIView):
    permission_classes = [IsAuthenticated, IsStoreManager]

    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': serializer.data}, status=status.HTTP_201_CREATED)
        return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        # If pk is provided in URL, update that specific product
        if pk:
            product = get_object_or_404(Product, pk=pk)
            serializer = ProductUpdateSerializer(product, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({'status': 'success', 'data': ProductSerializer(product).data})
            return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Legacy support for updating by store_id and sku in body (if needed, or remove)
        # For now, let's keep it but prioritize ID based update if pk is present
        serializer = ProductUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        product = get_object_or_404(Product, store_id=data['store_id'], sku=data['sku'])
        update_fields = {}
        for field in ['product_name', 'price', 'date']:
            if field in data:
                setattr(product, field, data[field])
                update_fields[field] = data[field]
        product.save(update_fields=list(update_fields.keys()))
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
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': ProductSerializer(product).data})
        return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response({'status': 'success', 'message': 'Product deleted successfully'},
                        status=status.HTTP_204_NO_CONTENT)


class PriceFeedSearchView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        query = request.GET.get('q', '').strip()
        store_name = request.GET.get('store_name')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        sku = request.GET.get('sku')
        sort = request.GET.get('sort', 'relevance')

        qs = Product.objects.select_related('store').all()

        if query:
            words = [w for w in query.split() if w]
            q_obj = Q()
            for word in words:
                q_obj |= Q(product_name__icontains=word) | Q(sku__icontains=word)
            qs = qs.filter(q_obj)
        else:
            words = []

        if store_name:
            qs = qs.filter(store__name__icontains=store_name)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if sku:
            qs = qs.filter(sku__icontains=sku)

        if sort == 'price_asc':
            qs = qs.order_by('price')
        elif sort == 'price_desc':
            qs = qs.order_by('-price')
        else:
            if words:
                match_expr = reduce(
                    lambda acc, w: acc + Case(When(product_name__icontains=w, then=1), default=0, output_field=IntegerField()) + Case(When(sku__icontains=w, then=1), default=0, output_field=IntegerField()),
                    words,
                    Value(0, output_field=IntegerField())
                )
                qs = qs.annotate(match_score=match_expr).order_by('-match_score', 'price')
            else:
                qs = qs.order_by('price')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        if page is not None:
            serializer = ProductSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ProductSerializer(qs, many=True)
        return Response({'status': 'success', 'data': serializer.data})


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
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': serializer.data}, status=status.HTTP_201_CREATED)
        return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


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
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': serializer.data})
        return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


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
            # If the exception is from the actor execution (e.g. validation error inside the task),
            # get_result re-raises it. We should catch it and return it as an error status.
            # We use repr(e) to get more details if str(e) is empty or unhelpful
            error_msg = str(e)
            if not error_msg:
                error_msg = repr(e)
            return Response({'status': 'error', 'task_id': task_id, 'error': error_msg}, status=status.HTTP_200_OK)
