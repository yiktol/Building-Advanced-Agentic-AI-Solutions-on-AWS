"""Seed DynamoDB tables with sample customer and order data."""

import argparse
import boto3
from decimal import Decimal


def seed_customers(table):
    """Seed customer records."""
    customers = [
        {
            "customer_id": "CUST-1001",
            "name": "Lois Lane",
            "email": "lois.lane@dailyplanet.com",
            "status": "active",
            "tier": "premium",
            "since": "2022-03-15",
            "lifetime_value": Decimal("12450"),
        },
        {
            "customer_id": "CUST-1002",
            "name": "Alfred Pennyworth",
            "email": "alfred@waynemanor.com",
            "status": "active",
            "tier": "standard",
            "since": "2023-01-10",
            "lifetime_value": Decimal("3200"),
        },
        {
            "customer_id": "CUST-1003",
            "name": "Mary Jane Watson",
            "email": "mj.watson@email.com",
            "status": "active",
            "tier": "premium",
            "since": "2021-11-22",
            "lifetime_value": Decimal("8900"),
        },
        {
            "customer_id": "CUST-1004",
            "name": "Steve Trevor",
            "email": "steve.trevor@gov.us",
            "status": "inactive",
            "tier": "standard",
            "since": "2023-06-01",
            "lifetime_value": Decimal("1500"),
        },
        {
            "customer_id": "CUST-1005",
            "name": "Pepper Potts",
            "email": "pepper@starkindustries.com",
            "status": "active",
            "tier": "enterprise",
            "since": "2020-08-14",
            "lifetime_value": Decimal("45000"),
        },
    ]

    for customer in customers:
        table.put_item(Item=customer)
    print(f"  ✓ Seeded {len(customers)} customers")


def seed_orders(table):
    """Seed order records."""
    orders = [
        {
            "order_id": "ORD-5001",
            "customer_id": "CUST-1001",
            "date": "2025-07-10",
            "status": "delivered",
            "items": [
                {"name": "TechMart Hub", "price": Decimal("149")},
                {"name": "Motion Sensor x2", "price": Decimal("58")},
            ],
            "total": Decimal("220"),
            "shipping": "express",
            "payment_method": "visa_4532",
        },
        {
            "order_id": "ORD-5002",
            "customer_id": "CUST-1001",
            "date": "2025-07-20",
            "status": "delivered",
            "items": [
                {"name": "TechMart Pro 15", "price": Decimal("799")},
            ],
            "total": Decimal("799"),
            "shipping": "standard",
            "payment_method": "visa_4532",
        },
        {
            "order_id": "ORD-5003",
            "customer_id": "CUST-1002",
            "date": "2025-07-15",
            "status": "delivered",
            "items": [
                {"name": "Smart Camera x3", "price": Decimal("237")},
            ],
            "total": Decimal("237"),
            "shipping": "standard",
            "payment_method": "amex_8821",
        },
        {
            "order_id": "ORD-5004",
            "customer_id": "CUST-1003",
            "date": "2025-07-25",
            "status": "processing",
            "items": [
                {"name": "TechMart Titan", "price": Decimal("1299")},
                {"name": "USB-C Dock", "price": Decimal("89")},
            ],
            "total": Decimal("1388"),
            "shipping": "express",
            "payment_method": "mc_3341",
        },
        {
            "order_id": "ORD-5005",
            "customer_id": "CUST-1005",
            "date": "2025-06-30",
            "status": "delivered",
            "items": [
                {"name": "TechMart Hub", "price": Decimal("149")},
                {"name": "Smart Camera x5", "price": Decimal("395")},
                {"name": "Motion Sensor x10", "price": Decimal("290")},
            ],
            "total": Decimal("834"),
            "shipping": "same_day",
            "payment_method": "corp_card",
        },
        {
            "order_id": "ORD-5006",
            "customer_id": "CUST-1005",
            "date": "2025-07-28",
            "status": "delivered",
            "items": [
                {"name": "TechMart Pro 15 x10", "price": Decimal("7990")},
            ],
            "total": Decimal("7990"),
            "shipping": "express",
            "payment_method": "corp_card",
        },
    ]

    for order in orders:
        table.put_item(Item=order)
    print(f"  ✓ Seeded {len(orders)} orders")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="ap-southeast-1")
    args = parser.parse_args()

    dynamodb = boto3.resource("dynamodb", region_name=args.region)

    customers_table = dynamodb.Table("m3-demo-customers")
    orders_table = dynamodb.Table("m3-demo-orders")

    seed_customers(customers_table)
    seed_orders(orders_table)

    print("  ✓ Data seeding complete")


if __name__ == "__main__":
    main()
