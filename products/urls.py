from django.urls import path
from .views import PriceFeedCSVUploadView, PriceFeedView, PriceFeedSearchView, CSVTaskStatusView, StoreListCreateView, StoreDetailView

urlpatterns = [
    path('price-feed/upload/', PriceFeedCSVUploadView.as_view(), name='price_feed_csv_upload'),
    path('price-feed/', PriceFeedView.as_view(), name='price_feed_create'),
    path('price-feed/update/', PriceFeedView.as_view(), name='price_feed_update'),
    path('price-feed/search/', PriceFeedSearchView.as_view(), name='price_feed_search'),
    path('price-feed/csv-task-status/<str:task_id>/', CSVTaskStatusView.as_view(), name='csv_task_status'),
    path('stores/', StoreListCreateView.as_view(), name='store_list_create'),
    path('stores/<int:pk>/', StoreDetailView.as_view(), name='store_detail'),
]
