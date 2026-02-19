from .models import Product, Store
from .serializers import ProductSerializer, StoreSerializer, PriceFeedCSVUploadSerializer, ProductUpdateSerializer, ProductCreateSerializer
from .tasks import process_csv_price_feed
from .permissions import IsStoreManager
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
import dramatiq
import dramatiq.brokers.redis
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend
from dramatiq.results.errors import ResultTimeout

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
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        file_obj = serializer.validated_data['file']
        broker = dramatiq.get_broker()
        actor = process_csv_price_feed.send_with_options(args=(file_obj.read().decode('utf-8'),), pipe=True)
        task_id = actor.message.message_id
        return Response({'status': 'Processing', 'task_id': task_id}, status=status.HTTP_202_ACCEPTED)

class PriceFeedView(APIView):
    permission_classes = [IsAuthenticated, IsStoreManager]

    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        serializer = ProductUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        product = get_object_or_404(Product, store_id=data['store_id'], sku=data['sku'])
        update_fields = {}
        for field in ['product_name', 'price', 'date']:
            if field in data:
                setattr(product, field, data[field])
                update_fields[field] = data[field]
        product.save(update_fields=list(update_fields.keys()))
        return Response(ProductSerializer(product).data)

class PriceFeedSearchView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        query = request.GET.get('q', '')
        store_name = request.GET.get('store_name')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        sort = request.GET.get('sort', 'relevance')
        qs = Product.objects.all()
        # Multi-word, case-insensitive, partial match for product_name
        if query:
            words = query.strip().split()
            q_obj = Q()
            for word in words:
                q_obj |= Q(product_name__icontains=word)
            qs = qs.filter(q_obj)
        if store_name:
            qs = qs.filter(store__name__icontains=store_name)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if sort == 'price_asc':
            qs = qs.order_by('price')
        elif sort == 'price_desc':
            qs = qs.order_by('-price')
        else:
            # Default: order by best match (number of query words matched, then price asc)
            if query:
                from django.db.models import Count, Case, When, IntegerField
                for word in words:
                    qs = qs.annotate(**{f'match_{word}': Case(When(product_name__icontains=word, then=1), default=0, output_field=IntegerField())})
                match_fields = [f'match_{word}' for word in words]
                qs = qs.annotate(total_matches=sum([getattr(qs.model, f'match_{word}') for word in words]))
                qs = qs.order_by('-total_matches', 'price')
            else:
                qs = qs.order_by('price')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        if page is not None:
            serializer = ProductSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ProductSerializer(qs, many=True)
        return Response(serializer.data)

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
        return Response(serializer.data)

    def post(self, request):
        serializer = StoreSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
        return Response(serializer.data)

    def put(self, request, pk):
        store = self.get_object(pk)
        serializer = StoreSerializer(store, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CSVTaskStatusView(APIView):
    permission_classes = [IsAuthenticated, IsStoreManager]
    def get(self, request, task_id):
        broker = dramatiq.get_broker()
        results_middleware = next((m for m in broker.middleware if isinstance(m, Results)), None)
        
        if not results_middleware:
            return Response({'task_id': task_id, 'status': 'error', 'error': 'Results backend not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        backend = results_middleware.backend
        try:
            message = backend.get_result_message(task_id, timeout=100)
        except ResultTimeout:
            return Response({'task_id': task_id, 'status': 'pending'}, status=status.HTTP_200_OK)
        
        if message.status == "success":
            return Response({'task_id': task_id, 'status': 'completed', 'result': message.return_value}, status=status.HTTP_200_OK)
            
        return Response({'task_id': task_id, 'status': 'error', 'error': message.exception_data}, status=status.HTTP_200_OK)
