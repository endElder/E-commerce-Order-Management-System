import psycopg2
from psycopg2 import extras # Used for DictCursor
from datetime import datetime # For precise timestamp formatting in output

class ECommerceManager:
    def __init__(self, dbname, user, password, host="localhost", port="5432"):
        self.conn_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port
        }
        self.conn = None
        self.cursor = None
        self._connect()
        self._initialize_database()

    def _connect(self):
        """Connects to the PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            # Use DictCursor to access results by column name
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            print("Successfully connected to PostgreSQL database.")
        except psycopg2.Error as e:
            print(f"Database connection error: {e}")
            raise # Re-raise the exception to indicate connection failure

    def _initialize_database(self):
        """Initializes the database: creates tables, views, and indexes if they don't exist."""
        try:
            # All DDL (Data Definition Language) SQL statements
            ddl_sql = """
            -- Disable notice for 'CREATE TABLE IF NOT EXISTS' for cleaner output during initialization
            SET client_min_messages TO WARNING;

            -- 1. Create Customers Table
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(20),
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 2. Create Products Table
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                product_name VARCHAR(100) UNIQUE NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
                stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 3. Create Orders Table
            CREATE TABLE IF NOT EXISTS orders (
                order_id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount >= 0),
                status VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'))
            );

            -- 4. Create Order_Items Table
            CREATE TABLE IF NOT EXISTS order_items (
                order_item_id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                price_at_purchase DECIMAL(10, 2) NOT NULL CHECK (price_at_purchase >= 0),
                UNIQUE (order_id, product_id)
            );

            ---

            -- 5. Create Views
            CREATE OR REPLACE VIEW customer_order_details AS
            SELECT
                c.customer_id,
                c.first_name,
                c.last_name,
                o.order_id,
                o.order_date,
                o.total_amount,
                o.status,
                p.product_name,
                oi.quantity,
                oi.price_at_purchase
            FROM
                customers c
            JOIN
                orders o ON c.customer_id = o.customer_id
            JOIN
                order_items oi ON o.order_id = oi.order_id
            JOIN
                products p ON oi.product_id = p.product_id
            ORDER BY
                o.order_date DESC, o.order_id, p.product_name;

            ---

            -- 6. Create Indexes for Performance Optimization
            CREATE INDEX IF NOT EXISTS idx_customers_email ON customers (email);
            CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);
            CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
            CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);

            -- Re-enable client messages to default
            RESET client_min_messages;
            """
            self.cursor.execute(ddl_sql)
            self.conn.commit()
            print("Database schema (tables, views, indexes) ensured to exist.")
        except psycopg2.Error as e:
            print(f"Database initialization error: {e}")
            self.conn.rollback() # Rollback if initialization fails
            raise

    def execute_query(self, sql_query, params=None, fetch_results=True):
        """
        Executes an SQL query with optional parameters.
        Returns results for SELECT queries or a status dict for others.
        Automatically handles commit for non-SELECTs and rollback on error.
        """
        try:
            self.cursor.execute(sql_query, params)
            if sql_query.strip().upper().startswith("SELECT") and fetch_results:
                return self.cursor.fetchall()
            else:
                self.conn.commit()
                return {"rows_affected": self.cursor.rowcount}
        except psycopg2.Error as e:
            print(f"SQL execution error: {e}")
            self.conn.rollback() # Rollback on error
            return {"error": str(e)}
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            self.conn.rollback()
            return {"error": str(e)}

    def add_customer(self, first_name, last_name, email, phone=None):
        """Adds a new customer to the database."""
        sql = "INSERT INTO customers (first_name, last_name, email, phone) VALUES (%s, %s, %s, %s) RETURNING customer_id;"
        result = self.execute_query(sql, (first_name, last_name, email, phone))
        if isinstance(result, list) and result:
            print(f"Customer '{first_name} {last_name}' added successfully with ID: {result[0]['customer_id']}")
            return result[0]['customer_id']
        else:
            print(f"Failed to add customer: {result.get('error', 'Unknown error')}")
            return None

    def add_product(self, product_name, description, price, stock_quantity):
        """Adds a new product to the database."""
        sql = "INSERT INTO products (product_name, description, price, stock_quantity) VALUES (%s, %s, %s, %s) RETURNING product_id;"
        result = self.execute_query(sql, (product_name, description, price, stock_quantity))
        if isinstance(result, list) and result:
            print(f"Product '{product_name}' added successfully with ID: {result[0]['product_id']}")
            return result[0]['product_id']
        else:
            print(f"Failed to add product: {result.get('error', 'Unknown error')}")
            return None

    def create_order(self, customer_id, products_with_quantities):
        """
        Creates a new order, handling the transaction:
        1. Inserts the order.
        2. Inserts order items.
        3. Updates product stock.
        Rolls back if any step fails (e.g., insufficient stock).
        `products_with_quantities` should be a list of tuples: `[(product_id, quantity), ...]`.
        """
        try:
            self.conn.autocommit = False # Start transaction

            total_amount = 0
            # Pre-check stock and calculate total amount before inserting anything
            for product_id, quantity in products_with_quantities:
                # Retrieve product price and current stock
                product_info = self.execute_query("SELECT price, stock_quantity FROM products WHERE product_id = %s;", (product_id,), fetch_results=True)
                if not product_info:
                    raise ValueError(f"Product ID {product_id} does not exist.")
                product_price = product_info[0]['price']
                current_stock = product_info[0]['stock_quantity']

                if current_stock < quantity:
                    raise ValueError(f"Product '{product_id}' has insufficient stock. Needed: {quantity}, Available: {current_stock}.")
                total_amount += product_price * quantity

            # 1. Insert the new order
            order_sql = "INSERT INTO orders (customer_id, total_amount, status) VALUES (%s, %s, 'Pending') RETURNING order_id;"
            order_result = self.execute_query(order_sql, (customer_id, total_amount), fetch_results=True)
            if not order_result:
                raise Exception("Failed to create order record.")
            order_id = order_result[0]['order_id']

            # 2. Insert order items and 3. Update product stock for each item
            for product_id, quantity in products_with_quantities:
                # Re-fetch price_at_purchase to ensure it's accurate at the moment of order creation
                product_info = self.execute_query("SELECT price FROM products WHERE product_id = %s;", (product_id,), fetch_results=True)
                price_at_purchase = product_info[0]['price']

                item_sql = "INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase) VALUES (%s, %s, %s, %s);"
                self.execute_query(item_sql, (order_id, product_id, quantity, price_at_purchase), fetch_results=False)

                update_stock_sql = "UPDATE products SET stock_quantity = stock_quantity - %s WHERE product_id = %s;"
                self.execute_query(update_stock_sql, (quantity, product_id), fetch_results=False)

            self.conn.commit() # Commit transaction if all steps succeed
            print(f"Order {order_id} created successfully, Total Amount: {total_amount:.2f}")
            return order_id

        except ValueError as ve:
            self.conn.rollback()
            print(f"Failed to create order (Validation Error): {ve}")
            return None
        except psycopg2.Error as e:
            self.conn.rollback() # Rollback on database errors
            print(f"Failed to create order (Database Error): {e}")
            return None
        except Exception as e:
            self.conn.rollback() # Catch other unexpected errors and rollback
            print(f"Failed to create order (Unexpected Error): {e}")
            return None
        finally:
            self.conn.autocommit = True # Restore autocommit to default behavior

    def get_customer_order_history(self, customer_id):
        """Queries and prints the order history for a specific customer, using the view."""
        sql = "SELECT * FROM customer_order_details WHERE customer_id = %s;"
        results = self.execute_query(sql, (customer_id,))
        if results and not results.get('error'): # Check for actual results, not just an error dict
            print(f"\n--- Order History for Customer ID {customer_id} ---")
            for row in results:
                order_date_str = row['order_date'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(row['order_date'], datetime) else str(row['order_date'])
                print(f"  Order ID: {row['order_id']}, Date: {order_date_str}, "
                      f"Product: {row['product_name']}, Qty: {row['quantity']}, Unit Price: {row['price_at_purchase']:.2f}, "
                      f"Order Total: {row['total_amount']:.2f}, Status: {row['status']}")
            print("---------------------------------------")
        elif results.get('error'):
            print(f"Error fetching order history: {results['error']}")
        else:
            print(f"No order history found for Customer ID {customer_id}.")
        return results

    def get_top_selling_products(self, limit=5):
        """Queries and prints the top-selling products by total quantity sold."""
        sql = """
        SELECT
            p.product_name,
            SUM(oi.quantity) AS total_quantity_sold
        FROM
            products p
        JOIN
            order_items oi ON p.product_id = oi.product_id
        GROUP BY
            p.product_name
        ORDER BY
            total_quantity_sold DESC
        LIMIT %s;
        """
        results = self.execute_query(sql, (limit,))
        if results and not results.get('error'):
            print(f"\n--- Top {limit} Selling Products ---")
            for row in results:
                print(f"  Product: {row['product_name']}, Total Sold: {row['total_quantity_sold']}")
            print("--------------------------")
        elif results.get('error'):
            print(f"Error fetching top selling products: {results['error']}")
        else:
            print("No product sales data available.")
        return results

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.cursor.close()
            self.conn.close()
            print("Database connection closed.")

# --- Main Program Entry Point ---
def main():
    # IMPORTANT: Configure your PostgreSQL connection parameters here
    # Replace 'your_username' and 'your_password' with your actual credentials.
    db_config = {
        "dbname": "ecommerce_db",
        "user": "your_username",
        "password": "your_password",
        "host": "localhost",
        "port": "5432"
    }

    try:
        manager = ECommerceManager(**db_config)
    except psycopg2.Error:
        print("Failed to connect to the database. Please check your database configuration and ensure PostgreSQL service is running.")
        return

    print("\n--- Starting E-commerce System Demonstration ---")

    # 1. Add Customers
    print("\n--- Adding Customers ---")
    customer1_id = manager.add_customer("Alice", "Smith", "alice.smith@example.com", "123-456-7890")
    customer2_id = manager.add_customer("Bob", "Johnson", "bob.j@example.com")

    # 2. Add Products
    print("\n--- Adding Products ---")
    product1_id = manager.add_product("Smartphone X", "Latest model smartphone", 999.99, 100)
    product2_id = manager.add_product("Wireless Earbuds Pro", "Noise-cancelling earbuds", 199.00, 200)
    product3_id = manager.add_product("Laptop Ultra", "High-performance ultrabook", 1499.00, 50)
    product4_id = manager.add_product("Smart Watch 2.0", "Fitness and notification watch", 299.00, 75)


    # 3. Create Orders (with transaction handling)
    print("\n--- Creating Orders ---")
    if customer1_id and product1_id and product2_id:
        # Alice buys 1 Smartphone X and 2 Wireless Earbuds Pro
        order1_products = [(product1_id, 1), (product2_id, 2)]
        order1_id = manager.create_order(customer1_id, order1_products)

    if customer2_id and product1_id and product3_id:
        # Bob buys 2 Smartphone X and 1 Laptop Ultra
        order2_products = [(product1_id, 2), (product3_id, 1)]
        order2_id = manager.create_order(customer2_id, order2_products)

    # Attempt to create an order with insufficient stock (should roll back)
    print("\n--- Attempting to create an order with insufficient stock ---")
    if customer1_id and product3_id:
        manager.create_order(customer1_id, [(product3_id, 100)]) # Laptop Ultra only has 50 in stock

    # 4. Query Customer Order History (using the view)
    if customer1_id:
        manager.get_customer_order_history(customer1_id)
    if customer2_id:
        manager.get_customer_order_history(customer2_id)

    # 5. Query Top Selling Products
    manager.get_top_selling_products(limit=3)

    # 6. Demonstrate direct execution of a complex SQL query
    print("\n--- Executing a Custom Complex SQL Query (e.g., Total Spent per Customer) ---")
    print("Query: Calculate total orders and total spent for each customer:")
    complex_query = """
    SELECT
        c.first_name,
        c.last_name,
        COUNT(o.order_id) AS total_orders,
        COALESCE(SUM(o.total_amount), 0.00) AS total_spent -- COALESCE handles customers with no orders
    FROM
        customers c
    LEFT JOIN
        orders o ON c.customer_id = o.customer_id
    GROUP BY
        c.customer_id, c.first_name, c.last_name
    ORDER BY
        total_spent DESC;
    """
    results = manager.execute_query(complex_query)
    if results and not results.get('error'):
        for row in results:
            print(f"  Customer: {row['first_name']} {row['last_name']}, Orders: {row['total_orders']}, Total Spent: {row['total_spent']:.2f}")
    elif results.get('error'):
        print(f"Error executing custom query: {results['error']}")

    # 7. Update Product Stock (example)
    print("\n--- Updating Product Stock (example) ---")
    if product2_id:
        update_sql = "UPDATE products SET stock_quantity = %s WHERE product_id = %s;"
        update_result = manager.execute_query(update_sql, (150, product2_id)) # Set Wireless Earbuds Pro stock to 150
        if not update_result.get('error'):
            print(f"Product ID {product2_id} (Wireless Earbuds Pro) stock updated successfully. Rows affected: {update_result.get('rows_affected')}")
        else:
            print(f"Failed to update product stock: {update_result['error']}")

    # 8. Deleting a customer (will cascade delete their orders and order items due to ON DELETE CASCADE)
    # print("\n--- Deleting a Customer (Note: This will cascade delete their orders and order items) ---")
    # if customer1_id:
    #     delete_result = manager.execute_query("DELETE FROM customers WHERE customer_id = %s;", (customer1_id,))
    #     if not delete_result.get('error'):
    #         print(f"Customer ID {customer1_id} and associated orders/items deleted successfully. Rows affected: {delete_result.get('rows_affected')}")
    #     else:
    #         print(f"Failed to delete customer: {delete_result['error']}")
    #     # Verify deletion
    #     manager.get_customer_order_history(customer1_id) # Should now say "No order history found"

    print("\n--- Demonstration Complete ---")
    # Close the database connection
    manager.close()

if __name__ == "__main__":
    main()
