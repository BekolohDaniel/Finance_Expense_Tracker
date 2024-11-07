from datetime import datetime
from flask import Flask, request, flash, url_for, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, Float, Enum, func, engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Relationship, Session, sessionmaker
from flask_login import LoginManager, login_user
from flask_bootstrap import Bootstrap5
from werkzeug.security import generate_password_hash, check_password_hash
import os


class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
# Create the engine
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], echo=True)

# Session configuration
SessionLocal = sessionmaker(bind=engine)
# initialize the app with the extension
db.init_app(app)
# bootstrap installation
bootstrap = Bootstrap5(app)

# session bing-engine
session = Session(bind=engine)

# Calculating the net income
@app.route('/net_income/<int:id>', methods=['GET'])
def calc_net_income(id):
  with SessionLocal() as session:
    user = session.get(User, id)
    if user:
      net_income = user.net_income(session)
      return jsonify({'NET INCOME': net_income})
    else:
      return jsonify({"error": "User not found"}), 404


# Creating the user model
class User(db.Model):
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

  def calc_income(self, session):
    total_income = session.query(func.sum(Transaction.amount)).filter(Transaction.user_id == self.id,
                                                                      Transaction.type=='income').scalar()
    return total_income if total_income is not None else 0.0

  def calc_expense(self, session):
    total_expenses = session.query(func.sum(Transaction.expenses)).filter(Transaction.user_id==self.id,
                                                                          Transaction.type=='expense').scalar()
    return total_expenses if total_expenses is not None else 0.0

  def net_income(self, session):
    return self.calc_income(session) - self.calc_expense(session)

# Creating the category model
class Category(db.Model):
  __tablename__ = 'category'
  id: Mapped[int] = mapped_column(primary_key=True)
  name: Mapped[str] = mapped_column(unique=True, nullable=False)
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

# Setting up secure user registration, login and session management
# setting up secure user registration
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return db.get_or_404(User, id)

# home
@app.route('/')
def index():
  return 'Index page'

# Setting up user registration
@app.route('/registration', methods=['POST'])
def registration():
  username = request.form.get('username')
  email = request.form.get('email')
  password = request.form.get('password')
  hashed_password = generate_password_hash(password, method='scrypt', salt_length=16)

  new_user = User(username=username, email=email, password=hashed_password)
  try:
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Registration successful"})
  except Exception as e:
    db.session.rollback()
    return jsonify({"error": str(e)}), 400


# Login the user
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
        return jsonify({"message": "Login successful"})
    return jsonify({"error": "Invalid credentials"}), 401



if __name__ == '__main__':
  app.run(debug=True)
