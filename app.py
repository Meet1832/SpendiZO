import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import requests
from oauthlib.oauth2 import WebApplicationClient
from config import Config

# Load environment variables
load_dotenv()

# Create the Flask application
app = Flask(__name__)
app.config.from_object(Config)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
app.config['SESSION_PERMANENT'] = True

# OAuth 2 client setup
client = WebApplicationClient(Config.GOOGLE_CLIENT_ID)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['password'])

# Database connection function
def get_db_connection():
    database_url = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    
    # Handle PostgreSQL connection strings (for Heroku)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    if database_url.startswith('sqlite:///'):
        # SQLite connection
        db_path = database_url.replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    else:
        # For PostgreSQL or other database types
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.pool import NullPool
            engine = create_engine(database_url, poolclass=NullPool)
            conn = engine.connect()
            return conn
        except ImportError:
            # Fallback to SQLite if SQLAlchemy is not available
            app.logger.warning("SQLAlchemy not available, falling back to SQLite")
            conn = sqlite3.connect('database.db')
            conn.row_factory = sqlite3.Row
            return conn

# Initialize database
def init_db():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    
    # Drop existing tables if they exist
    cursor.execute('DROP TABLE IF EXISTS expenses')
    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('DROP TABLE IF EXISTS budgets')
    
    # Create users table with Google OAuth support
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT,
        email TEXT UNIQUE,
        google_id TEXT UNIQUE
    )
    ''')
    
    # Create expenses table with user_id and receipt support
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT,
        category TEXT,
        amount REAL,
        description TEXT,
        receipt_path TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create budgets table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        period TEXT NOT NULL,
        start_date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    connection.commit()
    connection.close()
    print("Database setup complete!")

# Route: Home Page (View Expenses)
@app.route('/')
@login_required
def index():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Fetch user's expenses from the database
        cursor.execute("SELECT date, category, amount, description, id FROM expenses WHERE user_id = ? ORDER BY date DESC", (current_user.id,))
        expenses = cursor.fetchall()

        # Calculate summary statistics
        total_amount = 0
        monthly_amount = 0
        categories = set()
        category_amounts = {}
        monthly_data = {}
        current_month = datetime.now().strftime('%Y-%m')

        if expenses:
            for expense in expenses:
                date = expense[0]
                category = expense[1]
                amount = expense[2]

                # Total amount
                total_amount += amount

                # Monthly amount
                if date.startswith(current_month):
                    monthly_amount += amount

                # Category distribution
                categories.add(category)
                category_amounts[category] = category_amounts.get(category, 0) + amount

                # Monthly trends
                month = date[:7]  # Get YYYY-MM
                monthly_data[month] = monthly_data.get(month, 0) + amount

        # Prepare data for charts
        categories_list = list(categories)
        category_amounts_list = [category_amounts.get(cat, 0) for cat in categories_list]

        # Sort monthly data by date
        sorted_months = sorted(monthly_data.keys())
        monthly_amounts_list = [monthly_data[month] for month in sorted_months]



    finally:
        cursor.close()
        connection.close()

    # Pass all necessary data to the template
    return render_template('index.html',
                         expenses=expenses,
                         total_amount=total_amount,
                         monthly_amount=monthly_amount,
                         categories_count=len(categories),
                         categories=categories_list,
                         category_amounts=category_amounts_list,
                         monthly_labels=sorted_months,
                         monthly_amounts=monthly_amounts_list)

# Route: Add Expense Page
@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        try:
            date = request.form['date']
            category = request.form['category']
            amount = float(request.form['amount'])
            description = request.form['description']
            receipt = request.files.get('receipt')

            if not all([date, category, amount]):
                flash('Date, category and amount are required')
                return redirect(url_for('add_expense'))

            receipt_path = None
            if receipt and receipt.filename:
                try:
                    # Import cloud storage module
                    from cloud_storage import save_file
                    
                    # Generate secure filename
                    filename = secure_filename(f'{current_user.id}_{datetime.now().strftime("%Y%m%d%H%M%S")}_{receipt.filename}')
                    
                    # Save file using cloud storage module
                    receipt_path = save_file(receipt, filename, 'receipts')
                except ImportError:
                    # Fallback to local storage if cloud_storage module is not available
                    app.logger.warning("cloud_storage module not available, using local storage")
                    filename = secure_filename(f'{current_user.id}_{datetime.now().strftime("%Y%m%d%H%M%S")}_{receipt.filename}')
                    receipt_path = os.path.join('static', 'receipts', filename)
                    os.makedirs(os.path.dirname(receipt_path), exist_ok=True)
                    receipt.save(receipt_path)

            conn = get_db_connection()
            conn.execute("INSERT INTO expenses (user_id, date, category, amount, description, receipt_path) VALUES (?, ?, ?, ?, ?, ?)",
                        (current_user.id, date, category, amount, description, receipt_path))
            conn.commit()
            conn.close()
            flash('Expense added successfully')
            return redirect('/')
        except ValueError:
            flash('Invalid amount value')
            return redirect(url_for('add_expense'))
        except Exception as e:
            app.logger.error(f'Error adding expense: {e}')
            flash('An error occurred while adding the expense')
            return redirect(url_for('add_expense'))
    
    return render_template('add_expense.html')



# Google OAuth routes
@app.route('/google_login')
def google_login():
    # Find out what URL to hit for Google login
    google_provider_cfg = requests.get(Config.GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route('/google_login/callback')
def google_callback():
    # Get authorization code Google sent back
    code = request.args.get("code")

    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = requests.get(Config.GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send request to get tokens
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(Config.GOOGLE_CLIENT_ID, Config.GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens
    client.parse_request_body_response(token_response.text)

    # Get user info from Google
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        google_id = userinfo_response.json()["sub"]
        email = userinfo_response.json()["email"]
        name = userinfo_response.json()["given_name"]

        # Check if user exists
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE google_id = ?', (google_id,)).fetchone()

        if not user:
            # Create new user
            conn.execute(
                'INSERT INTO users (username, email, google_id) VALUES (?, ?, ?)',
                (name, email, google_id)
            )
            conn.commit()
            user = conn.execute('SELECT * FROM users WHERE google_id = ?', (google_id,)).fetchone()

        conn.close()
        user_obj = User(user['id'], user['username'], user.get('password', ''))
        login_user(user_obj)
        return redirect(url_for('index'))
    else:
        flash("Google authentication failed")
        return redirect(url_for('login'))

# Initialize the database when the application starts
init_db()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        if conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            flash('Username already exists')
            return redirect(url_for('register'))
            
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                    (username, generate_password_hash(password)))
        conn.commit()
        conn.close()
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['password'])
            login_user(user_obj, remember=remember)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/delete_expense', methods=['POST'])
@login_required
def delete_expense():
    expense_id = request.form.get('expense_id')
    if expense_id:
        conn = get_db_connection()
        # Verify the expense belongs to the current user before deleting
        conn.execute('DELETE FROM expenses WHERE id = ? AND user_id = ?', (expense_id, current_user.id))
        conn.commit()
        conn.close()
        flash('Expense deleted successfully')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/budget', methods=['GET'])
@login_required
def budget():
    conn = get_db_connection()
    
    # Get user's budgets
    budgets = conn.execute(
        'SELECT id, category, amount, period, start_date FROM budgets WHERE user_id = ?',
        (current_user.id,)
    ).fetchall()
    
    # Calculate spent and remaining amounts for each budget
    budgets_with_spending = []
    for budget in budgets:
        budget_id, category, amount, period, start_date = budget
        
        # Calculate date range based on period
        start = datetime.strptime(start_date, '%Y-%m-%d')
        today = datetime.now()
        
        if period == 'monthly':
            # For monthly budgets, get expenses from the start date to 30 days later
            end = start + timedelta(days=30)
            if today < end:
                end = today
        elif period == 'quarterly':
            # For quarterly budgets, get expenses from the start date to 90 days later
            end = start + timedelta(days=90)
            if today < end:
                end = today
        elif period == 'yearly':
            # For yearly budgets, get expenses from the start date to 365 days later
            end = start + timedelta(days=365)
            if today < end:
                end = today
        
        # Format dates for SQL query
        start_str = start.strftime('%Y-%m-%d')
        end_str = end.strftime('%Y-%m-%d')
        
        # Get total spending for this category in the date range
        spent_result = conn.execute(
            'SELECT SUM(amount) FROM expenses WHERE user_id = ? AND category = ? AND date BETWEEN ? AND ?',
            (current_user.id, category, start_str, end_str)
        ).fetchone()
        
        spent = spent_result[0] if spent_result[0] else 0
        remaining = amount - spent
        
        # Add to the list with spent and remaining values
        budgets_with_spending.append({
            'id': budget_id,
            'category': category,
            'amount': amount,
            'period': period,
            'start_date': start_date,
            'spent': spent,
            'remaining': remaining
        })
    
    conn.close()
    return render_template('budget.html', budgets=budgets_with_spending)

@app.route('/add_budget', methods=['POST'])
@login_required
def add_budget():
    if request.method == 'POST':
        category = request.form['category']
        amount = float(request.form['amount'])
        period = request.form['period']
        start_date = request.form['start_date']
        
        if not all([category, amount, period, start_date]):
            flash('All fields are required')
            return redirect(url_for('budget'))
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO budgets (user_id, category, amount, period, start_date) VALUES (?, ?, ?, ?, ?)',
            (current_user.id, category, amount, period, start_date)
        )
        conn.commit()
        conn.close()
        
        flash('Budget added successfully')
        return redirect(url_for('budget'))

@app.route('/delete_budget', methods=['POST'])
@login_required
def delete_budget():
    budget_id = request.form.get('budget_id')
    if budget_id:
        conn = get_db_connection()
        # Verify the budget belongs to the current user before deleting
        conn.execute('DELETE FROM budgets WHERE id = ? AND user_id = ?', (budget_id, current_user.id))
        conn.commit()
        conn.close()
        flash('Budget deleted successfully')
    return redirect(url_for('budget'))

@app.route('/download_report', methods=['GET'])
@login_required
def download_report():
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    
    # Get start and end date for the selected month
    start_date = f"{month}-01"
    # Calculate the end date (last day of the month)
    year, month_num = map(int, month.split('-'))
    if month_num == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month_num + 1
        next_year = year
    end_date = f"{next_year}-{next_month:02d}-01"
    
    # Get expenses for the selected month
    conn = get_db_connection()
    expenses = conn.execute(
        'SELECT date, category, amount, description FROM expenses WHERE user_id = ? AND date >= ? AND date < ? ORDER BY date',
        (current_user.id, start_date, end_date)
    ).fetchall()
    
    # Calculate total by category
    category_totals = {}
    total_amount = 0
    for expense in expenses:
        category = expense[1]
        amount = expense[2]
        category_totals[category] = category_totals.get(category, 0) + amount
        total_amount += amount
    
    # Get budgets for comparison
    budgets = conn.execute(
        'SELECT category, amount FROM budgets WHERE user_id = ? AND period = "monthly"',
        (current_user.id,)
    ).fetchall()
    budget_dict = {budget[0]: budget[1] for budget in budgets}
    
    conn.close()
    
    # Create CSV content
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Monthly Expense Report', month])
    writer.writerow([])
    writer.writerow(['Date', 'Category', 'Amount', 'Description'])
    
    # Write expense data
    for expense in expenses:
        writer.writerow([expense[0], expense[1], f"Rs. {expense[2]:.2f}", expense[3]])
    
    # Write summary
    writer.writerow([])
    writer.writerow(['Category Summary'])
    writer.writerow(['Category', 'Spent', 'Budget', 'Remaining'])
    
    for category, spent in category_totals.items():
        budget = budget_dict.get(category, 0)
        remaining = budget - spent if budget > 0 else 0
        writer.writerow([category, f"Rs. {spent:.2f}", f"Rs. {budget:.2f}", f"Rs. {remaining:.2f}"])
    
    writer.writerow([])
    writer.writerow(['Total Expenses', f"Rs. {total_amount:.2f}"])
    
    # Prepare response
    output.seek(0)
    month_name = datetime.strptime(month, '%Y-%m').strftime('%B_%Y')
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=expense_report_{month_name}.csv"}
    )

if __name__ == '__main__':
    @app.route("/")
    def home():
        return "Hello from Flask on Vercel!"

    app.run(host="0.0.0.0", port=8080)
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # In production, debug should be False
    debug = os.environ.get('FLASK_ENV', 'production') != 'production'
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=debug)
