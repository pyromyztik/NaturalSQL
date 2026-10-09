-- Clean up existing tables
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- 1. Customers
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    city VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Products
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    stock_quantity INTEGER NOT NULL
);

-- 3. Orders
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id) ON DELETE CASCADE,
    order_date DATE NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL
);

-- 4. Order Items
CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(product_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL,
    item_price NUMERIC(10,2) NOT NULL
);

-- Seed Data: Customers
INSERT INTO customers (full_name, email, city) VALUES
('Alice Johnson', 'alice.j@example.com', 'New York'),
('Bob Smith', 'bob.smith@example.com', 'Austin'),
('Charlie Brown', 'charlie.b@example.com', 'San Francisco'),
('Diana Prince', 'diana.p@example.com', 'Chicago'),
('Evan Wright', 'evan.w@example.com', 'Austin');

-- Seed Data: Products
INSERT INTO products (product_name, category, unit_price, stock_quantity) VALUES
('Mechanical Keyboard', 'Electronics', 120.00, 45),
('Wireless Mouse', 'Electronics', 45.00, 120),
('USB-C Hub', 'Electronics', 35.50, 75),
('Denim Jacket', 'Clothing', 89.99, 30),
('Cotton T-Shirt', 'Clothing', 25.00, 150),
('Ceramic Coffee Mug', 'Home', 15.00, 200),
('Standing Desk', 'Home', 450.00, 15),
('Data Engineering Handbook', 'Books', 55.00, 60);

-- Seed Data: Orders
INSERT INTO orders (customer_id, order_date, order_status, total_amount) VALUES
(1, '2026-01-15', 'delivered', 165.00),
(1, '2026-02-10', 'delivered', 89.99),
(2, '2026-02-18', 'delivered', 450.00),
(3, '2026-03-01', 'shipped', 210.00),
(4, '2026-03-05', 'pending', 40.00),
(2, '2026-03-12', 'delivered', 70.50);

-- Seed Data: Order Items
INSERT INTO order_items (order_id, product_id, quantity, item_price) VALUES
(1, 1, 1, 120.00),
(1, 2, 1, 45.00),
(2, 4, 1, 89.99),
(3, 7, 1, 450.00),
(4, 1, 1, 120.00),
(4, 5, 2, 25.00),
(4, 6, 1, 15.00),
(5, 5, 1, 25.00),
(5, 6, 1, 15.00),
(6, 3, 2, 35.50);
