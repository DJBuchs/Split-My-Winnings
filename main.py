from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request, session
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey, JSON, DateTime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from typing import List
import os
from dotenv import load_dotenv
import smtplib
import bleach
import secrets
from forms import RegisterForm, LoginForm
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_KEY")
Bootstrap5(app)


login_manager = LoginManager()
login_manager.init_app(app)


app.config['SEND_EMAIL'] = os.getenv("SEND_EMAIL")
app.config['EMAIL_PASS'] = os.getenv("EMAIL_PASS")
app.config['EMAIL_RECEIVE'] = os.getenv("SEND_EMAIL")
app.config['SESSION_COOKIE_SECURE'] = True


class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/danibuchsbaum/Split_My_Winnings/instance/poker_database.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class User(db.Model, UserMixin):
    __tablename__ = "blog_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))

    def get(user_id):
        return User.query.get(user_id)
    

class GameData(db.Model):
    __tablename__ = "game_data"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_data: Mapped[dict] = mapped_column(JSON)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # relationship mapping for cash game
    cash_game_id: Mapped[int] = mapped_column(ForeignKey("poker_game.id"))
    cash_game: Mapped["CashGame"] = relationship("CashGame", back_populates="session_data")

    def __init__(self, game_data, cash_game):
        self.game_data = game_data
        self.cash_game = cash_game


class CashGame(db.Model):
    __tablename__ = "poker_game"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cash_name: Mapped[str] = mapped_column(String(100))
    player_list: Mapped[list] = mapped_column(JSON, default=[])
    # relationship mapping for game sessions
    session_data: Mapped[List["GameData"]] = relationship("GameData", back_populates="cash_game")

    
# with app.app_context():
#     db.create_all()


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/', methods=['POST', 'GET'])
def home():
    form = RegisterForm()
    return render_template("index.html", form=form)


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# LOGIN PAGE
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        elif user is None:
            flash("That email doesn't exist.")
            return redirect(url_for('login'))
        elif check_password_hash(user.password, form.password.data) is False:
            flash("Incorrect password, try again.")
            return redirect(url_for('login'))
    return render_template('login.html', form=form)


# THANK YOU PAGE
@app.route('/thank-you')
def thank_you():
    return render_template("thank_you.html")


# WELCOME PAGE
@app.route('/registration_success')
def register_success():
    return render_template("register_success.html")


# REGISTER INTEREST
@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email_exists = db.session.execute(db.select(User).where(User.email == form.email.data)).scalars().first()
        if email_exists:
            flash('That email address is already in use.')
            return redirect(url_for('register'))
        else:
            hashed_pass = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
            new_user = User(
                email=form.email.data,
                password=hashed_pass,
                name=form.name.data,
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('register_success'))
    return render_template("register.html", form=form)


# DASHBOARD
@app.route('/dashboard', methods=['POST', 'GET'])
@login_required
def dashboard():
    # 3 most recent games
    games = get_recent_games()
    game_data = [game.game_data for game in games]
    formatted_dates = [game.date.strftime("%A %d{} %B").format(get_ordinal_suffix(game.date.day)) for game in games]
    buyins = [sum(data['buyin'] for data in game) for game in game_data]
    owner_data = [next((data['cashout'] - data['buyin'] for data in game if data['name'] == current_user.name), None) for game in game_data]
    game_names = [game.cash_game for game in games]

    return render_template("dashboard.html", game_data=game_data, buyins=buyins, date=formatted_dates,
                           owner_data=owner_data, game_name = game_names)


# CONTACT US
@app.route('/contact-us', methods=['POST', 'GET'])
def contact_form():
    if request.method == 'POST':
        form_data = request.form
        email_entered = form_data['email']
        name_entered = form_data['name']
        message = form_data['message']
        try:
            with smtplib.SMTP("smtp.gmail.com") as connection:
                connection.starttls()
                connection.login(user=app.config['SEND_EMAIL'], password=app.config['EMAIL_PASS'])
                connection.sendmail(
                    from_addr=app.config['SEND_EMAIL'], 
                    to_addrs=app.config['EMAIL_RECEIVE'],
                    msg=f"Subject: New Contact Form Message\n\n{name_entered} has sent a message!\nEmail: {email_entered}\n"
                            f"Message: {message}"
                    )
        except Exception as e:
            return f"An error occurred: {e}", 500

    return render_template("contact_form.html")


# CONTACT FOOTER
@app.route('/feature-request', methods=['POST', 'GET'])
def contact_footer():
    if request.method == 'POST':
        form_data = request.form
        message = form_data['message']
        try:
            with smtplib.SMTP("smtp.gmail.com") as connection:
                connection.starttls()
                connection.login(user=app.config['SEND_EMAIL'], password=app.config['EMAIL_PASS'])
                connection.sendmail(
                    from_addr=app.config['SEND_EMAIL'], 
                    to_addrs=app.config['EMAIL_RECEIVE'], 
                    msg=f"Subject: New Poker Message\n\nYou were sent the following message:\n{message}"
                )
        except Exception as e:
            return f"An error occurred: {e}", 500
            
        return redirect(request.referrer)


# PAID VERSION - NUMBER OF PLAYERS + GAME
@app.route('/player-count', methods=['POST', 'GET'])
def player_count():
    result = db.session.execute(db.select(CashGame).order_by(CashGame.id))
    all_games = result.scalars().all()
    cash_list = [game.cash_name for game in all_games]

    if request.method == 'POST':
        data = request.form
        number_of_players = data["number"]
        if number_of_players:
            session['num_players'] = int(number_of_players)
            session['session_game'] = data['selected_game']
            return redirect(url_for('paid_details', players=number_of_players))
        
    return render_template("paid_count.html", cash_game=cash_list)


# PAID VERSION - INPUTS FOR CASH GAME
@app.route('/player-details', methods=['POST', 'GET'])
def paid_details():
    if request.method == 'POST':
        data = request.form
        num_players = session.get('num_players')
        buy_ins = 0
        cash_outs = 0
        for i in range(num_players):
            buy_ins += int(data[f'buyin_{i}'])
            cash_outs += int(data[f'cashout_{i}'])        
        if buy_ins == cash_outs:
            session['form_data'] = data.to_dict()
            session.pop('extra_data', None)
            return redirect(url_for('paid_results', players=num_players))
        else:
            flash(f'Calculation error  |  Buy-ins: {buy_ins}  |  Cash-outs: {cash_outs}  |  Difference: {abs(buy_ins-cash_outs)}')
            session['form_data'] = data.to_dict()
            return redirect(url_for('paid_details', players=num_players))
    form_data = session.get('form_data', {})
    number_of_players = session.get('num_players')
    return render_template("paid_details.html", players=number_of_players, form_data=form_data)


# PAID VERSION - RESULTS
@app.route('/results', methods=['POST', 'GET'])
def paid_results():

    if request.method == 'POST':        
        # Get new form data
        new_data = request.form.to_dict()
        payer = new_data['payer'].capitalize()
        payee = new_data['payee'].capitalize()

        form_data = session.get('form_data', {})
        num_players = session.get('num_players')

        player_names = [form_data[f'player_{i}'].capitalize() for i in range(num_players)]
        
        if payer not in player_names or payee not in player_names:
            flash("One or more of the names entered were not involved in the game.")
            return redirect(url_for("paid_results"))
        else: 
            # Update session with new data
            previous_data = session.get('extra_data', [])
            previous_data.append(new_data)
            session['extra_data'] = previous_data
            
            return redirect(url_for("paid_results"))
    
    num_players = session.get('num_players')
    form_data = session.get('form_data', {})

    players = []
    for i in range(num_players):
        player = {
            'name': form_data[f'player_{i}'].capitalize(),
            'buyin': float(form_data[f'buyin_{i}']),
            'cashout': float(form_data[f'cashout_{i}'])
        }
        players.append(player)

    # Caluculation for winnings
    session_winnings = [player['cashout'] - player['buyin'] for player in players]
    
    extra_data = session.get('extra_data', [])
    help_needed = False

    if extra_data:
        help_needed = True
        players = update_cashout(players, extra_data)
    
    settlements = calculate_settlements(players)

    return render_template("paid_results.html", form_data=form_data, 
                           players=num_players, settlements=settlements,
                           help_needed=help_needed, winnings=session_winnings)


# SAVE GAME DATA
@app.route('/save-data', methods=['POST', 'GET'])
def save_data():
    form_data = session.get('form_data', {})
    num_players = session.get('num_players')
    game_data = []
    for i in range(num_players):
        player = {
            'name': form_data[f'player_{i}'].capitalize(),
            'buyin': float(form_data[f'buyin_{i}']),
            'cashout': float(form_data[f'cashout_{i}'])
        }
        game_data.append(player)
    game_name = session.get('session_game')
    cash_game = db.session.query(CashGame).filter_by(cash_name=game_name).first()


    new_game = GameData(game_data=game_data, cash_game=cash_game)
    db.session.add(new_game)
    db.session.commit()

    # give feedback and write something here to disable the button being pressed multiple times until the next time this page is visited

    return redirect(url_for('paid_results'))



# FREE VERSION - NUMBER OF PLAYERS
@app.route('/free-count', methods=['POST', 'GET'])
def free_player_count():
    if request.method == 'POST':
        data = request.form
        number_of_players = data["number"]
        if number_of_players:
            session['num_players'] = int(number_of_players)
            return redirect(url_for('free_details', players=number_of_players))
    return render_template("player_count.html")



# FREE VERSION - INPUTS FOR CASH GAME
@app.route('/free-details', methods=['POST', 'GET'])
def free_details():
    if request.method == 'POST':
        data = request.form
        num_players = session.get('num_players')
        buy_ins = 0
        cash_outs = 0
        for i in range(num_players):
            buy_ins += int(data[f'buyin_{i}'])
            cash_outs += int(data[f'cashout_{i}'])        
        if buy_ins == cash_outs:
            session['form_data'] = data.to_dict()
            session.pop('extra_data', None)
            return redirect(url_for('free_results', players=num_players))
        else:
            flash(f'Calculation error  |  Buy-ins: {buy_ins}  |  Cash-outs: {cash_outs}  |  Difference: {abs(buy_ins-cash_outs)}')
            session['form_data'] = data.to_dict()
            return redirect(url_for('free_details', players=num_players))
    form_data = session.get('form_data', {})
    number_of_players = session.get('num_players')
    return render_template("player_details.html", players=number_of_players, form_data=form_data)


# CLEAR DETAILS TABLE
@app.route('/clear-table', methods=['POST', 'GET'])
def clear_table():
    session.pop('form_data', None)
    return redirect(url_for('free_details'))


# FREE VERSION - RESULTS
@app.route('/free-results', methods=['POST', 'GET'])
def free_results():

    if request.method == 'POST':        
        # Get new form data
        new_data = request.form.to_dict()
        payer = new_data['payer'].capitalize()
        payee = new_data['payee'].capitalize()

        form_data = session.get('form_data', {})
        num_players = session.get('num_players')

        player_names = [form_data[f'player_{i}'].capitalize() for i in range(num_players)]
        
        if payer not in player_names or payee not in player_names:
            flash("One or more of the names entered were not involved in the game.")
            return redirect(url_for("free_results"))
        else: 
            # Update session with new data
            previous_data = session.get('extra_data', [])
            previous_data.append(new_data)
            session['extra_data'] = previous_data
            
            return redirect(url_for("free_results"))
    
    num_players = session.get('num_players')
    form_data = session.get('form_data', {})

    players = []
    for i in range(num_players):
        player = {
            'name': form_data[f'player_{i}'].capitalize(),
            'buyin': float(form_data[f'buyin_{i}']),
            'cashout': float(form_data[f'cashout_{i}'])
        }
        players.append(player)

    # Caluculation for winnings
    session_winnings = [player['cashout'] - player['buyin'] for player in players]
    
    extra_data = session.get('extra_data', [])
    help_needed = False

    if extra_data:
        help_needed = True
        players = update_cashout(players, extra_data)
    
    settlements = calculate_settlements(players)

    return render_template("results.html", form_data=form_data, 
                           players=num_players, settlements=settlements,
                           help_needed=help_needed, winnings=session_winnings)


def calculate_settlements(players):
    balances = {player['name']: player['cashout'] - player['buyin'] for player in players}
    creditors = sorted([(name, bal) for name, bal in balances.items() if bal > 0], key=lambda x: x[1], reverse=True)
    debtors = sorted([(name, bal) for name, bal in balances.items() if bal < 0], key=lambda x: x[1])
    
    settlements = []
    while creditors and debtors:
        creditor = creditors.pop(0)
        debtor = debtors.pop(0)
        amount = min(creditor[1], -debtor[1])
        
        settlements.append(
            {
                'ower': debtor[0],
                'owed': creditor[0],
                'amount': f'{amount:.2f}',
        }
        )
        
        new_creditor_balance = creditor[1] - amount
        new_debtor_balance = debtor[1] + amount
        
        if new_creditor_balance > 0:
            creditors.insert(0, (creditor[0], new_creditor_balance))
        if new_debtor_balance < 0:
            debtors.insert(0, (debtor[0], new_debtor_balance))
    
    return settlements


def update_cashout(players, extra_data):
    for session in extra_data:
        payer = session['payer'].capitalize()
        payee = session['payee'].capitalize()
        amount = float(session['amount'])

        for player in players:
            if player['name'] == payer:
                player['cashout'] += amount
            elif player['name'] == payee:
                player['cashout'] -= amount

    return players


def get_ordinal_suffix(day):
    if 11 <= day <= 13:
        return 'th'
    else:
        return {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    

def get_recent_games(limit=3):
    return db.session.query(GameData).order_by(GameData.date.desc()).limit(limit).all()


if __name__ == "__main__":
    app.run(debug=True)

