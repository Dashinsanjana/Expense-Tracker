from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# MongoDB Configuration
app.config['MONGO_URI'] = 'mongodb://localhost:27017/Expense-tracker'
mongo = PyMongo(app)
bcrypt = Bcrypt(app)

# Routes
@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    users_collection = mongo.db.users

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            flash("Passwords do not match. Please try again.", "error")
            return redirect(url_for('signup'))

        # Check if the username already exists
        existing_user = users_collection.find_one({'username': username})
        if existing_user:
            flash("Username already exists. Try logging in.", "error")
            return redirect(url_for('signup'))

        # Hash the password and save to the database
        hashed_pw = generate_password_hash(password)
        users_collection.insert_one({'username': username, 'password': hashed_pw})

        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/set_income', methods=['POST'])
def set_income():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = mongo.db.users.find_one({'username': session['user']})
    income = float(request.form['income'])
    income_doc = mongo.db.income.find_one({'user_id': str(user['_id'])})

    if income_doc:
        mongo.db.income.update_one({'user_id': str(user['_id'])}, {'$set': {'amount': income}})
    else:
        mongo.db.income.insert_one({'user_id': str(user['_id']), 'amount': income})

    flash("Income updated successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = mongo.db.users.find_one({'username': username})
        if user and check_password_hash(user.get('password'), password):
            session['user'] = username
            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = mongo.db.users.find_one({'username': session['user']})
    expenses = list(mongo.db.expenses.find({'user_id': str(user['_id'])}))
    income_doc = mongo.db.income.find_one({'user_id': str(user['_id'])})
    income = income_doc['amount'] if income_doc else 0.0

    total_expenses = sum(exp['amount'] for exp in expenses)

    # Percentages
    monthly_percentage = (total_expenses / income) * 100 if income else 0
    weekly_percentage = monthly_percentage / 4
    annual_percentage = (total_expenses / (income * 12)) * 100 if income else 0

    # Progress bar % capped at 100 for UI
    progress_percentage = (total_expenses / income) * 100 if income else 0

    # Spending quality
    if income == 0:
        spending_quality = "⚠️ No income entered."
    elif total_expenses < income * 0.5:
        spending_quality = "🟢 Excellent spending habits!"
    elif total_expenses <= income:
        spending_quality = "🟡 Moderate spending. Keep tracking!"
    else:
        spending_quality = "🔴 Overspending! Try to cut back."

    warning = None
    if total_expenses > income:
        warning = f"You have exceeded your income by LKR {total_expenses - income:.2f}!"

    return render_template('dashboard.html',
                           username=session['user'],
                           expenses=expenses,
                           income=income,
                           total_expenses=total_expenses,
                           progress_percentage=progress_percentage,
                           monthly_percentage=monthly_percentage,
                           weekly_percentage=weekly_percentage,
                           annual_percentage=annual_percentage,
                           spending_quality=spending_quality,
                           warning=warning)

@app.route('/delete/<expense_id>')
def delete_expense(expense_id):
    mongo.db.expenses.delete_one({'_id': ObjectId(expense_id)})
    flash('Expense deleted.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user' not in session:
        return redirect(url_for('login'))

    description = request.form['description']
    amount = float(request.form['amount'])
    category = request.form['category']
    date = datetime.strptime(request.form['date'], '%Y-%m-%d')
    user = mongo.db.users.find_one({'username': session['user']})

    expense = {
        'description': description,
        'amount': amount,
        'category': category,
        'date': date,
        'user_id': str(user['_id'])
    }

    mongo.db.expenses.insert_one(expense)
    flash('Expense added successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/edit/<expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = mongo.db.expenses.find_one({'_id': ObjectId(expense_id)})

    if request.method == 'POST':
        updated_expense = {
            '_id': ObjectId(expense_id),
            'amount': float(request.form['amount']),
            'category': request.form['category'],
            'description': request.form['description'],
            'date': datetime.strptime(request.form['date'], '%Y-%m-%d')
        }
        mongo.db.expenses.update_one({'_id': ObjectId(expense_id)}, {'$set': updated_expense})
        flash('Expense updated.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_expense.html', expense=expense)

if __name__ == '__main__':
    app.run(debug=True)
