from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request, session
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from typing import List
from forms import Register
import os
from dotenv import load_dotenv
import smtplib
import bleach
import secrets

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_KEY")
Bootstrap5(app)


app.config['SEND_EMAIL'] = os.getenv("SEND_EMAIL")
app.config['EMAIL_PASS'] = os.getenv("EMAIL_PASS")
app.config['EMAIL_RECEIVE'] = os.getenv("SEND_EMAIL")
app.config['SESSION_COOKIE_SECURE'] = True


@app.route('/', methods=['POST', 'GET'])
def home():
    return render_template("index.html")


# THANK YOU PAGE
@app.route('/thank-you', methods=['POST', 'GET'])
def thank_you():
    return render_template("thank_you.html")


# REGISTER INTEREST
@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        form_data = request.form
        email_entered = form_data['email']
        name_entered = form_data['name']
        try:
            with smtplib.SMTP("smtp.gmail.com") as connection:
                connection.starttls()
                connection.login(user=app.config['SEND_EMAIL'], password=app.config['EMAIL_PASS'])
                connection.sendmail(
                    from_addr=app.config['SEND_EMAIL'], 
                    to_addrs=app.config['EMAIL_RECEIVE'], 
                    msg=f"Subject: New Poker Registration\n\n{name_entered} is interested in the full version of the website!\nEmail: {email_entered}"
                    )
        except Exception as e:
            return f"An error occurred: {e}", 500
        
        return redirect(url_for('thank_you'))
    return render_template("register.html")


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
@app.route('/results', methods=['POST', 'GET'])
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


if __name__ == "__main__":
    app.run(debug=True)

