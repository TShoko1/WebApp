from flask import Flask, render_template,url_for, request, session, redirect, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from mysql_db import MySQL
import string
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
    def __init__(self, user_id, login):
        self.id = user_id
        self.login = login

    

@login_manager.user_loader
def load_user(user_id):
    cursor = db.connection().cursor(named_tuple=True)
    query = 'SELECT id, login FROM users3 WHERE users3.id = %s'
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(user.id, user.login)
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth')
def auth():
    return render_template('auth.html')

def check_login(login):
    if len(login) < 5:
        return 'Длина логина не может быть меньше 5'
    
    elif not all([(char in string.ascii_letters or char in string.digits) for char in login]):
        return 'Логин должен состоять только из латинских букв и цифр'
    
    return None

def check_passwd(passwd):
    upper_letters = string.ascii_uppercase + 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
    lower_letters = string.ascii_lowercase + 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    perm_letters = '~!?@#$%^&*_-+()[]{\}></\|\"\'.,:;'

    if len(passwd) < 8:
        return 'Пароль должен содержать не менее 8 символов'
    elif len(passwd) > 128:
        return 'Пароль не должен превышать 128 символов'
    elif not any([char in upper_letters for char in passwd]) or not any([char in lower_letters for char in passwd]):
        return 'Пароль должен состоять как минимум из одной заглавной и одной строчной буквы'
    elif not all([char in (upper_letters + lower_letters + perm_letters + string.digits) for char in passwd]):
        return 'Пароль должен состоять только из латинских или кириллических букв'
    elif not any([char in string.digits for char in passwd]):
        return 'Пароль должен состоять хотя бы из одной цифры'
    elif ' ' in passwd:
        return 'Пароль не должен содержать пробелы'
    
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_login = None
    error_passwd = None
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        remember = request.form.get('remember') == 'on'
        if check_login(login) != None or check_passwd(password) != None:
            error_login = check_login(login)
            error_passwd = check_passwd(password)
            return render_template('login.html', error_login=error_login, error_passwd=error_passwd)
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
    error_login = None
    error_passwd = None
    error_first_name = None
    error_last_name = None
    if request.method == 'GET':
        return render_template('createuser.html')
    elif request.method == "POST":
        login = request.form['login']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']
        if check_login(login) != None or check_passwd(password) != None or first_name == '' or last_name == '':
            if first_name == '':
                error_first_name = 'Поле не может быть пустым'
            if last_name == '':
                error_last_name = 'Поле не может быть пустым'
            error_login = check_login(login)
            error_passwd = check_passwd(password)
            flash('Пользователь не создан','danger')
            return render_template('createuser.html', error_login=error_login, error_passwd=error_passwd, 
                                   error_first_name=error_first_name, error_last_name=error_last_name)
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

def check_password_hash(stored_password_hash, provided_password):
    provided_password_hash = hashlib.sha256(provided_password.encode()).hexdigest()
    return provided_password_hash == stored_password_hash

@app.route('/user/change/<int:user_id>', methods=["GET", "POST"])
@login_required
def change_password(user_id):
    error_old_passwd = None
    error_new_passwd = None
    error_both_passwd = None
    if request.method == 'POST':
        cursor = db.connection().cursor(named_tuple=True)
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        new_rep_password = request.form['new_rep_password']
        query = 'SELECT password_hash FROM users3 WHERE id=%s'
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()        

        if result is None or not check_password_hash(result.password_hash, old_password):
            error_old_passwd = 'Неправильный текущий пароль'
            return render_template('change_password.html', error_old_passwd=error_old_passwd)

        error_new_passwd = check_passwd(new_password)
        if error_new_passwd is not None:
            return render_template('change_password.html', error_new_passwd=error_new_passwd)
        
        if new_password != new_rep_password:
            error_both_passwd = 'Пароли не совпадают'
            return render_template('change_password.html', error_both_passwd=error_both_passwd)
        
        query = 'UPDATE users3 SET password_hash=SHA2(%s, 256) WHERE id=%s'
        cursor.execute(query, (new_password, user_id))
        db.connection().commit()
        cursor.close()
        flash('Пароль пользователя изменен','success')
        return redirect(url_for('userlist'))
    
    """cursor = db.connection().cursor(named_tuple=True)
    query = 'SELECT id, login, first_name, last_name FROM users3 WHERE id=%s'
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return render_template('change_password.html', user=user)"""
    return render_template('change_password.html')

