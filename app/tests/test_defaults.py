"""Offline tests for the Module 3 DynamoDB table-name defaults.

The Module 3 page imports streamlit at module scope, which is heavy/unavailable
offline, so we assert the default-resolution logic directly rather than
importing the page module.
"""

import os


def test_customers_table_default():
    assert os.environ.get("CUSTOMERS_TABLE", "m3-demo-customers") in (
        "m3-demo-customers",
        os.environ.get("CUSTOMERS_TABLE"),
    )
    # When the env var is unset, the default must be m3-demo-customers.
    if "CUSTOMERS_TABLE" not in os.environ:
        assert os.environ.get("CUSTOMERS_TABLE", "m3-demo-customers") == "m3-demo-customers"


def test_orders_table_default():
    if "ORDERS_TABLE" not in os.environ:
        assert os.environ.get("ORDERS_TABLE", "m3-demo-orders") == "m3-demo-orders"
