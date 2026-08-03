"""Seed DynamoDB tables with e-commerce product catalog and sample data."""

import argparse
import boto3
from decimal import Decimal


def seed_products(table):
    """Seed product catalog."""
    products = [
        {"product_id": "PROD-001", "name": "TechMart Air", "category": "laptops", "price": Decimal("599"), "stock": 234, "specs": "14in, i5, 8GB, 256GB SSD, Wi-Fi 5"},
        {"product_id": "PROD-002", "name": "TechMart Pro 15", "category": "laptops", "price": Decimal("799"), "stock": 142, "specs": "15.6in, i7, 16GB, 512GB SSD, Wi-Fi 6"},
        {"product_id": "PROD-003", "name": "TechMart Titan", "category": "laptops", "price": Decimal("1299"), "stock": 67, "specs": "16in, RTX 4060, 32GB, 1TB SSD, Wi-Fi 6E"},
        {"product_id": "PROD-004", "name": "TechMart Hub", "category": "smart_home", "price": Decimal("149"), "stock": 512, "specs": "Wi-Fi 6, Bluetooth 5.0, Zigbee 3.0, max 50 devices"},
        {"product_id": "PROD-005", "name": "Smart Camera", "category": "smart_home", "price": Decimal("79"), "stock": 890, "specs": "1080p, night vision, Wi-Fi direct or via Hub"},
        {"product_id": "PROD-006", "name": "Motion Sensor", "category": "smart_home", "price": Decimal("29"), "stock": 1450, "specs": "Zigbee 3.0, 120° detection, 2yr battery"},
        {"product_id": "PROD-007", "name": "USB-C Dock", "category": "accessories", "price": Decimal("89"), "stock": 320, "specs": "3x USB-A, 2x USB-C, HDMI, Ethernet"},
        {"product_id": "PROD-008", "name": "Wireless KB+Mouse", "category": "accessories", "price": Decimal("49"), "stock": 670, "specs": "Bluetooth, multi-device, rechargeable"},
    ]
    for p in products:
        table.put_item(Item=p)
    print(f"  ✓ Seeded {len(products)} products")


def seed_customers(table):
    """Seed customer records."""
    customers = [
        {"customer_id": "CUST-2001", "name": "Alice Johnson", "email": "alice@example.com", "tier": "premium", "lifetime_value": Decimal("4500")},
        {"customer_id": "CUST-2002", "name": "Bob Smith", "email": "bob@example.com", "tier": "standard", "lifetime_value": Decimal("1200")},
        {"customer_id": "CUST-2003", "name": "Carol Williams", "email": "carol@example.com", "tier": "enterprise", "lifetime_value": Decimal("28000")},
        {"customer_id": "CUST-2004", "name": "Dave Brown", "email": "dave@example.com", "tier": "standard", "lifetime_value": Decimal("800")},
    ]
    for c in customers:
        table.put_item(Item=c)
    print(f"  ✓ Seeded {len(customers)} customers")


def seed_orders(table):
    """Seed order records."""
    orders = [
        {"order_id": "ORD-7001", "customer_id": "CUST-2001", "status": "delivered", "total": Decimal("799"), "items": [{"name": "TechMart Pro 15", "qty": 1}], "date": "2025-07-20"},
        {"order_id": "ORD-7002", "customer_id": "CUST-2001", "status": "delivered", "total": Decimal("207"), "items": [{"name": "TechMart Hub", "qty": 1}, {"name": "Motion Sensor", "qty": 2}], "date": "2025-07-10"},
        {"order_id": "ORD-7003", "customer_id": "CUST-2002", "status": "processing", "total": Decimal("1299"), "items": [{"name": "TechMart Titan", "qty": 1}], "date": "2025-07-28"},
        {"order_id": "ORD-7004", "customer_id": "CUST-2003", "status": "delivered", "total": Decimal("4745"), "items": [{"name": "TechMart Pro 15", "qty": 5}, {"name": "USB-C Dock", "qty": 5}], "date": "2025-07-15"},
        {"order_id": "ORD-7005", "customer_id": "CUST-2004", "status": "shipped", "total": Decimal("599"), "items": [{"name": "TechMart Air", "qty": 1}], "date": "2025-07-25"},
    ]
    for o in orders:
        table.put_item(Item=o)
    print(f"  ✓ Seeded {len(orders)} orders")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="ap-southeast-1")
    args = parser.parse_args()

    dynamodb = boto3.resource("dynamodb", region_name=args.region)
    seed_products(dynamodb.Table("m5-demo-products"))
    seed_customers(dynamodb.Table("m5-demo-customers"))
    seed_orders(dynamodb.Table("m5-demo-orders"))
    print("  ✓ Seeding complete")


if __name__ == "__main__":
    main()
