

# E-commerce Order Management System

This is a simple e-commerce order management system built using **PostgreSQL** as the database and Python with the `psycopg2` library for database interaction. It demonstrates how to perform complex database operations, including multi-table relationships, transaction management, views, indexing, and advanced SQL queries.

-----

## Table of Contents

  * [Project Overview](https://www.google.com/search?q=%23project-overview)
  * [Features](https://www.google.com/search?q=%23features)
  * [Database Design](https://www.google.com/search?q=%23database-design)
  * [Prerequisites](https://www.google.com/search?q=%23prerequisites)
  * [Setup and Run](https://www.google.com/search?q=%23setup-and-run)
  * [Usage Examples](https://www.google.com/search?q=%23usage-examples)
  * [Code Structure](https://www.google.com/search?q=%23code-structure)
  * [Important Notes](https://www.google.com/search?q=%23important-notes)

-----

## Project Overview

This project aims to simulate core order management functionalities of an e-commerce platform. It involves four main entities: Customers, Products, Orders, and Order Items, with data persistently stored in a PostgreSQL database. The system supports creating orders (with transactional inventory deduction), retrieving customer order history, querying top-selling products, and leveraging views and indexes for query optimization.

-----

## Features

  * **Customer Management**: Add new customers.
  * **Product Management**: Add new products.
  * **Order Creation**:
      * Supports multiple products within a single order.
      * **Transactional operations**: Ensures that order creation, order item insertion, and product stock deduction are atomic. If any step fails, the entire operation is rolled back.
      * Includes stock checks to prevent overselling.
  * **Order Queries**:
      * Retrieve detailed customer order history by customer ID (simplified using database views).
      * Query the top-selling products.
  * **Generic SQL Executor**: Provides an `execute_query` method that allows executing any parameterized SQL query, enhancing flexibility and security.
  * **Performance Optimization**: Necessary indexes are automatically created during database initialization to improve query efficiency.

-----

## Database Design

The system comprises the following four primary tables:

  * **`customers`**: Stores customer information.
      * `customer_id` (PRIMARY KEY, SERIAL)
      * `first_name` (VARCHAR)
      * `last_name` (VARCHAR)
      * `email` (VARCHAR, UNIQUE)
      * `phone` (VARCHAR)
      * `registration_date` (TIMESTAMP)
  * **`products`**: Stores product information.
      * `product_id` (PRIMARY KEY, SERIAL)
      * `product_name` (VARCHAR, UNIQUE)
      * `description` (TEXT)
      * `price` (DECIMAL)
      * `stock_quantity` (INTEGER)
      * `created_at` (TIMESTAMP)
      * `updated_at` (TIMESTAMP)
  * **`orders`**: Stores main order information.
      * `order_id` (PRIMARY KEY, SERIAL)
      * `customer_id` (FOREIGN KEY -\> `customers`)
      * `order_date` (TIMESTAMP)
      * `total_amount` (DECIMAL)
      * `status` (VARCHAR, e.g., 'Pending', 'Shipped')
  * **`order_items`**: Stores specific products and quantities within an order (many-to-many relationship).
      * `order_item_id` (PRIMARY KEY, SERIAL)
      * `order_id` (FOREIGN KEY -\> `orders`)
      * `product_id` (FOREIGN KEY -\> `products`)
      * `quantity` (INTEGER)
      * `price_at_purchase` (DECIMAL)

Additionally, the system creates a **view** named `customer_order_details` and several **indexes** (`idx_customers_email`, `idx_orders_customer_id`, `idx_order_items_order_id`, `idx_order_items_product_id`) to optimize query performance.

-----

## Prerequisites

Before running this project, ensure you have the following components installed:

  * **Python 3.x**
  * **PostgreSQL Database**: Make sure your PostgreSQL service is running.
  * **`psycopg2-binary` Python library**: Used for connecting to PostgreSQL.

-----

## Setup and Run

1.  **Install `psycopg2-binary`**:

    ```bash
    pip install psycopg2-binary
    ```

2.  **Create PostgreSQL Database and User**:
    Open your PostgreSQL client (e.g., `psql`) and execute the following SQL commands:

    ```sql
    CREATE DATABASE ecommerce_db;
    CREATE USER your_username WITH PASSWORD 'your_password';
    GRANT ALL PRIVILEGES ON DATABASE ecommerce_db TO your_username;
    ```

    **Important**: Replace `your_username` and `your_password` with your actual username and password.

3.  **Save the Code**:
    Save the provided Python code as a `.py` file (e.g., `ecommerce_app.py`).

4.  **Configure Database Connection**:
    Open the `ecommerce_app.py` file and locate the `db_config` dictionary within the `main()` function. Update the values for `user` and `password` with the credentials you created in Step 2:

    ```python
    db_config = {
        "dbname": "ecommerce_db",
        "user": "your_username",     # <-- Change to your username
        "password": "your_password", # <-- Change to your password
        "host": "localhost",
        "port": "5432"
    }
    ```

5.  **Run the Application**:
    Navigate to the directory containing `ecommerce_app.py` in your command line or terminal, then run:

    ```bash
    python ecommerce_app.py
    ```

-----

## Usage Examples

Upon running the application, you'll see a series of database operation demonstrations printed to the console, including:

  * Adding customers and products.
  * Successfully creating orders (showing order ID and total amount).
  * Attempting to create an order with insufficient stock (which will rollback and show an error).
  * Retrieving a specific customer's order history (using the database view).
  * Querying the top-selling products.
  * Executing a custom complex SQL query (e.g., calculating total spending per customer).
  * Updating product stock.

You can modify or add more operations in the code to test additional functionalities.

-----

## Code Structure

  * **`ECommerceManager` Class**:
      * `__init__`: Constructor, responsible for connecting to the database and initializing (creating tables, views, indexes).
      * `_connect`: Internal method handling database connection.
      * `_initialize_database`: Internal method executing all DDL (Data Definition Language) SQL to set up the database schema.
      * `execute_query`: Core method for executing any SQL query, supporting parameterization (to prevent SQL injection), and automatically handling commits and rollbacks.
      * `add_customer`, `add_product`: Basic methods for adding customers and products.
      * `create_order`: Core method containing transaction logic for order creation, order item insertion, and stock updates.
      * `get_customer_order_history`: Queries customer order details using the database view.
      * `get_top_selling_products`: Queries the top-selling products.
      * `close`: Closes the database connection.
  * **`main()` Function**: The entry point of the program, responsible for instantiating `ECommerceManager` and calling its methods to demonstrate various functionalities.

