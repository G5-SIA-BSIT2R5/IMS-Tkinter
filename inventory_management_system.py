import mysql.connector
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import csv
from tkcalendar import DateEntry

# Database Manager Class for MySQL
class DatabaseManager:
    def __init__(self, host="127.0.0.1", user="root", password="", database="inventory_db"):
        self.conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Create tables (executed for completeness, but SQL Workbench/J script is primary)
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

    def add_product(self, name, description, category):
        self.cursor.execute('INSERT INTO products (name, description, category) VALUES (%s, %s, %s)',
                          (name, description, category))
        self.conn.commit()

    def add_warehouse(self, name, location):
        self.cursor.execute('INSERT INTO warehouses (name, location) VALUES (%s, %s)', (name, location))
        self.conn.commit()

    def add_location(self, warehouse_id, zone, aisle, bin):
        self.cursor.execute('INSERT INTO locations (warehouse_id, zone, aisle, bin) VALUES (%s, %s, %s, %s)',
                          (warehouse_id, zone, aisle, bin))
        self.conn.commit()

    def add_inventory(self, product_id, location_id, quantity, status):
        self.cursor.execute('INSERT INTO inventory (product_id, location_id, quantity, status) VALUES (%s, %s, %s, %s)',
                          (product_id, location_id, quantity, status))
        self.conn.commit()

    def add_serial_batch(self, product_id, serial_or_batch_number, type, expiry_date, received_date):
        self.cursor.execute('INSERT INTO serial_batches (product_id, serial_or_batch_number, type, expiry_date, received_date) VALUES (%s, %s, %s, %s, %s)',
                          (product_id, serial_or_batch_number, type, expiry_date, received_date))
        self.conn.commit()

    def log_movement(self, product_id, quantity, from_location, to_location, movement_type):
        timestamp = datetime.now()
        self.cursor.execute('INSERT INTO stock_movements (product_id, quantity, from_location, to_location, movement_type, timestamp) VALUES (%s, %s, %s, %s, %s, %s)',
                          (product_id, quantity, from_location, to_location, movement_type, timestamp))
        self.conn.commit()

    def log_audit(self, inventory_id, action, reason, changed_by):
        timestamp = datetime.now()
        self.cursor.execute('INSERT INTO audit_logs (inventory_id, action, reason, changed_by, timestamp) VALUES (%s, %s, %s, %s, %s)',
                          (inventory_id, action, reason, changed_by, timestamp))
        self.conn.commit()

    def set_reorder_rule(self, product_id, min_threshold, reorder_point, auto_order_enabled):
        self.cursor.execute('INSERT INTO reorder_rules (product_id, min_threshold, reorder_point, auto_order_enabled) VALUES (%s, %s, %s, %s) '
                          'ON DUPLICATE KEY UPDATE min_threshold=%s, reorder_point=%s, auto_order_enabled=%s',
                          (product_id, min_threshold, reorder_point, auto_order_enabled, min_threshold, reorder_point, auto_order_enabled))
        self.conn.commit()

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
        self.cursor.execute('''
            SELECT p.name, i.quantity, i.status, w.name, l.zone, l.aisle, l.bin
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN locations l ON i.location_id = l.location_id
            JOIN warehouses w ON l.warehouse_id = w.warehouse_id
        ''')
        return self.cursor.fetchall()

    def authenticate_user(self, username, password):
        self.cursor.execute('SELECT role FROM users WHERE username = %s AND password = %s', (username, password))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def close(self):
        self.conn.close()

# GUI Application (unchanged from original)
class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.db = DatabaseManager(host="127.0.0.1", user="root", password="", database="inventory_db")
        self.current_user = None

        # Login Window
        self.login_frame = ttk.Frame(self.root)
        self.login_frame.pack(padx=10, pady=10)
        ttk.Label(self.login_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        self.username_entry = ttk.Entry(self.login_frame)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.login_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        self.password_entry = ttk.Entry(self.login_frame, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self.login_frame, text="Login", command=self.login).grid(row=2, column=0, columnspan=2, pady=10)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        role = self.db.authenticate_user(username, password)
        if role:
            self.current_user = username
            self.login_frame.destroy()
            self.create_main_interface(role)
        else:
            messagebox.showerror("Error", "Invalid credentials")

    def create_main_interface(self, role):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        inventory_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Inventory", menu=inventory_menu)
        inventory_menu.add_command(label="Add Product", command=self.add_product_form)
        inventory_menu.add_command(label="View Inventory", command=self.view_inventory)
        if role in ["Admin", "Warehouse Manager"]:
            inventory_menu.add_command(label="Stock Movement", command=self.stock_movement_form)
            inventory_menu.add_command(label="Add Serial/Batch", command=self.add_serial_batch_form)
        if role == "Admin":
            inventory_menu.add_command(label="Adjust Inventory", command=self.adjust_inventory_form)
            inventory_menu.add_command(label="Set Reorder Rules", command=self.set_reorder_rules_form)
        reports_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Reports", menu=reports_menu)
        reports_menu.add_command(label="Inventory Summary", command=self.inventory_summary_report)
        reports_menu.add_command(label="Expiry Alerts", command=self.expiry_alerts_report)
        reports_menu.add_command(label="Reorder Alerts", command=self.reorder_alerts_report)
        if role == "Admin":
            reports_menu.add_command(label="Audit Logs", command=self.audit_logs_report)

        self.dashboard_frame = ttk.Frame(self.root)
        self.dashboard_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.update_dashboard()

    def update_dashboard(self):
        for widget in self.dashboard_frame.winfo_children():
            widget.destroy()
        summary = self.db.get_inventory_summary()
        tree = ttk.Treeview(self.dashboard_frame, columns=("Product", "Quantity", "Status", "Warehouse", "Zone", "Aisle", "Bin"), show="headings")
        tree.heading("Product", text="Product")
        tree.heading("Quantity", text="Quantity")
        tree.heading("Status", text="Status")
        tree.heading("Warehouse", text="Warehouse")
        tree.heading("Zone", text="Zone")
        tree.heading("Aisle", text="Aisle")
        tree.heading("Bin", text="Bin")
        for row in summary:
            color = "green" if row[2] == "available" else "red" if row[2] == "damaged" else "orange"
            tree.insert("", "end", values=row, tags=(color,))
        tree.tag_configure("green", background="lightgreen")
        tree.tag_configure("red", background="salmon")
        tree.tag_configure("orange", background="orange")
        tree.pack(fill="both", expand=True)

    def add_product_form(self):
        form = tk.Toplevel(self.root)
        form.title("Add Product")
        ttk.Label(form, text="Name:").grid(row=0, column=0, padx=5, pady=5)
        name_entry = ttk.Entry(form)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(form, text="Description:").grid(row=1, column=0, padx=5, pady=5)
        desc_entry = ttk.Entry(form)
        desc_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(form, text="Category:").grid(row=2, column=0, padx=5, pady=5)
        cat_entry = ttk.Entry(form)
        cat_entry.grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(form, text="Save", command=lambda: self.save_product(name_entry.get(), desc_entry.get(), cat_entry.get(), form)).grid(row=3, column=0, columnspan=2, pady=10)

    def save_product(self, name, description, category, form):
        if name:
            self.db.add_product(name, description, category)
            messagebox.showinfo("Success", "Product added")
            form.destroy()
        else:
            messagebox.showerror("Error", "Name is required")

    def stock_movement_form(self):
        form = tk.Toplevel(self.root)
        form.title("Stock Movement")
        ttk.Label(form, text="Product ID:").grid(row=0, column=0, padx=5, pady=5)
        product_id_entry = ttk.Entry(form)
        product_id_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(form, text="Quantity:").grid(row=1, column=0, padx=5, pady=5)
        quantity_entry = ttk.Entry(form)
        quantity_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(form, text="From Location ID:").grid(row=2, column=0, padx=5, pady=5)
        from_loc_entry = ttk.Entry(form)
        from_loc_entry.grid(row=2, column=1, padx=5, pady=5)
        ttk.Label(form, text="To Location ID:").grid(row=3, column=0, padx=5, pady=5)
        to_loc_entry = ttk.Entry(form)
        to_loc_entry.grid(row=3, column=1, padx=5, pady=5)
        ttk.Label(form, text="Movement Type:").grid(row=4, column=0, padx=5, pady=5)
        movement_type = ttk.Combobox(form, values=["transfer", "sale", "return", "restock"])
        movement_type.grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(form, text="Save", command=lambda: self.save_movement(
            product_id_entry.get(), quantity_entry.get(), from_loc_entry.get(), to_loc_entry.get(), movement_type.get(), form)).grid(row=5, column=0, columnspan=2, pady=10)

    def save_movement(self, product_id, quantity, from_loc, to_loc, movement_type, form):
        try:
            product_id = int(product_id)
            quantity = int(quantity)
            from_loc = int(from_loc) if from_loc else None
            to_loc = int(to_loc) if to_loc else None
            self.db.log_movement(product_id, quantity, from_loc, to_loc, movement_type)
            if movement_type == "sale":
                self.db.cursor.execute('UPDATE inventory SET quantity = quantity - %s WHERE product_id = %s', (quantity, product_id))
            elif movement_type == "restock":
                self.db.cursor.execute('UPDATE inventory SET quantity = quantity + %s WHERE product_id = %s', (quantity, product_id))
            self.db.conn.commit()
            messagebox.showinfo("Success", "Movement recorded")
            form.destroy()
            self.update_dashboard()
        except ValueError:
            messagebox.showerror("Error", "Invalid input")

    def add_serial_batch_form(self):
        form = tk.Toplevel(self.root)
        form.title("Add Serial/Batch")
        ttk.Label(form, text="Product ID:").grid(row=0, column=0, padx=5, pady=5)
        product_id_entry = ttk.Entry(form)
        product_id_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(form, text="Serial/Batch Number:").grid(row=1, column=0, padx=5, pady=5)
        number_entry = ttk.Entry(form)
        number_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(form, text="Type:").grid(row=2, column=0, padx=5, pady=5)
        type_combo = ttk.Combobox(form, values=["serial", "batch"])
        type_combo.grid(row=2, column=1, padx=5, pady=5)
        ttk.Label(form, text="Expiry Date:").grid(row=3, column=0, padx=5, pady=5)
        expiry_entry = DateEntry(form)
        expiry_entry.grid(row=3, column=1, padx=5, pady=5)
        ttk.Label(form, text="Received Date:").grid(row=4, column=0, padx=5, pady=5)
        received_entry = DateEntry(form)
        received_entry.grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(form, text="Save", command=lambda: self.save_serial_batch(
            product_id_entry.get(), number_entry.get(), type_combo.get(), expiry_entry.get(), received_entry.get(), form)).grid(row=5, column=0, columnspan=2, pady=10)

    def save_serial_batch(self, product_id, number, type, expiry_date, received_date, form):
        try:
            product_id = int(product_id)
            self.db.add_serial_batch(product_id, number, type, expiry_date, received_date)
            messagebox.showinfo("Success", "Serial/Batch added")
            form.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid product ID")

    def adjust_inventory_form(self):
        form = tk.Toplevel(self.root)
        form.title("Adjust Inventory")
        ttk.Label(form, text="Inventory ID:").grid(row=0, column=0, padx=5, pady=5)
        inv_id_entry = ttk.Entry(form)
        inv_id_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(form, text="Action:").grid(row=1, column=0, padx=5, pady=5)
        action_entry = ttk.Entry(form)
        action_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(form, text="Reason:").grid(row=2, column=0, padx=5, pady=5)
        reason_entry = ttk.Entry(form)
        reason_entry.grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(form, text="Save", command=lambda: self.save_adjustment(
            inv_id_entry.get(), action_entry.get(), reason_entry.get(), form)).grid(row=3, column=0, columnspan=2, pady=10)

    def save_adjustment(self, inventory_id, action, reason, form):
        try:
            inventory_id = int(inventory_id)
            self.db.log_audit(inventory_id, action, reason, self.current_user)
            messagebox.showinfo("Success", "Adjustment logged")
            form.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid inventory ID")

    def set_reorder_rules_form(self):
        form = tk.Toplevel(self.root)
        form.title("Set Reorder Rules")
        ttk.Label(form, text="Product ID:").grid(row=0, column=0, padx=5, pady=5)
        product_id_entry = ttk.Entry(form)
        product_id_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(form, text="Min Threshold:").grid(row=1, column=0, padx=5, pady=5)
        min_entry = ttk.Entry(form)
        min_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(form, text="Reorder Point:").grid(row=2, column=0, padx=5, pady=5)
        reorder_entry = ttk.Entry(form)
        reorder_entry.grid(row=2, column=1, padx=5, pady=5)
        ttk.Label(form, text="Auto Order:").grid(row=3, column=0, padx=5, pady=5)
        auto_var = tk.BooleanVar()
        ttk.Checkbutton(form, variable=auto_var).grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(form, text="Save", command=lambda: self.save_reorder_rule(
            product_id_entry.get(), min_entry.get(), reorder_entry.get(), auto_var.get(), form)).grid(row=4, column=0, columnspan=2, pady=10)

    def save_reorder_rule(self, product_id, min_threshold, reorder_point, auto_order, form):
        try:
            product_id = int(product_id)
            min_threshold = int(min_threshold)
            reorder_point = int(reorder_point)
            self.db.set_reorder_rule(product_id, min_threshold, reorder_point, auto_order)
            messagebox.showinfo("Success", "Reorder rule set")
            form.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid input")

    def inventory_summary_report(self):
        report = tk.Toplevel(self.root)
        report.title("Inventory Summary")
        tree = ttk.Treeview(report, columns=("Product", "Quantity", "Status", "Warehouse", "Zone", "Aisle", "Bin"), show="headings")
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
        ttk.Button(report, text="Export to CSV", command=lambda: self.export_to_csv(summary, "inventory_summary.csv")).pack(pady=10)

    def expiry_alerts_report(self):
        report = tk.Toplevel(self.root)
        report.title("Expiry Alerts")
        tree = ttk.Treeview(report, columns=("Product ID", "Batch Number", "Days to Expiry"), show="headings")
        tree.heading("Product ID", text="Product ID")
        tree.heading("Batch Number", text="Batch Number")
        tree.heading("Days to Expiry", text="Days to Expiry")
        alerts = self.db.check_expiry_alerts()
        for alert in alerts:
            tree.insert("", "end", values=alert)
        tree.pack(fill="both", expand=True)
        ttk.Button(report, text="Export to CSV", command=lambda: self.export_to_csv(alerts, "expiry_alerts.csv")).pack(pady=10)

    def reorder_alerts_report(self):
        report = tk.Toplevel(self.root)
        report.title("Reorder Alerts")
        tree = ttk.Treeview(report, columns=("Product ID", "Quantity", "Min Threshold", "Reorder Point"), show="headings")
        tree.heading("Product ID", text="Product ID")
        tree.heading("Quantity", text="Quantity")
        tree.heading("Min Threshold", text="Min Threshold")
        tree.heading("Reorder Point", text="Reorder Point")
        alerts = self.db.check_reorder_alerts()
        for alert in alerts:
            tree.insert("", "end", values=alert)
        tree.pack(fill="both", expand=True)
        ttk.Button(report, text="Export to CSV", command=lambda: self.export_to_csv(alerts, "reorder_alerts.csv")).pack(pady=10)

    def audit_logs_report(self):
        report = tk.Toplevel(self.root)
        report.title("Audit Logs")
        tree = ttk.Treeview(report, columns=("Audit ID", "Inventory ID", "Action", "Reason", "Changed By", "Timestamp"), show="headings")
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
        ttk.Button(report, text="Export to CSV", command=lambda: self.export_to_csv(logs, "audit_logs.csv")).pack(pady=10)

    def export_to_csv(self, data, filename):
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([col[0] for col in self.db.cursor.description] if self.db.cursor.description else data[0])
            writer.writerows(data)
        messagebox.showinfo("Success", f"Exported to {filename}")

    def view_inventory(self):
        self.update_dashboard()

if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop()