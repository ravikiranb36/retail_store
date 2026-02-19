from rest_framework import serializers
from .models import Product, Store

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name']

class ProductSerializer(serializers.ModelSerializer):
    store = StoreSerializer(read_only=True)
    store_id = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all(), source='store', write_only=True)

    class Meta:
        model = Product
        fields = ['id', 'store', 'store_id', 'sku', 'product_name', 'price', 'date']
        read_only_fields = ['id', 'store']

class PriceFeedCSVUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError('Only CSV files are allowed.')
        return value

class ProductUpdateSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    sku = serializers.CharField(max_length=64)
    product_name = serializers.CharField(max_length=255, required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    date = serializers.DateField(required=False)

    def validate_store_id(self, value):
        from .models import Store
        if not Store.objects.filter(id=value).exists():
            raise serializers.ValidationError('Store does not exist.')
        return value

    def validate(self, data):
        # Ensure SKU exists for update
        from .models import Product
        if not Product.objects.filter(store_id=data['store_id'], sku=data['sku']).exists():
            raise serializers.ValidationError('Product with this SKU and store does not exist.')
        return data

class ProductCreateSerializer(serializers.ModelSerializer):
    store_id = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all(), source='store')
    class Meta:
        model = Product
        fields = ['store_id', 'sku', 'product_name', 'price', 'date']

    def validate_store_id(self, value):
        if not value:
            raise serializers.ValidationError('Store is required.')
        return value
