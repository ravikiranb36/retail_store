from .models import Product, Store
import csv
from io import StringIO
import dramatiq
from django.db import transaction

@dramatiq.actor(store_results=True)
def process_csv_price_feed(csv_content):
    reader = csv.DictReader(StringIO(csv_content))
    rows = list(reader)
    # Prepare keys for lookup
    key_tuples = [(row['Store ID'], row['SKU']) for row in rows]
    # Get store_id to Store instance mapping
    store_ids = set(row['Store ID'] for row in rows)
    stores = {str(store.id): store for store in Store.objects.filter(id__in=store_ids)}
    # Query existing products in one shot
    existing_products = Product.objects.filter(
        store_id__in=[k[0] for k in key_tuples],
        sku__in=[k[1] for k in key_tuples]
    )
    existing_map = {(str(p.store_id), p.sku): p for p in existing_products}
    to_update = []
    to_create = []
    for row in rows:
        key = (str(row['Store ID']), row['SKU'])
        store = stores.get(str(row['Store ID']))
        if not store:
            continue  # skip unknown stores
        data = {
            'store': store,
            'sku': row['SKU'],
            'product_name': row['Product Name'],
            'price': row['Price'],
            'date': row['Date']
        }
        if key in existing_map:
            product = existing_map[key]
            product.product_name = data['product_name']
            product.price = data['price']
            product.date = data['date']
            to_update.append(product)
        else:
            to_create.append(Product(**data))
    with transaction.atomic():
        if to_create:
            Product.objects.bulk_create(to_create, batch_size=1000)
        if to_update:
            Product.objects.bulk_update(to_update, ['product_name', 'price', 'date'], batch_size=1000)
    return {'created': len(to_create), 'updated': len(to_update)}
