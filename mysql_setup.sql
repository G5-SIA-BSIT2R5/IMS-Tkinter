-- Drop the database if it exists (careful: this deletes all data)
DROP DATABASE IF EXISTS inventory_db;

-- Create the database
CREATE DATABASE IF NOT EXISTS inventory_db;
USE inventory_db;

-- Create the products table
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100)
);

-- Create the warehouses table
CREATE TABLE warehouses (
    warehouse_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255)
);

-- Create the locations table
CREATE TABLE locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    warehouse_id INT,
    zone VARCHAR(50),
    aisle VARCHAR(50),
    bin VARCHAR(50),
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id) ON DELETE CASCADE
);

-- Create the inventory table
CREATE TABLE inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    location_id INT,
    quantity INT,
    status ENUM('available', 'reserved', 'in-transit', 'damaged'),
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(location_id) ON DELETE CASCADE
);

-- Create the serial_batches table
CREATE TABLE serial_batches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    serial_or_batch_number VARCHAR(100),
    type ENUM('serial', 'batch'),
    expiry_date DATE,
    received_date DATE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- Create the stock_movements table
CREATE TABLE stock_movements (
    movement_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    quantity INT,
    from_location INT,
    to_location INT,
    movement_type VARCHAR(50),
    timestamp DATETIME,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (from_location) REFERENCES locations(location_id) ON DELETE SET NULL,
    FOREIGN KEY (to_location) REFERENCES locations(location_id) ON DELETE SET NULL
);

-- Create the reorder_rules table
CREATE TABLE reorder_rules (
    product_id INT,
    min_threshold INT,
    reorder_point INT,
    auto_order_enabled BOOLEAN,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    PRIMARY KEY (product_id)
);

-- Create the audit_logs table
CREATE TABLE audit_logs (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    inventory_id INT,
    action VARCHAR(255),
    reason TEXT,
    changed_by VARCHAR(100),
    timestamp DATETIME,
    FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON DELETE CASCADE
);

-- Create the users table
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    password VARCHAR(255),
    role ENUM('Admin', 'Warehouse Manager', 'Auditor')
);

-- Insert a default admin user
INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'Admin');