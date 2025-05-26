# IMS-Tkinter

# Inventory Management System Setup Guide

This guide will walk you through setting up and running the Inventory Management System on your local PC. The application is a Python-based desktop app with a MySQL backend, using `tkinter` and `ttkbootstrap` for the GUI. It allows you to manage products, warehouses, inventory, and more.

## Prerequisites

Before starting, ensure you have the following installed on your system:

### 1. Python
- **Version**: Python 3.8 or higher (3.10 recommended).
- **Download**: Get it from [python.org](https://www.python.org/downloads/).
- **Installation**:
  - Windows: Download the installer, run it, and ensure you check "Add Python to PATH" during installation.
  - macOS/Linux: Python is often pre-installed. Verify by running `python3 --version` in the terminal. If not installed, use a package manager like `brew` (macOS) or `apt` (Linux), e.g., `brew install python3` or `sudo apt install python3`.

### 2. MySQL
- **Version**: MySQL 5.7 or higher (8.0 recommended).
- **Download**: Get MySQL Community Server from [mysql.com](https://dev.mysql.com/downloads/mysql/).
- **Installation**:
  - **Windows**:
    - Download the MySQL Installer and select "MySQL Server" and "MySQL Workbench".
    - During setup, set a root password (or leave it blank for simplicity, but note it for later).
    - Start the MySQL server after installation (it should start automatically).
  - **macOS**:
    - Install via Homebrew: `brew install mysql`.
    - Start the server: `brew services start mysql`.
    - Set a root password (optional): `mysqladmin -u root password 'yourpassword'`.
  - **Linux**:
    - Install via package manager, e.g., `sudo apt install mysql-server` (Ubuntu).
    - Start the server: `sudo service mysql start`.
    - Set a root password (optional): `sudo mysql_secure_installation`.
- **Verify**: Run `mysql --version` in your terminal to confirm MySQL is installed.

### 3. MySQL Workbench (Optional but Recommended)
- **Purpose**: A GUI tool to manage your MySQL database.
- **Download**: Available with MySQL Installer (Windows) or separately from [mysql.com](https://dev.mysql.com/downloads/workbench/).
- **Installation**: Follow the installer instructions. Use it to verify database setup later.

### 4. Git (Optional)
- If you're cloning the project from a repository, install Git:
  - Download from [git-scm.com](https://git-scm.com/downloads).
  - Install and verify with `git --version`.

## Step 1: Set Up the Project Files

1. **Download or Clone the Project**:
   - If the project is in a Git repository, clone it:
     ```bash
     git clone <repository-url>
     cd <repository-directory>
     ```
   - Alternatively, download the project files as a ZIP and extract them to a folder (e.g., `inventory_system`).

2. **Verify Project Files**:
   Ensure you have the following files in your project directory:
   - `inventory_management_system.py`: The main application code.
   - `mysql_setup.sql`: The SQL script to set up the database schema.

## Step 2: Install Python Dependencies

1. **Set Up a Virtual Environment (Recommended)**:
   - Open a terminal in your project directory.
   - Create a virtual environment:
     ```bash
     python3 -m venv venv
     ```
   - Activate the virtual environment:
     - Windows: `venv\Scripts\activate`
     - macOS/Linux: `source venv/bin/activate`

2. **Install Required Python Packages**:
   - With the virtual environment activated, install the dependencies:
     ```bash
     pip install mysql-connector-python ttkbootstrap
     ```
   - **Packages**:
     - `mysql-connector-python`: For connecting Python to MySQL.
     - `ttkbootstrap`: For the enhanced GUI styling of `tkinter`.

## Step 3: Set Up the MySQL Database

1. **Start the MySQL Server**:
   - Ensure your MySQL server is running:
     - Windows: Check the Services app or restart via MySQL Installer.
     - macOS: `brew services start mysql`.
     - Linux: `sudo service mysql start`.
   - Verify by running `mysql -u root -p` and entering your root password (press Enter if no password).

2. **Create the Database and Tables**:
   - Open MySQL Workbench (or use the MySQL command line).
   - Run the `mysql_setup.sql` script to set up the database:
     - In MySQL Workbench:
       1. Open a new SQL tab (File > New Query Tab).
       2. Copy-paste the contents of `mysql_setup.sql`.
       3. Execute the script (click the lightning bolt icon or press `Ctrl+Shift+Enter`).
     - Command line:
       ```bash
       mysql -u root -p < mysql_setup.sql
       ```
       Enter your root password when prompted.
   - **Verify**:
     - Connect to the database: `mysql -u root -p`
     - Check the database: `USE inventory_db; SHOW TABLES;`
     - Expected tables: `products`, `warehouses`, `locations`, `inventory`, `serial_batches`, `stock_movements`, `reorder_rules`, `audit_logs`, `users`.

3. **Check the Default User**:
   - The script adds a default admin user:
     ```sql
     SELECT * FROM users;
     ```
   - Expected output:
     ```
     +---------+----------+----------+-------+
     | user_id | username | password | role  |
     +---------+----------+----------+-------+
     |       1 | admin    | admin123 | Admin |
     +---------+----------+----------+-------+
     ```

4. **Update MySQL Connection Details (if needed)**:
   - Open `inventory_management_system.py`.
   - In the `InventoryApp` class, the `DatabaseManager` is initialized as:
     ```python
     self.db = DatabaseManager(host="127.0.0.1", user="root", password="", database="inventory_db")
     ```
   - **Adjust Parameters**:
     - `host`: Usually `127.0.0.1` (localhost). Change if your MySQL server is on a different host.
     - `user`: Default is `root`. Change if using a different MySQL user.
     - `password`: Default is `""` (empty). Update to your MySQL root password if set.
     - `database`: Should be `inventory_db` (matches the script).
   - Example with a password:
     ```python
     self.db = DatabaseManager(host="127.0.0.1", user="root", password="yourpassword", database="inventory_db")
     ```

## Step 4: Run the Application

1. **Activate the Virtual Environment** (if not already activated):
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

2. **Run the Application**:
   - In the terminal, navigate to the project directory and run:
     ```bash
     python inventory_management_system.py
     ```
   - A GUI window titled "Inventory Management System" should appear with a login screen.

3. **Log In**:
   - Use the default admin credentials:
     - Username: `admin`
     - Password: `admin123`
   - Click "Login". You should see the main interface with tabs like "Dashboard", "Add Product", etc.

## Step 5: Test the Application

1. **Add a Warehouse**:
   - Go to the "Add Warehouse" tab.
   - Enter a name (e.g., "Main Warehouse") and location (e.g., "New York").
   - Click "Save". You should see a "Success: Warehouse added" message.

2. **Add a Location**:
   - Go to the "Add Location" tab.
   - Select the warehouse you added (e.g., "Main Warehouse (New York)").
   - Enter Zone (e.g., "Zone A"), Aisle (e.g., "A1"), Bin (e.g., "B1").
   - Click "Save".

3. **Add a Product**:
   - Go to the "Add Product" tab.
   - Enter details (e.g., Name: "Laptop", Description: "Gaming Laptop", Category: "Electronics", Quantity: 100, Status: "available").
   - Select the location (e.g., "Main Warehouse (Zone: Zone A, Aisle: A1, Bin: B1)").
   - Click "Save".

4. **Check the Dashboard**:
   - Go to the "Dashboard" tab.
   - Verify that your product appears in the inventory table with the correct details.

## Troubleshooting

### 1. MySQL Connection Errors
- **Error**: "Can't connect to MySQL server on '127.0.0.1'".
  - **Fix**: Ensure the MySQL server is running (see Step 3.1). Check the host in `DatabaseManager` (e.g., `127.0.0.1`).
- **Error**: "Access denied for user 'root'@'localhost'".
  - **Fix**: Update the password in `DatabaseManager` to match your MySQL root password. Alternatively, reset the root password:
    ```bash
    mysqladmin -u root password 'newpassword'
    ```

### 2. Table Not Found or Column Errors
- **Error**: "Table 'inventory_db.warehouses' doesn't exist" or "Unknown column 'name'".
  - **Fix**: Ensure the `mysql_setup.sql` script was executed successfully (Step 3.2). Verify with:
    ```sql
    USE inventory_db;
    SHOW TABLES;
    DESCRIBE warehouses;
    ```
  - If tables are missing, rerun the script or manually create the tables.

### 3. Missing Python Modules
- **Error**: "ModuleNotFoundError: No module named 'mysql.connector'".
  - **Fix**: Ensure you're in the virtual environment and reinstall the dependencies:
    ```bash
    pip install mysql-connector-python ttkbootstrap
    ```

### 4. Application Crashes or Doesn't Start
- **Check Logs**: The application logs messages to the console (e.g., "Database connection established"). Look for errors like:
  ```
  2025-05-26 <time> - ERROR - Database connection failed: <error>
  ```
- **Fix**: Address the specific error (e.g., connection issues, missing dependencies).

## Additional Notes

- **Database Backup**: Before making changes, back up your database:
  ```bash
  mysqldump -u root -p inventory_db > inventory_db_backup.sql
  ```
- **Resetting the Database**: If you encounter persistent issues, reset the database:
  ```sql
  DROP DATABASE inventory_db;
  CREATE DATABASE inventory_db;
  ```
  Then rerun `mysql_setup.sql`.
- **Customizing the Application**:
  - Add more users by inserting into the `users` table:
    ```sql
    INSERT INTO users (username, password, role) VALUES ('newuser', 'newpass123', 'Warehouse Manager');
    ```
  - Modify `inventory_management_system.py` to add features or change the UI.