import traceback

from .models import Product, Store
import csv
from io import StringIO
import dramatiq
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@dramatiq.actor(store_results=True)
def process_csv_price_feed(csv_content):
    try:
        reader = csv.DictReader(StringIO(csv_content))
        
        # Check if fieldnames were parsed correctly
        if not reader.fieldnames:
             return {'created': 0, 'updated': 0, 'warning': 'CSV file is empty or headers could not be parsed'}

        # Normalize headers (strip whitespace)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]

        rows = list(reader)
        
        if not rows:
            return {'created': 0, 'updated': 0, 'warning': 'CSV file contains no data rows'}

        # Validate required headers
        required_headers = {'Store ID', 'SKU', 'Product Name', 'Price', 'Date'}
        if not required_headers.issubset(set(reader.fieldnames or [])):
            missing = required_headers - set(reader.fieldnames or [])
            # Log the actual headers found for debugging
            logger.error(f"Missing headers. Found: {reader.fieldnames}. Missing: {missing}")
            raise ValueError(f"Missing required headers: {', '.join(missing)}")

        # Prepare keys for lookup
        key_tuples = [(row['Store ID'], row['SKU']) for row in rows if row.get('Store ID') and row.get('SKU')]
        
        if not key_tuples:
             return {'created': 0, 'updated': 0, 'warning': 'No valid rows found (missing Store ID or SKU)'}

        # Get store_id to Store instance mapping
        store_ids = set(row['Store ID'] for row in rows if row.get('Store ID'))
        stores = {str(store.id): store for store in Store.objects.filter(id__in=store_ids)}
        
        # Query existing products in one shot
        existing_products = Product.objects.filter(
            store_id__in=[k[0] for k in key_tuples],
            sku__in=[k[1] for k in key_tuples]
        )
        existing_map = {(str(p.store_id), p.sku): p for p in existing_products}
        
        to_update = []
        to_create = []
        errors = []
        
        for i, row in enumerate(rows):
            try:
                store_id = row.get('Store ID')
                sku = row.get('SKU')
                
                if not store_id or not sku:
                    continue

                key = (str(store_id), sku)
                store = stores.get(str(store_id))
                
                if not store:
                    errors.append(f"Row {i+1}: Store ID {store_id} not found")
                    continue 
                
                data = {
                    'store': store,
                    'sku': sku,
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
            except Exception as e:
                errors.append(f"Row {i+1}: {str(e)}")

        with transaction.atomic():
            if to_create:
                Product.objects.bulk_create(to_create, batch_size=1000)
            if to_update:
                Product.objects.bulk_update(to_update, ['product_name', 'price', 'date'], batch_size=1000)
        
        result = {'created': len(to_create), 'updated': len(to_update)}
        if errors:
            result['errors'] = errors[:10] # Limit errors returned
            if len(errors) > 10:
                result['errors'].append(f"...and {len(errors)-10} more errors")
        
        return result

    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error processing CSV: {e}", exc_info=True)
        # Return the specific error message
        raise ValueError(f"Failed to process CSV: {str(e)}")
