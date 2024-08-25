from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request, session, jsonify
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey, JSON, DateTime, func, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from typing import List
import os
from dotenv import load_dotenv
import smtplib
import bleach
import secrets
from forms import RegisterForm, LoginForm
from datetime import datetime, timedelta


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_KEY")
Bootstrap5(app)


login_manager = LoginManager()
login_manager.init_app(app)

def current_user_only(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        session_id = request.args.get('session')
        if not session_id:
            abort(400, description="Session ID is required")

        poker_session = db.session.execute(db.select(GameSession).where(GameSession.id == session_id)).scalar()
        if not poker_session or not poker_session.cash_game:
            abort(404, description="Session or associated game not found")

        if current_user.id != poker_session.cash_game.user_id:
            abort(403, description="Access forbidden: You do not own this session")

        return f(*args, **kwargs)
    return decorator


def game_user_only(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        game_id = request.args.get('game_id')
        if not game_id:
            abort(400, description="Game ID is required")

        poker_game = db.session.execute(db.select(CashGame).where(CashGame.id == game_id)).scalar()
        if not poker_game:
            abort(404, description="Poker game not found")
        
        elif poker_game.cash_name == "None":
            abort(403, description="Cannot delete 'None' type games. You are very naughty for trying!")

        if current_user.id != poker_game.user_id:
            abort(403, description="Access forbidden: You do not own this game")

        return f(*args, **kwargs)
    return decorator


app.config['SEND_EMAIL'] = os.getenv("SEND_EMAIL")
app.config['EMAIL_PASS'] = os.getenv("EMAIL_PASS")
app.config['EMAIL_RECEIVE'] = os.getenv("SEND_EMAIL")
app.config['SESSION_COOKIE_SECURE'] = True


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/danibuchsbaum/Split_My_Winnings/instance/poker_database.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))
    # relationship mapping for cash game
    associated_games: Mapped[List["CashGame"]] = relationship("CashGame", back_populates="associated_user")
    

class GameSession(db.Model):
    __tablename__ = "game_data"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_data: Mapped[dict] = mapped_column(JSON)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # relationship mapping for cash game
    cash_game_id: Mapped[int] = mapped_column(ForeignKey("poker_game.id", ondelete="CASCADE"))
    cash_game: Mapped["CashGame"] = relationship("CashGame", back_populates="session_data")

    def __init__(self, game_data, cash_game):
        self.game_data = game_data
        self.cash_game = cash_game


class CashGame(db.Model):
    __tablename__ = "poker_game"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cash_name: Mapped[str] = mapped_column(String(100), nullable=False)
    player_list: Mapped[list] = mapped_column(JSON, default=[])
    currency: Mapped[str] = mapped_column(String(10))
    # relationship mapping for game sessions
    session_data: Mapped[List["GameSession"]] = relationship("GameSession", back_populates="cash_game", cascade="all, delete-orphan")
    # relationship mapping for user
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    associated_user: Mapped["User"] = relationship("User", back_populates="associated_games")

    __table_args__ = (UniqueConstraint('user_id', 'cash_name', name='uix_user_cash_name'),)

    
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
@login_required
def register_success():
    return render_template("register_success.html")


# REGISTER INTEREST
@app.route('/register', methods=['POST', 'GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

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
            new_poker_game = CashGame(
                cash_name="None",
                player_list=[current_user.name],
                currency="$",
                associated_user=current_user
            )
            db.session.add(new_poker_game)
            db.session.commit()
            return redirect(url_for('register_success'))
    return render_template("register.html", form=form)


# DASHBOARD
@app.route('/dashboard', methods=['POST', 'GET'])
@login_required
def dashboard():
    # list of cash games
    result = (
    db.session.query(CashGame).where(CashGame.user_id==current_user.id)
    .outerjoin(GameSession)  # Adjust to match your relationship
    .group_by(CashGame.id)
    .order_by(func.count(GameSession.id).desc(), CashGame.id.desc())
    )
    all_games = result.all()
    games_list = []
    # pull the required data from the poker games in the db
    for game in all_games:
        session_data = game.session_data
        num_sessions = len(session_data)
        total_buyins = sum(
        player['buyin']
        for data in session_data  
        for player in data.game_data  # Iterate over each player in game_data
        )
        avg_buyins = total_buyins / num_sessions if num_sessions > 0 else 0
        amount_won = sum(
        (player['cashout'] - player['buyin'])
        for data in session_data
        for player in data.game_data
        if player['name'] == current_user.name
        )
        games_list.append({
        'name': game.cash_name,
        'sessions': num_sessions,
        'avg_buyin': avg_buyins,
        'amount_won': amount_won,
        'currency': game.currency,
        'id': game.id,
        })

    # 3 most recent games
    games = get_recent_games()
    game_data = [game.game_data for game in games]
    formatted_dates = [game.date.strftime(f"%A %d{get_ordinal_suffix(game.date.day)} %B") for game in games]
    buyins = [sum(data['buyin'] for data in game) for game in game_data]
    owner_data = [next((data['cashout'] - data['buyin'] for data in game if data['name'] == current_user.name), None) for game in game_data]
    game_names = [game.cash_game.cash_name for game in games]
    session_id = [game.id for game in games]
    currency = [game.cash_game.currency for game in games]

    min_length = min(3, len(games_list))

    return render_template("dashboard.html", game_data=game_data, buyins=buyins, date=formatted_dates,
                           owner_data=owner_data, game_name = game_names,
                           games=games_list, min_length=min_length,
                           session_id=session_id, currency=currency)


# VIEW POKER GAME
@app.route('/view-game')
def view_game():
    # game and sessions for chosen game
    game_id = request.args.get('game_id')
    cash_game = db.session.execute(db.select(CashGame).where(CashGame.id == game_id)).scalars().first()
    sessions = db.session.execute(db.select(GameSession).where(GameSession.cash_game_id == game_id)).scalars().all()
    sessions.reverse()

    # data for game history
    game_data = [session.game_data for session in sessions]
    buyins = [sum(data['buyin'] for data in game) for game in game_data]
    owner_data = [next((data['cashout'] - data['buyin'] for data in game if data['name'] == current_user.name), None) for game in game_data]
    formatted_dates = [session.date.strftime(f"%A %d{get_ordinal_suffix(session.date.day)} %B") for session in sessions]

    # Calculate player statistics
    player_stats = []

    for session in sessions:
        for player_data in session.game_data:
            player_name = player_data['name']
            buyin = player_data['buyin']
            cashout = player_data['cashout']

            # Find the player in the list
            player = next((p for p in player_stats if p['name'] == player_name), None)

            if player is None:
                # Player not in list, add new entry
                player_stats.append({
                    'name': player_name,
                    'total_sessions': 1,
                    'total_buyin': buyin,
                    'total_cashout': cashout
                })
            else:
                # Player found, update their stats
                player['total_sessions'] += 1
                player['total_buyin'] += buyin
                player['total_cashout'] += cashout

    # Finalize player statistics
    for player in player_stats:
        player['average_buyin'] = player['total_buyin'] / player['total_sessions']
        player['net'] = player['total_cashout'] - player['total_buyin']

    current_user_name = current_user.name

    # Sort player_stats
    player_stats_sorted = sorted(
        player_stats,
        key=lambda p: (
            p['name'] != current_user_name,     # Ensure current_user_name is first
            -p['total_sessions'],               # Sort by number of sessions (descending)
            -p['average_buyin']                 # Sort by average buyin (descending)
        )
    )

    # Header stats
    biggest_win = {'amount': float('-inf'), 'name': None}
    biggest_loss = {'amount': float('inf'), 'name': None}

    for session in sessions:
        for player_data in session.game_data:
            p_name = player_data['name']
            net = player_data['cashout'] - player_data['buyin']

            if net > biggest_win['amount']:
                biggest_win = {'amount': net, 'name': p_name}

            if net < biggest_loss['amount']:
                biggest_loss = {'amount': net, 'name': p_name}



    
    total_wagered = sum(buyins)

    return render_template("view_game.html", game=cash_game, sessions=sessions, dates=formatted_dates, buyins=buyins,
                            owner_data=owner_data, stats=player_stats_sorted, total_wagered=total_wagered,
                            biggest_loss=biggest_loss, biggest_win=biggest_win)


# DASHBOARD CHART DATA
@app.route('/dash_chart_data')
def dash_chart_data():
    today = datetime.now()

    # Fetch games and sessions for the current user
    associated_games = db.session.execute(db.select(CashGame).where(CashGame.user_id == current_user.id)).scalars().all()
    cash_game_ids = [associated_game.id for associated_game in associated_games]
    associated_sessions = db.session.execute(
    db.select(GameSession).where(GameSession.cash_game_id.in_(cash_game_ids))
    ).scalars().all()
    
    # Initialize lists
    buyins_all = []
    cashouts_all = []
    net_profits_all = []
    buyins_3m = []
    cashouts_3m = []
    net_profits_3m = []
    buyins_1m = []
    cashouts_1m = []
    net_profits_1m = []
    buyins_1w = []
    cashouts_1w = []
    net_profits_1w = []

    for session in associated_sessions:
        for player_data in session.game_data:
            if player_data['name'] == current_user.name:  # Check if the player is the current user
                buyin = player_data['buyin']
                cashout = player_data['cashout']
                net_profit = cashout - buyin
                date = session.date

                # All time
                buyins_all.append(buyin)
                cashouts_all.append(cashout)
                net_profits_all.append(net_profit)

                # Last 3 months
                if date >= today - timedelta(days=90):
                    buyins_3m.append(buyin)
                    cashouts_3m.append(cashout)
                    net_profits_3m.append(net_profit)

                # Last month
                if date >= today - timedelta(days=30):
                    buyins_1m.append(buyin)
                    cashouts_1m.append(cashout)
                    net_profits_1m.append(net_profit)

                # Last week
                if date >= today - timedelta(days=7):
                    buyins_1w.append(buyin)
                    cashouts_1w.append(cashout)
                    net_profits_1w.append(net_profit)

    # Aggregate the results
    results = {
        'all_time': {
            'buyins': sum(buyins_all) / len(buyins_all) if buyins_all else 0,
            'cashouts': sum(cashouts_all) / len(cashouts_all) if cashouts_all else 0,
            'net_profits': sum(net_profits_all),
        },
        'last_3_months': {
            'buyins': sum(buyins_3m) / len(buyins_3m) if buyins_3m else 0,
            'cashouts': sum(cashouts_3m) / len(cashouts_3m) if cashouts_3m else 0,
            'net_profits': sum(net_profits_3m),
        },
        'last_month': {
            'buyins': sum(buyins_1m) / len(buyins_1m) if buyins_1m else 0,
            'cashouts': sum(cashouts_1m) / len(cashouts_1m) if cashouts_1m else 0,
            'net_profits': sum(net_profits_1m),
        },
        'last_week': {
            'buyins': sum(buyins_1w) / len(buyins_1w) if buyins_1w else 0,
            'cashouts': sum(cashouts_1w) / len(cashouts_1w) if cashouts_1w else 0,
            'net_profits': sum(net_profits_1w),
        }
    }

    return jsonify(results)


# ADD A POKER GAME
@app.route('/add-game', methods=['POST', 'GET'])
@login_required
def add_game():
    if request.method == 'POST':
        data = request.form
        game_name = data['name']
        currency = data['currency']
        new_poker_game = CashGame(
            cash_name=game_name,
            player_list=[current_user.name],
            currency=currency,
            associated_user=current_user
        )
        db.session.add(new_poker_game)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("A game with this name already exists. Please choose a different name.")
            return redirect(url_for('add_game'))
        else:
            return redirect(url_for('dashboard'))

    return render_template('add_game.html')


# EDIT A POKER GAME
@app.route('/edit-game', methods=['POST', 'GET'])
def edit_game():
    game_id = request.args.get('game_id')
    game = db.session.execute(db.select(CashGame).where(CashGame.id == game_id)).scalar()
    currency_list = ['$', '£', '€', '₪', '¥']

    if request.method == 'POST':
        print(game)
        data = request.form
        game.cash_name = data['name']
        game.currency = data['currency']
        db.session.commit()

        return redirect(url_for('view_game', game_id=game_id))

    return render_template('edit_game.html', game=game, currency_list=currency_list)


# DELETE A POKER GAME
@app.route('/delete-game', methods=['POST', 'GET'])
@game_user_only
def delete_game():
    game_id = request.args.get('game_id')
    game_to_delete = db.get_or_404(CashGame, game_id)
    if current_user.id == game_to_delete.user_id:
        db.session.delete(game_to_delete)
        db.session.commit()
        return redirect(url_for('dashboard'))
    
    else:
        return abort(403, description="Access forbidden: You do not own this game")


# DELETE A POKER SESSION
@app.route('/delete-session', methods=['POST', 'GET'])
def delete_session():
    session_id = request.args.get('session_id')
    session_to_delete = db.get_or_404(GameSession, session_id)
    game_id = session_to_delete.cash_game_id
    if current_user.id == session_to_delete.cash_game.user_id:
        db.session.delete(session_to_delete)
        db.session.commit()

        # check view_game
        view_game = None
        if request.args.get('view_game'):
            view_game = True

            return redirect(url_for('view_game', game_id=game_id))
    else:
        return abort(403, description="Access forbidden: You do not own this session")
    
    return redirect(url_for('dashboard'))


# EDIT A POKER SESSION
@app.route('/edit-session', methods=['POST', 'GET'])
@current_user_only
def edit_session():
    # get the speicific session and related game
    session_id = request.args.get('session')
    session_to_edit = db.session.execute(db.select(GameSession).where(GameSession.id == session_id)).scalar()
    cash_game = session_to_edit.cash_game
    game_id = cash_game.id

    # get the list of cash games
    result = db.session.execute(db.select(CashGame).where(CashGame.user_id==current_user.id).order_by(CashGame.id))
    all_games = result.scalars().all()
    cash_list = [game.cash_name for game in all_games]

    # check view_game
    view_game = None
    if request.args.get('view_game'):
        view_game = True

    if request.method == 'POST':

        data = request.form
        num_players = len(session_to_edit.game_data)
        buy_ins = 0
        cash_outs = 0
        for i in range(num_players):
            buy_ins += int(data[f'buyin_{i}'])
            cash_outs += int(data[f'cashout_{i}']) 

        if buy_ins == cash_outs:

            player_names = set()
            for i in range(num_players):
                player_name = data[f"player_{i}"]
            
                if player_name in player_names:
                    flash('Cannot have two players with the same name.')
                    return redirect(url_for('edit_session', session=session_id))
                
                player_names.add(player_name)

            if data['selected_game'] != cash_game.cash_name:
                new_cash_game = db.session.execute(db.select(CashGame).where(CashGame.cash_name == data['selected_game'],
                CashGame.user_id == current_user.id)).scalar()
                session_to_edit.cash_game_id = new_cash_game.id
                db.session.commit()
                cash_game = new_cash_game
                    
            # add player names to db
            player_list = cash_game.player_list.copy()
            changed = False
            for i in range(num_players):
                player_name = data[f"player_{i}"].capitalize()
                if player_name not in player_list:
                    player_list.append(player_name)
                    changed = True

            if changed:
                cash_game.player_list = player_list
                db.session.commit()

            # update session in db
            updated_game_data = []
            for i in range(num_players):
                player = {
                    'name': data[f'player_{i}'].capitalize(),
                    'buyin': float(data[f'buyin_{i}']),
                    'cashout': float(data[f'cashout_{i}'])
                }
                updated_game_data.append(player)


            session_to_edit.game_data = updated_game_data
            db.session.commit()

            if view_game:
                return redirect(url_for('view_game', game_id=game_id))

            return redirect(url_for('dashboard'))
        
        else:
            flash(f'Calculation error  |  Buy-ins: {buy_ins}  |  Cash-outs: {cash_outs}  |  Difference: {abs(buy_ins-cash_outs)}')
            return redirect(url_for('edit_session', session=session_id))
    
        
    return render_template('edit_session.html', session=session_to_edit, poker_game=cash_game, cash_games=cash_list,
                           view_game=view_game)


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
            
        return redirect(request.referrer or url_for('home'))


# PAID VERSION - NUMBER OF PLAYERS + GAME
@app.route('/player-count', methods=['POST', 'GET'])
@login_required
def player_count():
    result = db.session.execute(db.select(CashGame).where(CashGame.user_id==current_user.id).order_by(CashGame.id))
    all_games = result.scalars().all()
    cash_list = [game.cash_name for game in all_games]

    if request.method == 'POST':
        data = request.form
        number_of_players = data["number"]
        if int(number_of_players) > 0:
            session['num_players'] = int(number_of_players)
            session['session_game'] = data['selected_game']
            return redirect(url_for('paid_details', players=number_of_players))
        
    return render_template("paid_count.html", cash_game=cash_list)


# PAID VERSION - INPUTS FOR CASH GAME
@app.route('/player-details', methods=['POST', 'GET'])
@login_required
def paid_details():
    # pull the poker game chosen
    game_name = session.get('session_game')
    cash_game = db.session.query(CashGame).filter_by(cash_name=game_name, user_id=current_user.id).first()
    if request.method == 'POST':

        data = request.form
        num_players = session.get('num_players')
        buy_ins = 0
        cash_outs = 0
        for i in range(num_players):
            buy_ins += int(data[f'buyin_{i}'])
            cash_outs += int(data[f'cashout_{i}']) 

        if buy_ins == cash_outs:

            player_names = set()
            for i in range(num_players):
                player_name = data[f"player_{i}"]
            
                if player_name in player_names:
                    flash('Cannot have two players with the same name.')
                    session['form_data'] = data.to_dict()
                    return redirect(url_for('paid_details', players=num_players))
                
                player_names.add(player_name)
                    
                    

            # add player names to db
            player_list = cash_game.player_list.copy()
            changed = False
            for i in range(num_players):
                player_name = data[f"player_{i}"].capitalize()
                if player_name not in player_list:
                    player_list.append(player_name)
                    changed = True

            if changed:
                cash_game.player_list = player_list
                db.session.commit()

            session['form_data'] = data.to_dict()
            session.pop('extra_data', None)

            return redirect(url_for('paid_results', players=num_players))
        
        else:
            flash(f'Calculation error  |  Buy-ins: {buy_ins}  |  Cash-outs: {cash_outs}  |  Difference: {abs(buy_ins-cash_outs)}')
            session['form_data'] = data.to_dict()
            return redirect(url_for('paid_details', players=num_players))
        
    form_data = session.get('form_data', {})
    number_of_players = session.get('num_players')

    return render_template("paid_details.html", players=number_of_players, form_data=form_data, cash_game=cash_game)


# PAID VERSION - RESULTS
@app.route('/results', methods=['POST', 'GET'])
@login_required
def paid_results():

    if request.method == 'POST':        
        # Get new form data
        new_data = request.form.to_dict()
        form_data = session.get('form_data', {})
        num_players = session.get('num_players')

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

    # pass currency from game chosen

    game_name = session.get('session_game')
    cash_game = db.session.query(CashGame).filter_by(cash_name=game_name, user_id=current_user.id).first()

    return render_template("paid_results.html", form_data=form_data, 
                           players=num_players, settlements=settlements,
                           help_needed=help_needed, winnings=session_winnings,
                           cash_game=cash_game)


# TRACK LIVE - COUNT
@app.route('/live-count', methods=['POST', 'GET'])
@login_required
def live_count():
    result = db.session.execute(db.select(CashGame).where(CashGame.user_id==current_user.id).order_by(CashGame.id))
    all_games = result.scalars().all()
    cash_list = [game.cash_name for game in all_games]

    if request.method == 'POST':
        data = request.form
        number_of_players = data["number"]
        if int(number_of_players) > 0:
            session['num_players'] = int(number_of_players)
            session['session_game'] = data['selected_game']
            return redirect(url_for('live_details', players=number_of_players))
        
    return render_template('live_count.html', games=cash_list)


# TRACK LIVE - DETAILS
@app.route('/live-details', methods=['POST', 'GET'])
@login_required
def live_details():
    # pull the poker game chosen
    game_name = session.get('session_game')
    cash_game = db.session.query(CashGame).filter_by(cash_name=game_name, user_id=current_user.id).first()

    # if request.method == 'POST':

    #     data = request.form
    #     num_players = session.get('num_players')
    #     buy_ins = 0
    #     cash_outs = 0
    #     for i in range(num_players):
    #         buy_ins += int(data[f'buyin_{i}'])
    #         cash_outs += int(data[f'cashout_{i}']) 

    #     if buy_ins == cash_outs:

    #         player_names = set()
    #         for i in range(num_players):
    #             player_name = data[f"player_{i}"]
            
    #             if player_name in player_names:
    #                 flash('Cannot have two players with the same name.')
    #                 session['form_data'] = data.to_dict()
    #                 return redirect(url_for('paid_details', players=num_players))
                
    #             player_names.add(player_name)
                    
                    

    #         # add player names to db
    #         player_list = cash_game.player_list.copy()
    #         changed = False
    #         for i in range(num_players):
    #             player_name = data[f"player_{i}"].capitalize()
    #             if player_name not in player_list:
    #                 player_list.append(player_name)
    #                 changed = True

    #         if changed:
    #             cash_game.player_list = player_list
    #             db.session.commit()

    #         session['form_data'] = data.to_dict()
    #         session.pop('extra_data', None)

    #         return redirect(url_for('paid_results', players=num_players))
        
    #     else:
    #         flash(f'Calculation error  |  Buy-ins: {buy_ins}  |  Cash-outs: {cash_outs}  |  Difference: {abs(buy_ins-cash_outs)}')
    #         session['form_data'] = data.to_dict()
    #         return redirect(url_for('paid_details', players=num_players))
        
    number_of_players = session.get('num_players')

    return render_template("live_details.html", players=number_of_players, cash_game=cash_game)


# SAVE GAME DATA
@app.route('/save-data', methods=['POST', 'GET'])
@login_required
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
    cash_game = db.session.query(CashGame).filter_by(cash_name=game_name, user_id=current_user.id).first()


    new_game = GameSession(game_data=game_data, cash_game=cash_game)
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


# CLEAR DETAILS TABLE FOR PAID
@app.route('/paid-clear', methods=['POST', 'GET'])
@login_required
def paid_clear():
    session.pop('form_data', None)
    return redirect(url_for('paid_details'))


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
        form_data = session.get('form_data', {})
        num_players = session.get('num_players')

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
    result = (
        db.session.query(GameSession)
        .join(GameSession.cash_game)  # Join through the CashGame relationship
        .filter(CashGame.user_id == current_user.id)  # Filter by the current user
        .order_by(GameSession.date.desc())  # Order by the date of the GameSession
        .limit(limit)  # Limit the number of results
        .all()
    )
    return result


if __name__ == "__main__":
    app.run(debug=True)

