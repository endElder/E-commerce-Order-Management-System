-- 1. Create Customers Table
-- Stores information about individual customers.
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY, -- Unique identifier for the customer, auto-increments
    first_name VARCHAR(50) NOT NULL, -- Customer's first name
    last_name VARCHAR(50) NOT NULL,  -- Customer's last name
    email VARCHAR(100) UNIQUE NOT NULL, -- Customer's email, must be unique and not null
    phone VARCHAR(20),               -- Customer's phone number (optional)
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Date and time of customer registration
);

-- 2. Create Products Table
-- Stores information about the products available for sale.
CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,    -- Unique identifier for the product, auto-increments
    product_name VARCHAR(100) UNIQUE NOT NULL, -- Name of the product, must be unique and not null
    description TEXT,                -- Detailed description of the product (optional)
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0), -- Price of the product, cannot be negative
    stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0), -- Current stock level, cannot be negative
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Date and time when the product was added
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Last date and time the product was updated
);

-- 3. Create Orders Table
-- Stores high-level information about each order placed by customers.
CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,   -- Unique identifier for the order, auto-increments
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
                                   -- Foreign key linking to the customers table.
                                   -- ON DELETE CASCADE means if a customer is deleted, their orders are also deleted.
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Date and time the order was placed
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount >= 0), -- Total monetary value of the order
    status VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'))
                                   -- Current status of the order (e.g., Pending, Shipped)
);

-- 4. Create Order_Items Table
-- Stores details for each item within an order, linking products to specific orders.
-- This handles the many-to-many relationship between orders and products.
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id SERIAL PRIMARY KEY, -- Unique identifier for each item line in an order
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
                                     -- Foreign key linking to the orders table.
                                     -- ON DELETE CASCADE means if an order is deleted, its items are also deleted.
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
                                     -- Foreign key linking to the products table.
                                     -- ON DELETE RESTRICT means a product cannot be deleted if there are still order items referencing it.
    quantity INTEGER NOT NULL CHECK (quantity > 0), -- Quantity of the product ordered in this item line
    price_at_purchase DECIMAL(10, 2) NOT NULL CHECK (price_at_purchase >= 0),
                                     -- Price of the product at the time of purchase (important for historical accuracy)
    UNIQUE (order_id, product_id)    -- Ensures that a specific product appears only once in a given order
);

---

-- 5. Create Views
-- Views simplify complex queries by creating a virtual table based on the result-set of a SELECT query.
-- This view provides a detailed overview of every item in every customer's order.
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
-- Indexes speed up data retrieval by providing quick lookup paths for frequently queried columns.

-- Index on customers.email for faster lookup when logging in or checking customer details by email.
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers (email);

-- Index on orders.customer_id for faster retrieval of all orders belonging to a specific customer.
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);

-- Indexes on order_items.order_id and order_items.product_id for faster joins
-- and lookups involving order items.
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);

-- Re-enable client messages to default
RESET client_min_messages;
