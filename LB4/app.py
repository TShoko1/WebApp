from flask import Flask, render_template, url_for, request, session, redirect, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from mysql_db import MySQL
import re
import hashlib


app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)

db = MySQL(app)

login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к данной странице необходимо пройти аутентификацию'
login_manager.login_message_category = "warning" 

application = app


app.config.from_pyfile('config.py')

class User(UserMixin):
    def __init__(self, user_id, login, password_hash=None, first_name=None, last_name=None):
        self.id = user_id
        self.login = login
        self.password_hash = password_hash
        self.first_name = first_name
        self.last_name = last_name

    

@login_manager.user_loader
def load_user(user_id):
    cursor = db.connection().cursor(named_tuple=True)
    query = 'SELECT id, login, password_hash, first_name, last_name FROM users3 WHERE users3.id = %s'
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(user.id, user.login, user.password_hash, user.first_name, user.last_name)
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth')
def auth():
    return render_template('auth.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        remember = request.form.get('remember') == 'on'
        cursor = db.connection().cursor(named_tuple=True)
        query = 'SELECT * FROM users3 WHERE users3.login = %s and users3.password_hash = SHA2(%s, 256)'
        cursor.execute(query, (login,password))
        user = cursor.fetchone()
        cursor.close()
        if user:
                login_user(User(user.id, user.login),remember = remember)
                param = request.args.get('next')
                flash('Успешный вход','success')
                return redirect(param or url_for('index'))
        flash('Логин или пароль введены неверно','danger')
    return render_template('login.html')
    

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/userlist')
@login_required
def userlist():
    cursor = db.connection().cursor(named_tuple=True)
    query = 'SELECT id, login, first_name, last_name FROM users3'
    cursor.execute(query)
    users = cursor.fetchall()
    cursor.close()
    return render_template('userlist.html', users=users)


@app.route('/createuser', methods=["GET", "POST"])
@login_required
def createuser():
    if request.method == 'GET':
        return render_template('createuser.html')
    elif request.method == "POST":
        login = request.form['login']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']
        errors = validate_user_data(login, password, first_name, last_name)
        if errors:
            for error in errors.items():
                flash(f'{error}', 'danger')
            return render_template('createuser.html', login=login, first_name=first_name, last_name=last_name)
        cursor = db.connection().cursor(named_tuple=True)
        query = 'INSERT INTO users3 (login, password_hash, first_name, last_name) VALUES (%s, SHA2(%s, 256), %s, %s)'
        values = (login, password, first_name, last_name)
        cursor.execute(query, values)
        db.connection().commit()
        cursor.close()
        flash('Пользователь успешно создан','success')
        return redirect(url_for('userlist'))

@app.route('/user/show/<int:user_id>')
@login_required
def show_user(user_id):
    cursor = db.connection().cursor(named_tuple=True)
    query = 'SELECT id, login, first_name, last_name, middle_name FROM users3 WHERE id=%s'
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return render_template('show_user.html', user=user)



@app.route('/user/edit/<int:user_id>', methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    if request.method == 'POST':
        cursor = db.connection().cursor(named_tuple=True)
        #login = request.form['login']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        middle_name = request.form['middle_name']
        query = 'UPDATE users3 SET first_name=%s, last_name=%s, middle_name=%s WHERE id=%s'
        cursor.execute(query, (first_name, last_name, middle_name, user_id))
        db.connection().commit()
        cursor.close()
        flash(f'Данные пользователя {login} изменены','success')
        return redirect(url_for('userlist'))
    
    cursor = db.connection().cursor(named_tuple=True)
    query = 'SELECT id, login, first_name, last_name FROM users3 WHERE id=%s'
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return render_template('edit_user.html', user=user)

@app.route('/user/delete/<int:user_id>', methods=["GET", "POST"])
@login_required
def delete_user(user_id):
    if request.method == 'POST':
        cursor = db.connection().cursor(named_tuple=True)
        login = request.form['login']
        query = 'DELETE FROM users3 WHERE id=%s'
        cursor.execute(query, (user_id,))
        db.connection().commit()
        cursor.close()
        flash(f'Пользователь {login} удалены','success')
        return redirect(url_for('userlist'))
    
    cursor = db.connection().cursor(named_tuple=True)
    query = 'SELECT id, login, first_name, last_name FROM users3 WHERE id=%s'
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return render_template('delete_user.html', user=user)

def validate_user_data(login, password, first_name, last_name):
    errors = {}
    # Проверка на наличие пустых значений
    if not login:
        errors['login'] = "Логин не может быть пустым"
    if not password:
        errors['password'] = "Пароль не может быть пустым"
    if not first_name:
        errors['first_name'] = "Имя не может быть пустым"
    if not last_name:
        errors['last_name'] = "Фамилия не может быть пустой"

    # Проверка логина
    if login and (len(login) < 5 or not re.match("^[a-zA-Z0-9]+$", login)):
        errors['login'] = "Логин должен состоять только из латинских букв и цифр и иметь длину не менее 5 символов"

    # Проверка пароля
    if password:
        if ' ' in password:
            errors['password'] = "Пароль не должен содержать пробелы"
        elif len(password) < 8:
            errors['password'] = "Пароль должен содержать не менее 8 символов"
        elif len(password) > 128:
            errors['password'] = "Пароль не должен превышать 128 символов"
        elif not re.search(r"[A-ZА-Я]", password) or not re.search(r"[a-zа-я]", password):
            errors['password'] = "Пароль должен содержать как минимум одну заглавную и одну строчную букву"
        elif not re.search(r"[0-9]", password):
            errors['password'] = "Пароль должен содержать минимум одну цифру"
        elif not re.match(r"^[a-zA-Zа-яА-Я0-9~!?@#$%^&*()_\-\+\[\]{}><\\|\"',.:;/]+$", password):
            errors['password'] = "Пароль содержит недопустимые символы"
        
    return errors

@app.route('/change_password/<int:user_id>', methods=["GET", "POST"])
@login_required
def change_password(user_id):
    error_messages = {}
    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        user = load_user(user_id)
        if not user or not check_password_hash(user.password_hash, old_password):
            error_messages['old_password'] = 'Старый пароль указан неверно'
        
        if new_password != confirm_password:
            error_messages['confirm_password'] = 'Пароли не совпадают'

        # Проверка нового пароля
        password_errors = validate_user_data(user.login, new_password, user.first_name, user.last_name).get('password', None)
        if password_errors:
            error_messages['password'] = password_errors
        
        print('Error messages:', error_messages)
        if not error_messages:
            try:
                cursor = db.connection().cursor(named_tuple=True)
                query = 'UPDATE users3 SET password_hash=SHA2(%s, 256) WHERE id=%s'
                cursor.execute(query, (new_password, user.id))
                db.connection().commit()
            except Exception as e:
                print("Ошибка обновления пароля:", e)
                flash('Произошла ошибка при смене пароля', 'danger')
            finally:
                cursor.close()
            flash('Пароль успешно изменен', 'success')
            return redirect(url_for('index'))

    return render_template('change_password.html', error_messages=error_messages)

def check_password_hash(stored_password_hash, provided_password):
    provided_password_hash = hashlib.sha256(provided_password.encode()).hexdigest()
    return provided_password_hash == stored_password_hash