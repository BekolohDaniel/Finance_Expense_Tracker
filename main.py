from datetime import datetime, timezone
from flask import Flask, request, flash, url_for, redirect, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, Float, Enum, func, engine, create_engine, extract
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Relationship, Session, sessionmaker
from flask_login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user
from flask_bootstrap import Bootstrap5
from werkzeug.security import generate_password_hash, check_password_hash
import os
import form


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')

# initialize the app with the extension
db.init_app(app)
# bootstrap installation
bootstrap = Bootstrap5(app)

# Setting up secure user registration, login and session management
# setting up secure user registration
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


# Creating the user model
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=True)
    email: Mapped[str] = mapped_column(nullable=True, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    transactions = Relationship('Transaction', back_populates='user')


# Creating the transactions model
class Transaction(db.Model):
    __tablename__ = 'transactions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), nullable=False)
    amount: Mapped[float] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(Enum("income", "expense", name="transaction_type"), nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    user = Relationship('User', back_populates='transactions')
    category_id: Mapped[int] = mapped_column(ForeignKey('category.id'), nullable=False)
    category = Relationship('Category', back_populates='transactions')
    expenses = Relationship('Expense', back_populates='transaction')
    date: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc))

    # calculate total income
    def calc_income(self):
        return db.session.query(func.sum(Transaction.amount)).filter_by(
            user_id=self.id, type='income'
        ).scalar() or 0.0

    # Calculate total expenses
    def calc_expense(self):
        return db.session.query(func.sum(Transaction.amount)).filter_by(
            user_id=self.id, type='expense'
        ).scalar() or 0.0

    def net_income(self):
        total_income = self.calc_income()
        total_expense = self.calc_expense()
        return total_income - total_expense


class Category(db.Model):
    __tablename__ = 'category'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=True)
    transactions = Relationship('Transaction', back_populates='category')


# Creating the expense model
class Expense(db.Model):
    __tablename__ = 'expenses'
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey('transactions.id'), nullable=False)
    transaction = Relationship('Transaction', back_populates='expenses')
    note: Mapped[str] = mapped_column()


# Create all tables
with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# home
@app.route('/')
def index():
    return render_template('index.html', current_user=current_user)


# Setting up user registration
@app.route('/registration', methods=['POST', 'GET'])
def registration():
    forms = form.RegistrationForm()
    if forms.validate_on_submit():
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='scrypt', salt_length=16)

        new_user = User(username=username,
                        email=email,
                        password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return render_template('login.html', message="Registration successful")
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Registration unsuccessful"})
    return render_template('register.html', form=forms, current_user=current_user)


# Login the user
@app.route('/login', methods=['POST', 'GET'])
def login():
    forms = form.LoginForm()
    if forms.validate_on_submit():
        result = db.session.execute(db.select(User).where(User.email == forms.email.data))
        password = request.form.get('password')
        user = result.scalar()
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return render_template('transaction.html')
    return render_template('login.html', form=forms, current_user=current_user)


# Calculating the net income
@app.route('/net_income', methods=['GET', 'POST'])
@login_required
def calc_net_income():
    user = current_user
    if user:
        transactions = Transaction.query.filter_by(user_id=user.id).all()
        net_income = sum(transaction.net_income() for transaction in transactions)
        return render_template('savings.html', current_user=current_user, total=net_income)
    else:
        return jsonify({'error': 'User not found'}), 404


# Filter Transactions by category
@app.route('/by_category/<int:category_id>', methods=['GET'])
@login_required
def filter_category(category_id):
    category = Category.query.filter_by(name='Food').first()
    user = current_user
    if user:
        transactions = db.session.execute(
            db.select(Transaction).filter(Transaction.user_id == user,
                                          Transaction.type == 'expense',
                                          Transaction.category_id == category_id)).scalars().all()
        # Check if transactions exist for the given category
        if not transactions:
            return jsonify({'message': 'No transactions found for this category.'}), 404

        transactions_data = [
            {
                'id': transaction.id,
                'amount': transaction.amount,
                'type': transaction.type,
                'description': transaction.description,
                'category_id': category.id,
                'date': transaction.date
            } for transaction in transactions
        ]
        return jsonify({'Success': transactions_data})
    return render_template('transaction.html', current_user=current_user)


# # Expenses for the month
@app.route('/expenses/<int:month>/<int:year>', methods=['POST', 'GET'])
@login_required
def monthly_expenses(month, year):
    user = current_user  # Access logged-in user directly
    if user:
        total_expenses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user.id,
            extract('month', Transaction.date) == month,
            extract('year', Transaction.date) == year,
            Transaction.type == 'expense'
        ).scalar()
        return render_template('savings.html', current_user=current_user, total_expenses=total_expenses)
    else:
        return jsonify({'Failed': 'User not found'}, 404)


# logout user
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# adding new income
@app.route('/deposit', methods=['GET', 'POST'])
@login_required
def add_income():
    forms = form.DepositForm()
    if forms.validate_on_submit():
        amount = forms.amount.data  # Use the form's data attribute for amount
        description = forms.description.data  # Use the form's data attribute for description
        category_name = forms.category.data  # The selected category from the form

        # Fetch the category object by name
        category = Category.query.filter_by(name=category_name).first()
        if category:
            # If the category exists, get the category id
            cat_id = category.id
            new_transaction = Transaction(
            user_id=current_user.id,
            amount=amount,
            type='income',
            description=description,
            category_id=cat_id,
            date=datetime.now()
        )
            db.session.add(new_transaction)
            db.session.commit()
            return jsonify({'Success': "Amount successfully added", "new_income": amount}), 404
        return jsonify({'error': 'Cannot perform transaction'})
    return render_template('deposit.html', form=forms, current_user=current_user)


# Adding new Category
@app.route('/add_category')
def new_category():
    default_categories = ["General", "Food", "Transport", "Rent", "Entertainment"]
    for category_name in default_categories:
        existing_category = Category.query.filter_by(name=category_name).first()
        if not existing_category:
            new_category = Category(name=category_name)
            db.session.add(new_category)
    db.session.commit()
    return render_template('transaction.html')

if __name__ == '__main__':
    app.run(debug=True)
