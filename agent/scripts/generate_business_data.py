import random
from datetime import date, timedelta

import psycopg

DSN = "postgresql://insight:insight@localhost:5432/insight"


def main() -> None:
    random.seed(42)
    start = date(2026, 1, 1)
    days = 180

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS order_items, orders, products, customers")
            cur.execute(
                """
                CREATE TABLE customers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(64),
                    region VARCHAR(32),
                    city VARCHAR(32),
                    created_at DATE
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(64),
                    category VARCHAR(32),
                    price NUMERIC(10, 2)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE orders (
                    id SERIAL PRIMARY KEY,
                    customer_id INT REFERENCES customers(id),
                    order_date DATE,
                    status VARCHAR(16),
                    amount NUMERIC(12, 2)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE order_items (
                    id SERIAL PRIMARY KEY,
                    order_id INT REFERENCES orders(id),
                    product_id INT REFERENCES products(id),
                    quantity INT,
                    price NUMERIC(10, 2)
                )
                """
            )

            regions = ["华东", "华南", "华北", "西南", "华中"]
            customers = []
            for index in range(1, 201):
                name = f"客户{index:03d}"
                region = random.choice(regions)
                city = f"{region}市{index % 5}"
                customers.append((name, region, city, start))
            cur.executemany(
                "INSERT INTO customers (name, region, city, created_at) VALUES (%s, %s, %s, %s)",
                customers,
            )

            categories = ["数码", "家电", "服饰", "食品", "美妆"]
            products = []
            for index in range(1, 101):
                category = random.choice(categories)
                price = round(random.uniform(20, 5000), 2)
                products.append((f"商品{index:03d}", category, price))
            cur.executemany(
                "INSERT INTO products (name, category, price) VALUES (%s, %s, %s)",
                products,
            )

            order_ids = []
            for _ in range(20_000):
                customer_id = random.randint(1, 200)
                order_date = start + timedelta(days=random.randint(0, days - 1))
                status = random.choices(["completed", "pending", "refunded"], weights=[80, 15, 5])[0]
                amount = round(random.uniform(50, 8000), 2)
                with conn.cursor() as insert_cur:
                    insert_cur.execute(
                        """
                        INSERT INTO orders (customer_id, order_date, status, amount)
                        VALUES (%s, %s, %s, %s) RETURNING id
                        """,
                        (customer_id, order_date, status, amount),
                    )
                    order_ids.append(insert_cur.fetchone()[0])

            items = []
            for order_id in order_ids:
                for _ in range(random.randint(1, 5)):
                    product_id = random.randint(1, 100)
                    quantity = random.randint(1, 10)
                    price = round(random.uniform(20, 5000), 2)
                    items.append((order_id, product_id, quantity, price))
            cur.executemany(
                """
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
                """,
                items,
            )

    print("business data generated: 200 customers, 100 products, 20000 orders")


if __name__ == "__main__":
    main()
