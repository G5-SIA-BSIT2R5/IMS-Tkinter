import mysql.connector
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import csv
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Database Manager Class for MySQL
class DatabaseManager:
    def __init__(self, host="127.0.0.1", user="root", password="", database="inventory_db"):
        try:
            self.conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
            self.cursor = self.conn.cursor()
            self.create_tables()
            logging.info("Database connection established")
        except mysql.connector.Error as e:
            logging.error(f"Database connection failed: {e}")
            raise

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(100)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouses (
                warehouse_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                location VARCHAR(255)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                location_id INT AUTO_INCREMENT PRIMARY KEY,
                warehouse_id INT,
                zone VARCHAR(50),
                aisle VARCHAR(50),
                bin VARCHAR(50),
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id) ON DELETE CASCADE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                inventory_id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT,
                location_id INT,
                quantity INT,
                status ENUM('available', 'reserved', 'in-transit', 'damaged'),
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES locations(location_id) ON DELETE CASCADE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS serial_batches (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT,
                serial_or_batch_number VARCHAR(100),
                type ENUM('serial', 'batch'),
                expiry_date DATE,
                received_date DATE,
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_movements (
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
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reorder_rules (
                product_id INT,
                min_threshold INT,
                reorder_point INT,
                auto_order_enabled BOOLEAN,
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
                PRIMARY KEY (product_id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                audit_id INT AUTO_INCREMENT PRIMARY KEY,
                inventory_id INT,
                action VARCHAR(255),
                reason TEXT,
                changed_by VARCHAR(100),
                timestamp DATETIME,
                FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON DELETE CASCADE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE,
                password VARCHAR(255),
                role ENUM('Admin', 'Warehouse Manager', 'Auditor')
            )
        ''')
        self.conn.commit()
        logging.info("Database tables created or verified")

    def add_product(self, name, description, category):
        try:
            self.cursor.execute('INSERT INTO products (name, description, category) VALUES (%s, %s, %s)',
                              (name, description, category))
            self.conn.commit()
            logging.info(f"Product added: {name}")
        except mysql.connector.Error as e:
            logging.error(f"Error adding product: {e}")
            raise

    def add_warehouse(self, name, location):
        try:
            self.cursor.execute('INSERT INTO warehouses (name, location) VALUES (%s, %s)', (name, location))
            self.conn.commit()
            logging.info(f"Warehouse added: {name}")
        except mysql.connector.Error as e:
            logging.error(f"Error adding warehouse: {e}")
            raise

    def add_location(self, warehouse_id, zone, aisle, bin):
        try:
            self.cursor.execute('INSERT INTO locations (warehouse_id, zone, aisle, bin) VALUES (%s, %s, %s, %s)',
                              (warehouse_id, zone, aisle, bin))
            self.conn.commit()
            logging.info(f"Location added: {zone}, {aisle}, {bin}")
        except mysql.connector.Error as e:
            logging.error(f"Error adding location: {e}")
            raise

    def add_inventory(self, product_id, location_id, quantity, status):
        try:
            # Check if inventory record exists for product_id and location_id
            self.cursor.execute('SELECT inventory_id, quantity FROM inventory WHERE product_id = %s AND location_id = %s',
                              (product_id, location_id))
            existing = self.cursor.fetchone()
            if existing:
                inventory_id, current_quantity = existing
                new_quantity = current_quantity + quantity
                self.cursor.execute('UPDATE inventory SET quantity = %s, status = %s WHERE inventory_id = %s',
                                  (new_quantity, status, inventory_id))
                logging.info(f"Updated inventory: product_id={product_id}, location_id={location_id}, new_quantity={new_quantity}")
            else:
                self.cursor.execute('INSERT INTO inventory (product_id, location_id, quantity, status) VALUES (%s, %s, %s, %s)',
                                  (product_id, location_id, quantity, status))
                logging.info(f"Added new inventory: product_id={product_id}, location_id={location_id}, quantity={quantity}")
            self.conn.commit()
        except mysql.connector.Error as e:
            logging.error(f"Error adding/updating inventory: {e}")
            raise

    def add_serial_batch(self, product_id, serial_or_batch_number, type, expiry_date, received_date):
        try:
            self.cursor.execute('INSERT INTO serial_batches (product_id, serial_or_batch_number, type, expiry_date, received_date) VALUES (%s, %s, %s, %s, %s)',
                              (product_id, serial_or_batch_number, type, expiry_date, received_date))
            self.conn.commit()
            logging.info(f"Serial/Batch added: {serial_or_batch_number}")
        except mysql.connector.Error as e:
            logging.error(f"Error adding serial/batch: {e}")
            raise

    def log_movement(self, product_id, quantity, from_location, to_location, movement_type):
        try:
            timestamp = datetime.now()
            self.cursor.execute('INSERT INTO stock_movements (product_id, quantity, from_location, to_location, movement_type, timestamp) VALUES (%s, %s, %s, %s, %s, %s)',
                              (product_id, quantity, from_location, to_location, movement_type, timestamp))
            self.conn.commit()
            logging.info(f"Movement logged: {movement_type}, product_id={product_id}")
        except mysql.connector.Error as e:
            logging.error(f"Error logging movement: {e}")
            raise

    def log_audit(self, inventory_id, action, reason, changed_by):
        try:
            timestamp = datetime.now()
            self.cursor.execute('INSERT INTO audit_logs (inventory_id, action, reason, changed_by, timestamp) VALUES (%s, %s, %s, %s, %s)',
                              (inventory_id, action, reason, changed_by, timestamp))
            self.conn.commit()
            logging.info(f"Audit logged: inventory_id={inventory_id}, action={action}")
        except mysql.connector.Error as e:
            logging.error(f"Error logging audit: {e}")
            raise

    def set_reorder_rule(self, product_id, min_threshold, reorder_point, auto_order_enabled):
        try:
            self.cursor.execute('INSERT INTO reorder_rules (product_id, min_threshold, reorder_point, auto_order_enabled) VALUES (%s, %s, %s, %s) '
                              'ON DUPLICATE KEY UPDATE min_threshold=%s, reorder_point=%s, auto_order_enabled=%s',
                              (product_id, min_threshold, reorder_point, auto_order_enabled, min_threshold, reorder_point, auto_order_enabled))
            self.conn.commit()
            logging.info(f"Reorder rule set: product_id={product_id}")
        except mysql.connector.Error as e:
            logging.error(f"Error setting reorder rule: {e}")
            raise

    def check_expiry_alerts(self):
        today = datetime.now().date()
        thresholds = [30, 60, 90]
        alerts = []
        self.cursor.execute('SELECT product_id, serial_or_batch_number, expiry_date FROM serial_batches')
        for row in self.cursor.fetchall():
            product_id, batch_number, expiry_date = row
            if expiry_date:
                days_to_expiry = (expiry_date - today).days
                for days in thresholds:
                    if 0 <= days_to_expiry <= days:
                        alerts.append((product_id, batch_number, days))
        return alerts

    def check_reorder_alerts(self):
        alerts = []
        self.cursor.execute('''
            SELECT i.product_id, i.quantity, r.min_threshold, r.reorder_point
            FROM inventory i
            JOIN reorder_rules r ON i.product_id = r.product_id
            WHERE r.auto_order_enabled = 1 AND i.quantity <= r.min_threshold
        ''')
        for row in self.cursor.fetchall():
            alerts.append(row)
        return alerts

    def get_inventory_summary(self):
        try:
            self.cursor.execute('''
                SELECT p.name, i.quantity, i.status, w.name, l.zone, l.aisle, l.bin, i.inventory_id, p.product_id
                FROM inventory i
                JOIN products p ON i.product_id = p.product_id
                JOIN locations l ON i.location_id = l.location_id
                JOIN warehouses w ON l.warehouse_id = w.warehouse_id
            ''')
            result = self.cursor.fetchall()
            logging.info(f"Inventory summary retrieved: {len(result)} records")
            return result
        except mysql.connector.Error as e:
            logging.error(f"Error retrieving inventory summary: {e}")
            return []

    def get_warehouses(self):
        try:
            self.cursor.execute('SELECT warehouse_id, name, location FROM warehouses')
            return self.cursor.fetchall()
        except mysql.connector.Error as e:
            logging.error(f"Error retrieving warehouses: {e}")
            return []

    def get_locations(self):
        try:
            self.cursor.execute('''
                SELECT l.location_id, w.name, l.zone, l.aisle, l.bin
                FROM locations l
                JOIN warehouses w ON l.warehouse_id = w.warehouse_id
            ''')
            return self.cursor.fetchall()
        except mysql.connector.Error as e:
            logging.error(f"Error retrieving locations: {e}")
            return []

    def get_products(self):
        try:
            self.cursor.execute('SELECT product_id, name FROM products')
            return self.cursor.fetchall()
        except mysql.connector.Error as e:
            logging.error(f"Error retrieving products: {e}")
            return []

    def authenticate_user(self, username, password):
        try:
            self.cursor.execute('SELECT role FROM users WHERE username = %s AND password = %s', (username, password))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except mysql.connector.Error as e:
            logging.error(f"Error authenticating user: {e}")
            return None

    def close(self):
        self.conn.close()
        logging.info("Database connection closed")

# GUI Application
class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.style = ttk.Style(theme="flatly")
        self.db = DatabaseManager(host="127.0.0.1", user="root", password="", database="inventory_db")
        self.current_user = None
        self.role = None

        # Main frame
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Override destroy to ensure clean closure
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Show login
        self.show_login()

    def on_closing(self):
        try:
            self.db.close()
            self.root.destroy()
        except Exception as e:
            logging.error(f"Error during window closure: {e}")
            self.root.destroy()

    def show_login(self):
        self.clear_main_frame()
        login_frame = ttk.Frame(self.main_frame, padding=20, bootstyle="primary")
        login_frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(login_frame, text="Inventory Management System", font=("Helvetica", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        ttk.Label(login_frame, text="Username:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.username_entry = ttk.Entry(login_frame)
        self.username_entry.grid(row=1, column=1, padx=5, pady=5)
        ToolTip(self.username_entry, text="Enter your username")
        ttk.Label(login_frame, text="Password:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.password_entry = ttk.Entry(login_frame, show="*")
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)
        ToolTip(self.password_entry, text="Enter your password")
        ttk.Button(login_frame, text="Login", command=self.login, bootstyle="primary").grid(row=3, column=0, columnspan=2, pady=10)

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        self.role = self.db.authenticate_user(username, password)
        if self.role:
            self.current_user = username
            self.create_main_interface()
        else:
            messagebox.showerror("Error", "Invalid credentials")

    def create_main_interface(self):
        self.clear_main_frame()

        # Notebook for tabs
        notebook = ttk.Notebook(self.main_frame)
        notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # Dashboard tab
        self.dashboard_frame = ttk.Frame(notebook, padding=10)
        notebook.add(self.dashboard_frame, text="Dashboard")
        self.update_dashboard()

        # Add Product tab
        self.add_product_frame = ttk.Frame(notebook, padding=10)
        notebook.add(self.add_product_frame, text="Add Product")
        self.create_add_product_form()

        # Add Warehouse tab
        self.add_warehouse_frame = ttk.Frame(notebook, padding=10)
        notebook.add(self.add_warehouse_frame, text="Add Warehouse")
        self.create_add_warehouse_form()

        # Add Location tab
        self.add_location_frame = ttk.Frame(notebook, padding=10)
        notebook.add(self.add_location_frame, text="Add Location")
        self.create_add_location_form()

        # Stock Movement tab
        if self.role in ["Admin", "Warehouse Manager"]:
            self.stock_movement_frame = ttk.Frame(notebook, padding=10)
            notebook.add(self.stock_movement_frame, text="Stock Movement")
            self.create_stock_movement_form()

        # Serial/Batch tab
        if self.role in ["Admin", "Warehouse Manager"]:
            self.serial_batch_frame = ttk.Frame(notebook, padding=10)
            notebook.add(self.serial_batch_frame, text="Add Serial/Batch")
            self.create_add_serial_batch_form()

        # Adjust Inventory tab
        if self.role == "Admin":
            self.adjust_inventory_frame = ttk.Frame(notebook, padding=10)
            notebook.add(self.adjust_inventory_frame, text="Adjust Inventory")
            self.create_adjust_inventory_form()

        # Reorder Rules tab
        if self.role == "Admin":
            self.reorder_rules_frame = ttk.Frame(notebook, padding=10)
            notebook.add(self.reorder_rules_frame, text="Reorder Rules")
            self.create_set_reorder_rules_form()

        # Reports tab
        self.reports_frame = ttk.Frame(notebook, padding=10)
        notebook.add(self.reports_frame, text="Reports")
        self.create_reports_form()

    def update_dashboard(self):
        for widget in self.dashboard_frame.winfo_children():
            widget.destroy()

        # Search bar
        search_frame = ttk.Frame(self.dashboard_frame)
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ttk.Label(search_frame, text="Search Product:").grid(row=0, column=0, padx=5, pady=5)
        search_entry = ttk.Entry(search_frame)
        search_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(search_frame, text="Search", command=lambda: self.filter_dashboard(search_entry.get()), bootstyle="info").grid(row=0, column=2, padx=5, pady=5)

        # Summary
        summary_frame = ttk.LabelFrame(self.dashboard_frame, text="Summary", padding=10)
        summary_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.db.cursor.execute('SELECT COUNT(*) FROM products')
        total_products = self.db.cursor.fetchone()[0]
        self.db.cursor.execute('SELECT COUNT(*) FROM inventory WHERE quantity <= 10')
        low_stock = self.db.cursor.fetchone()[0]
        ttk.Label(summary_frame, text=f"Total Products: {total_products}").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(summary_frame, text=f"Low Stock Items: {low_stock}", bootstyle="danger").grid(row=0, column=1, padx=5, pady=5)

        # Inventory table
        tree_frame = ttk.LabelFrame(self.dashboard_frame, text="Inventory", padding=10)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.dashboard_frame.columnconfigure(0, weight=1)
        self.dashboard_frame.rowconfigure(2, weight=1)

        tree = ttk.Treeview(tree_frame, columns=("Inventory ID", "Product ID", "Product", "Quantity", "Status", "Warehouse", "Zone", "Aisle", "Bin"), show="headings", bootstyle="primary")
        tree.heading("Inventory ID", text="Inventory ID")
        tree.heading("Product ID", text="Product ID")
        tree.heading("Product", text="Product")
        tree.heading("Quantity", text="Quantity")
        tree.heading("Status", text="Status")
        tree.heading("Warehouse", text="Warehouse")
        tree.heading("Zone", text="Zone")
        tree.heading("Aisle", text="Aisle")
        tree.heading("Bin", text="Bin")
        tree.column("Inventory ID", width=100)
        tree.column("Product ID", width=100)
        tree.column("Product", width=150)
        tree.column("Quantity", width=80)
        tree.column("Status", width=100)
        tree.column("Warehouse", width=120)
        tree.column("Zone", width=80)
        tree.column("Aisle", width=80)
        tree.column("Bin", width=80)

        summary = self.db.get_inventory_summary()
        for row in summary:
            color = "success" if row[2] == "available" else "danger" if row[2] == "damaged" else "warning"
            tree.insert("", "end", values=row, tags=(color,))
        tree.tag_configure("success", background="#d4edda")
        tree.tag_configure("danger", background="#f8d7da")
        tree.tag_configure("warning", background="#fff3cd")
        tree.pack(fill="both", expand=True)

        ttk.Button(tree_frame, text="Refresh", command=self.update_dashboard, bootstyle="info").pack(pady=5)

    def filter_dashboard(self, search_term):
        for widget in self.dashboard_frame.winfo_children():
            widget.destroy()
        self.update_dashboard()  # Rebuild dashboard
        tree_frame = self.dashboard_frame.winfo_children()[-1]  # Last child is tree_frame
        tree = tree_frame.winfo_children()[0]  # First child is Treeview
        for item in tree.get_children():
            values = tree.item(item, "values")
            if not search_term.lower() in values[2].lower():  # Check product name
                tree.delete(item)

    def create_add_product_form(self):
        form = ttk.LabelFrame(self.add_product_frame, text="Add Product", padding=10)
        form.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        ttk.Label(form, text="Name:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        name_entry = ttk.Entry(form)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        ToolTip(name_entry, text="Enter product name (required)")

        ttk.Label(form, text="Description:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        desc_entry = ttk.Entry(form)
        desc_entry.grid(row=1, column=1, padx=5, pady=5)
        ToolTip(desc_entry, text="Enter product description (optional)")

        ttk.Label(form, text="Category:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        cat_entry = ttk.Entry(form)
        cat_entry.grid(row=2, column=1, padx=5, pady=5)
        ToolTip(cat_entry, text="Enter product category (optional)")

        ttk.Label(form, text="Quantity:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        quantity_entry = ttk.Entry(form)
        quantity_entry.grid(row=3, column=1, padx=5, pady=5)
        ToolTip(quantity_entry, text="Enter quantity (required, non-negative)")

        ttk.Label(form, text="Status:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        status_combo = ttk.Combobox(form, values=["available", "reserved", "in-transit", "damaged"], bootstyle="primary")
        status_combo.grid(row=4, column=1, padx=5, pady=5)
        status_combo.set("available")
        ToolTip(status_combo, text="Select inventory status")

        locations = self.db.get_locations()
        if not locations:
            ttk.Label(form, text="No locations available. Add a warehouse and location first.", bootstyle="danger").grid(row=5, column=0, columnspan=2, pady=5)
        else:
            ttk.Label(form, text="Location:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
            location_combo = ttk.Combobox(form, values=[f"{loc[1]} (Zone: {loc[2]}, Aisle: {loc[3]}, Bin: {loc[4]})" for loc in locations], bootstyle="primary")
            location_combo.grid(row=5, column=1, padx=5, pady=5)
            location_combo.set(locations[0][1] if locations else "")
            ToolTip(location_combo, text="Select storage location")

        ttk.Button(form, text="Save", command=lambda: self.save_product(
            name_entry.get(), desc_entry.get(), cat_entry.get(),
            quantity_entry.get(), status_combo.get(), location_combo.get() if locations else "", locations
        ), bootstyle="success").grid(row=6, column=0, columnspan=2, pady=10)

    def save_product(self, name, description, category, quantity, status, location_str, locations):
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        if not quantity:
            messagebox.showerror("Error", "Quantity is required")
            return
        if not locations:
            messagebox.showerror("Error", "No locations available. Please add a warehouse and location first.")
            return
        try:
            quantity = int(quantity)
            if quantity < 0:
                raise ValueError("Quantity cannot be negative")

            selected_location = next((loc for loc in locations if f"{loc[1]} (Zone: {loc[2]}, Aisle: {loc[3]}, Bin: {loc[4]})" == location_str), None)
            if not selected_location:
                messagebox.showerror("Error", "Invalid location selected")
                return
            location_id = selected_location[0]

            self.db.add_product(name, description, category)
            self.db.cursor.execute("SELECT LAST_INSERT_ID()")
            product_id = self.db.cursor.fetchone()[0]
            self.db.add_inventory(product_id, location_id, quantity, status)
            messagebox.showinfo("Success", "Product and inventory record added")
            self.update_dashboard()
        except (ValueError, mysql.connector.Error) as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")
            logging.error(f"Error saving product: {e}")

    def create_add_warehouse_form(self):
        form = ttk.LabelFrame(self.add_warehouse_frame, text="Add Warehouse", padding=10)
        form.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        ttk.Label(form, text="Name:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        name_entry = ttk.Entry(form)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        ToolTip(name_entry, text="Enter warehouse name (required)")

        ttk.Label(form, text="Location:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        location_entry = ttk.Entry(form)
        location_entry.grid(row=1, column=1, padx=5, pady=5)
        ToolTip(location_entry, text="Enter warehouse location (optional)")

        ttk.Button(form, text="Save", command=lambda: self.save_warehouse(
            name_entry.get(), location_entry.get()
        ), bootstyle="success").grid(row=2, column=0, columnspan=2, pady=10)

    def save_warehouse(self, name, location):
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        try:
            self.db.add_warehouse(name, location)
            messagebox.showinfo("Success", "Warehouse added")
            self.create_add_warehouse_form()
            self.create_add_location_form()
            self.create_add_product_form()
        except mysql.connector.Error as e:
            messagebox.showerror("Error", f"Failed to add warehouse: {e}")

    def create_add_location_form(self):
        form = ttk.LabelFrame(self.add_location_frame, text="Add Location", padding=10)
        form.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        warehouses = self.db.get_warehouses()
        ttk.Label(form, text="Warehouse:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        warehouse_combo = ttk.Combobox(form, values=[f"{w[1]} ({w[2]})" for w in warehouses], bootstyle="primary")
        warehouse_combo.grid(row=0, column=1, padx=5, pady=5)
        warehouse_combo.set(warehouses[0][1] if warehouses else "")
        ToolTip(warehouse_combo, text="Select warehouse")

        ttk.Label(form, text="Zone:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        zone_entry = ttk.Entry(form)
        zone_entry.grid(row=1, column=1, padx=5, pady=5)
        ToolTip(zone_entry, text="Enter zone (required)")

        ttk.Label(form, text="Aisle:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        aisle_entry = ttk.Entry(form)
        aisle_entry.grid(row=2, column=1, padx=5, pady=5)
        ToolTip(aisle_entry, text="Enter aisle (required)")

        ttk.Label(form, text="Bin:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        bin_entry = ttk.Entry(form)
        bin_entry.grid(row=3, column=1, padx=5, pady=5)
        ToolTip(bin_entry, text="Enter bin (required)")

        ttk.Button(form, text="Save", command=lambda: self.save_location(
            warehouse_combo.get(), zone_entry.get(), aisle_entry.get(), bin_entry.get(), warehouses
        ), bootstyle="success").grid(row=4, column=0, columnspan=2, pady=10)

    def save_location(self, warehouse_str, zone, aisle, bin, warehouses):
        if not warehouse_str or not zone or not aisle or not bin:
            messagebox.showerror("Error", "All fields are required")
            return
        selected_warehouse = next((w for w in warehouses if f"{w[1]} ({w[2]})" == warehouse_str), None)
        if not selected_warehouse:
            messagebox.showerror("Error", "Invalid warehouse selected")
            return
        warehouse_id = selected_warehouse[0]
        try:
            self.db.add_location(warehouse_id, zone, aisle, bin)
            messagebox.showinfo("Success", "Location added")
            self.create_add_location_form()
            self.create_add_product_form()
        except mysql.connector.Error as e:
            messagebox.showerror("Error", f"Failed to add location: {e}")

    def create_stock_movement_form(self):
        form = ttk.LabelFrame(self.stock_movement_frame, text="Stock Movement", padding=10)
        form.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        products = self.db.get_products()
        ttk.Label(form, text="Product:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        product_combo = ttk.Combobox(form, values=[f"{p[1]} (ID: {p[0]})" for p in products], bootstyle="primary")
        product_combo.grid(row=0, column=1, padx=5, pady=5)
        product_combo.set(products[0][1] if products else "")
        ToolTip(product_combo, text="Select product")

        ttk.Label(form, text="Quantity:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        quantity_entry = ttk.Entry(form)
        quantity_entry.grid(row=1, column=1, padx=5, pady=5)
        ToolTip(quantity_entry, text="Enter quantity (required, non-negative)")

        ttk.Label(form, text="From Location ID:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        from_loc_entry = ttk.Entry(form)
        from_loc_entry.grid(row=2, column=1, padx=5, pady=5)
        ToolTip(from_loc_entry, text="Enter source location ID (optional)")

        ttk.Label(form, text="To Location ID:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        to_loc_entry = ttk.Entry(form)
        to_loc_entry.grid(row=3, column=1, padx=5, pady=5)
        ToolTip(to_loc_entry, text="Enter destination location ID (optional)")

        ttk.Label(form, text="Movement Type:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        movement_type = ttk.Combobox(form, values=["transfer", "sale", "return", "restock"], bootstyle="primary")
        movement_type.grid(row=4, column=1, padx=5, pady=5)
        ToolTip(movement_type, text="Select movement type")

        ttk.Button(form, text="Save", command=lambda: self.save_movement(
            product_combo.get(), quantity_entry.get(), from_loc_entry.get(), to_loc_entry.get(), movement_type.get(), products
        ), bootstyle="success").grid(row=5, column=0, columnspan=2, pady=10)

    def save_movement(self, product_str, quantity, from_loc, to_loc, movement_type, products):
        if not product_str or not quantity or not movement_type:
            messagebox.showerror("Error", "Product, quantity, and movement type are required")
            return
        try:
            selected_product = next((p for p in products if f"{p[1]} (ID: {p[0]})" == product_str), None)
            if not selected_product:
                messagebox.showerror("Error", "Invalid product selected")
                return
            product_id = selected_product[0]
            quantity = int(quantity)
            if quantity < 0:
                raise ValueError("Quantity cannot be negative")
            from_loc = int(from_loc) if from_loc else None
            to_loc = int(to_loc) if to_loc else None
            self.db.log_movement(product_id, quantity, from_loc, to_loc, movement_type)
            if movement_type == "sale":
                self.db.cursor.execute('UPDATE inventory SET quantity = quantity - %s WHERE product_id = %s', (quantity, product_id))
            elif movement_type == "restock":
                self.db.cursor.execute('UPDATE inventory SET quantity = quantity + %s WHERE product_id = %s', (quantity, product_id))
            self.db.conn.commit()
            messagebox.showinfo("Success", "Movement recorded")
            self.update_dashboard()
        except (ValueError, mysql.connector.Error) as e:
            messagebox.showerror("Error", f"Invalid input: {e}")

    def create_add_serial_batch_form(self):
        form = ttk.LabelFrame(self.serial_batch_frame, text="Add Serial/Batch", padding=10)
        form.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        products = self.db.get_products()
        ttk.Label(form, text="Product:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        product_combo = ttk.Combobox(form, values=[f"{p[1]} (ID: {p[0]})" for p in products], bootstyle="primary")
        product_combo.grid(row=0, column=1, padx=5, pady=5)
        product_combo.set(products[0][1] if products else "")
        ToolTip(product_combo, text="Select product")

        ttk.Label(form, text="Serial/Batch Number:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        number_entry = ttk.Entry(form)
        number_entry.grid(row=1, column=1, padx=5, pady=5)
        ToolTip(number_entry, text="Enter serial or batch number")

        ttk.Label(form, text="Type:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        type_combo = ttk.Combobox(form, values=["serial", "batch"], bootstyle="primary")
        type_combo.grid(row=2, column=1, padx=5, pady=5)
        ToolTip(type_combo, text="Select serial or batch")

        ttk.Label(form, text="Expiry Date (YYYY-MM-DD):").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        expiry_entry = ttk.Entry(form)
        expiry_entry.grid(row=3, column=1, padx=5, pady=5)
        ToolTip(expiry_entry, text="Enter expiry date (e.g., 2025-12-31)")

        ttk.Label(form, text="Received Date (YYYY-MM-DD):").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        received_entry = ttk.Entry(form)
        received_entry.grid(row=4, column=1, padx=5, pady=5)
        ToolTip(received_entry, text="Enter received date (e.g., 2025-05-26)")

        ttk.Button(form, text="Save", command=lambda: self.save_serial_batch(
            product_combo.get(), number_entry.get(), type_combo.get(), expiry_entry.get(), received_entry.get(), products
        ), bootstyle="success").grid(row=5, column=0, columnspan=2, pady=10)

    def save_serial_batch(self, product_str, number, type, expiry_date, received_date, products):
        if not product_str or not number or not type:
            messagebox.showerror("Error", "Product, serial/batch number, and type are required")
            return
        try:
            selected_product = next((p for p in products if f"{p[1]} (ID: {p[0]})" == product_str), None)
            if not selected_product:
                messagebox.showerror("Error", "Invalid product selected")
                return
            product_id = selected_product[0]
            # Validate date format
            if expiry_date:
                datetime.strptime(expiry_date, '%Y-%m-%d')
            if received_date:
                datetime.strptime(received_date, '%Y-%m-%d')
            self.db.add_serial_batch(product_id, number, type, expiry_date or None, received_date or None)
            messagebox.showinfo("Success", "Serial/Batch added")
        except (ValueError, mysql.connector.Error) as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

    def create_adjust_inventory_form(self):
        form = ttk.LabelFrame(self.adjust_inventory_frame, text="Adjust Inventory", padding=10)
        form.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        ttk.Label(form, text="Inventory ID:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        inv_id_entry = ttk.Entry(form)
        inv_id_entry.grid(row=0, column=1, padx=5, pady=5)
        ToolTip(inv_id_entry, text="Enter inventory ID from dashboard")

        ttk.Label(form, text="Action:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        action_entry = ttk.Entry(form)
        action_entry.grid(row=1, column=1, padx=5, pady=5)
        ToolTip(action_entry, text="Describe the action (e.g., Adjust quantity)")

        ttk.Label(form, text="Reason:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        reason_entry = ttk.Entry(form)
        reason_entry.grid(row=2, column=1, padx=5, pady=5)
        ToolTip(reason_entry, text="Enter reason for adjustment")

        ttk.Button(form, text="Save", command=lambda: self.save_adjustment(
            inv_id_entry.get(), action_entry.get(), reason_entry.get()
        ), bootstyle="success").grid(row=3, column=0, columnspan=2, pady=10)

    def save_adjustment(self, inventory_id, action, reason):
        if not inventory_id or not action or not reason:
            messagebox.showerror("Error", "All fields are required")
            return
        try:
            inventory_id = int(inventory_id)
            self.db.log_audit(inventory_id, action, reason, self.current_user)
            messagebox.showinfo("Success", "Adjustment logged")
        except (ValueError, mysql.connector.Error) as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

    def create_set_reorder_rules_form(self):
        form = ttk.LabelFrame(self.reorder_rules_frame, text="Set Reorder Rules", padding=10)
        form.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        products = self.db.get_products()
        ttk.Label(form, text="Product:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        product_combo = ttk.Combobox(form, values=[f"{p[1]} (ID: {p[0]})" for p in products], bootstyle="primary")
        product_combo.grid(row=0, column=1, padx=5, pady=5)
        product_combo.set(products[0][1] if products else "")
        ToolTip(product_combo, text="Select product")

        ttk.Label(form, text="Min Threshold:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        min_entry = ttk.Entry(form)
        min_entry.grid(row=1, column=1, padx=5, pady=5)
        ToolTip(min_entry, text="Enter minimum stock threshold")

        ttk.Label(form, text="Reorder Point:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        reorder_entry = ttk.Entry(form)
        reorder_entry.grid(row=2, column=1, padx=5, pady=5)
        ToolTip(reorder_entry, text="Enter reorder point")

        ttk.Label(form, text="Auto Order:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        auto_var = tk.BooleanVar()
        ttk.Checkbutton(form, variable=auto_var, bootstyle="success").grid(row=3, column=1, padx=5, pady=5)
        ToolTip(ttk.Checkbutton(form, variable=auto_var), text="Enable automatic reordering")

        ttk.Button(form, text="Save", command=lambda: self.save_reorder_rule(
            product_combo.get(), min_entry.get(), reorder_entry.get(), auto_var.get(), products
        ), bootstyle="success").grid(row=4, column=0, columnspan=2, pady=10)

    def save_reorder_rule(self, product_str, min_threshold, reorder_point, auto_order, products):
        if not product_str or not min_threshold or not reorder_point:
            messagebox.showerror("Error", "Product, min threshold, and reorder point are required")
            return
        try:
            selected_product = next((p for p in products if f"{p[1]} (ID: {p[0]})" == product_str), None)
            if not selected_product:
                messagebox.showerror("Error", "Invalid product selected")
                return
            product_id = selected_product[0]
            min_threshold = int(min_threshold)
            reorder_point = int(reorder_point)
            self.db.set_reorder_rule(product_id, min_threshold, reorder_point, auto_order)
            messagebox.showinfo("Success", "Reorder rule set")
        except (ValueError, mysql.connector.Error) as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

    def create_reports_form(self):
        form = ttk.LabelFrame(self.reports_frame, text="Reports", padding=10)
        form.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        ttk.Button(form, text="Inventory Summary", command=self.inventory_summary_report, bootstyle="info").grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(form, text="Expiry Alerts", command=self.expiry_alerts_report, bootstyle="info").grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(form, text="Reorder Alerts", command=self.reorder_alerts_report, bootstyle="info").grid(row=0, column=2, padx=5, pady=5)
        if self.role == "Admin":
            ttk.Button(form, text="Audit Logs", command=self.audit_logs_report, bootstyle="info").grid(row=0, column=3, padx=5, pady=5)

        self.report_display = ttk.Frame(form)
        self.report_display.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=10)

    def inventory_summary_report(self):
        for widget in self.report_display.winfo_children():
            widget.destroy()
        tree = ttk.Treeview(self.report_display, columns=("Inventory ID", "Product ID", "Product", "Quantity", "Status", "Warehouse", "Zone", "Aisle", "Bin"), show="headings", bootstyle="primary")
        tree.heading("Inventory ID", text="Inventory ID")
        tree.heading("Product ID", text="Product ID")
        tree.heading("Product", text="Product")
        tree.heading("Quantity", text="Quantity")
        tree.heading("Status", text="Status")
        tree.heading("Warehouse", text="Warehouse")
        tree.heading("Zone", text="Zone")
        tree.heading("Aisle", text="Aisle")
        tree.heading("Bin", text="Bin")
        summary = self.db.get_inventory_summary()
        for row in summary:
            tree.insert("", "end", values=row)
        tree.pack(fill="both", expand=True)
        ttk.Button(self.report_display, text="Export to CSV", command=lambda: self.export_to_csv(summary, "inventory_summary.csv"), bootstyle="success").pack(pady=5)

    def expiry_alerts_report(self):
        for widget in self.report_display.winfo_children():
            widget.destroy()
        tree = ttk.Treeview(self.report_display, columns=("Product ID", "Batch Number", "Days to Expiry"), show="headings", bootstyle="primary")
        tree.heading("Product ID", text="Product ID")
        tree.heading("Batch Number", text="Batch Number")
        tree.heading("Days to Expiry", text="Days to Expiry")
        alerts = self.db.check_expiry_alerts()
        for alert in alerts:
            tree.insert("", "end", values=alert)
        tree.pack(fill="both", expand=True)
        ttk.Button(self.report_display, text="Export to CSV", command=lambda: self.export_to_csv(alerts, "expiry_alerts.csv"), bootstyle="success").pack(pady=5)

    def reorder_alerts_report(self):
        for widget in self.report_display.winfo_children():
            widget.destroy()
        tree = ttk.Treeview(self.report_display, columns=("Product ID", "Quantity", "Min Threshold", "Reorder Point"), show="headings", bootstyle="primary")
        tree.heading("Product ID", text="Product ID")
        tree.heading("Quantity", text="Quantity")
        tree.heading("Min Threshold", text="Min Threshold")
        tree.heading("Reorder Point", text="Reorder Point")
        alerts = self.db.check_reorder_alerts()
        for alert in alerts:
            tree.insert("", "end", values=alert)
        tree.pack(fill="both", expand=True)
        ttk.Button(self.report_display, text="Export to CSV", command=lambda: self.export_to_csv(alerts, "reorder_alerts.csv"), bootstyle="success").pack(pady=5)

    def audit_logs_report(self):
        for widget in self.report_display.winfo_children():
            widget.destroy()
        tree = ttk.Treeview(self.report_display, columns=("Audit ID", "Inventory ID", "Action", "Reason", "Changed By", "Timestamp"), show="headings", bootstyle="primary")
        tree.heading("Audit ID", text="Audit ID")
        tree.heading("Inventory ID", text="Inventory ID")
        tree.heading("Action", text="Action")
        tree.heading("Reason", text="Reason")
        tree.heading("Changed By", text="Changed By")
        tree.heading("Timestamp", text="Timestamp")
        self.db.cursor.execute('SELECT * FROM audit_logs')
        logs = self.db.cursor.fetchall()
        for log in logs:
            tree.insert("", "end", values=log)
        tree.pack(fill="both", expand=True)
        ttk.Button(self.report_display, text="Export to CSV", command=lambda: self.export_to_csv(logs, "audit_logs.csv"), bootstyle="success").pack(pady=5)

    def export_to_csv(self, data, filename):
        try:
            with open(filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([col[0] for col in self.db.cursor.description] if self.db.cursor.description else data[0])
                writer.writerows(data)
            messagebox.showinfo("Success", f"Exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    app = InventoryApp(root)
    root.mainloop()