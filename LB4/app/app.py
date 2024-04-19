from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from db import MySQL
import mysql.connector.errors
from hashlib import sha256
import re


app = Flask(__name__)
db = MySQL(app)

app.config.from_pyfile('config.py')

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к данной странице необходимо пройти аутентификацию'
login_manager.login_message_category = "warning"


class User(UserMixin):
    def __init__(self, user_id, login):
        self.id = user_id
        self.login = login


@login_manager.user_loader
def load_user(UID):
    cursor = db.connection().cursor(named_tuple=True)
    query = 'SELECT id, login FROM users WHERE id = %s'
    cursor.execute(query, (UID,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(user.id, user.login)
    return None


@app.route('/')
def index():
    cursor = db.connection().cursor(named_tuple=True)
    query = "SELECT users.id, users.login, users.first_name, users.last_name, users.patronymic, roles.role_name FROM `users` \
            JOIN roles on users.role_id = roles.id \
            ORDER BY users.id"
    cursor.execute(query)
    users = cursor.fetchall()
    cursor.close()
    return render_template('index.html', users=users)


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    login = request.form['login']
    password = request.form['password']
    remember = request.form.get('remember') == 'on'
    cursor = db.connection().cursor(named_tuple=True)
    query = "SELECT * FROM `users` \
            WHERE `login` = %s AND `password_hash` = SHA2(%s, 256)"
    cursor.execute(query, (login, password))
    user = cursor.fetchone()
    cursor.close()

    if not user:
        flash('Логин или пароль введены неверно', 'danger')
        return render_template("login.html")

    login_user(User(user.id, user.login), remember=remember)
    param = request.args.get('next')
    flash('Успешный вход', 'success')
    return redirect(param or url_for('index'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/showUser/<int:UID>', methods=["GET", "POST"])
def showUser(UID: int):
    cursor = db.connection().cursor(named_tuple=True)
    query = "SELECT users.id, users.login, users.first_name, users.last_name, users.patronymic, roles.role_name FROM `users` \
            JOIN roles on users.role_id = roles.id \
            WHERE users.id = %s"
    cursor.execute(query, (UID,))
    user = cursor.fetchone()
    cursor.close()
    if user is None:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('index'))
    return render_template('showUser.html', user=user)


@app.route('/createUser', methods=["GET", "POST"])
@login_required
def createUser():
    cursor = db.connection().cursor(named_tuple=True)
    query = "SELECT role_name FROM roles"
    cursor.execute(query)
    roles = cursor.fetchall()
    cursor.close()
    if request.method == "GET":
        return render_template('createUser.html', roles=roles, selectedRole="", errors={}, user={'login': '', 'password': '', 'first_name': '', 'last_name': '', 'patronymic': '', 'role': ''})

    login = request.form.get("login")
    password = request.form.get("password")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    patronymic = request.form.get("patronymic")
    role = "Нет" if request.form.get(
        "role") == "Выберите роль" else request.form.get("role")

    errors = {}
    if not re.fullmatch(r"[a-zA-Z0-9]{5,}", login):
        # flash('Логин должен состоять только из латинских букв и цифр и иметь длину не менее 5 символов', 'danger')
        errors["login"] = "Логин должен состоять только из латинских букв и цифр и иметь длину не менее 5 символов"
    if not login:
        errors["login"] = "Логин не может быть пустым"
        # flash('Логин не может быть пустым', 'danger')
    if not re.fullmatch(r"^(?=.+[a-zа-я])(?=.+[A-ZА-Я])(?=.*\d)(?!.*\s)[a-zA-Zа-яА-Я\d~!?@#$%^&*_\-+()\[\]{}><\\/|\"\'.,:;]{8,128}$", password):
        # flash(
        #     'Пароль не сответствует требованиям: не менее 8 символов; не более 128 символов; как минимум одна заглавная и одна строчная буква; только латинские или кириллические буквы; как минимум одна цифра; только арабские цифры; без пробелов; Другие допустимые символы:~ ! ? @ # $ % ^ & * _ - + ( ) [ ] { } > < / \ | \" \' . , : ;', 'danger')
        errors[
            "password"] = "Пароль не сответствует требованиям: не менее 8 символов; не более 128 символов; как минимум одна заглавная и одна строчная буква; только латинские или кириллические буквы; как минимум одна цифра; только арабские цифры; без пробелов; Другие допустимые символы:~ ! ? @ # $ % ^ & * _ - + ( ) [ ] { } > < / \ | \" \' . , : ;"
    if not password:
        # flash('Пароль не может быть пустым', 'danger')
        errors["password"] = "Пароль не может быть пустым"
    if not last_name:
        # flash('Фамилия не может быть пустой', 'danger')
        errors["last_name"] = "Фамилия не может быть пустой"
    if not first_name:
        # flash('Имя не может быть пустым', 'danger')
        errors["first_name"] = "Имя не может быть пустым"
    if errors:
        return render_template('createUser.html', roles=roles, selectedRole=role, errors=errors, user={'login': login, 'password': password, 'first_name': first_name, 'last_name': last_name, 'patronymic': patronymic, 'role': role})

    cursor = db.connection().cursor(named_tuple=True)

    query = "SELECT id FROM `roles` WHERE `role_name` = %s"
    values = (role,)
    try:
        cursor.execute(query, values)
        roleId = cursor.fetchone().id
    except Exception as e:
        flash(e, 'danger')
        return render_template('createUser.html', roles=roles, selectedRole=role, errors={}, user={'login': login, 'password': password, 'first_name': first_name, 'last_name': last_name, 'patronymic': patronymic, 'role': role})

    query = "INSERT INTO `users` (`login`, `password_hash`, `first_name`, `last_name`, `patronymic`, `role_id`) \
            VALUES (%s, SHA2(%s, 256), %s, %s, %s, %s)"
    values = (login, password, first_name, last_name, patronymic, roleId)
    try:
        cursor.execute(query, values)
        db.connection().commit()
        cursor.close()
        flash('Пользователь успешно создан', 'success')
        return redirect(url_for('index'))
    except mysql.connector.errors.IntegrityError as e:
        cursor.close()
        flash(f"Логин `{login}` уже занят", 'danger')
        return render_template('createUser.html', roles=roles, selectedRole=role, errors={}, user={'login': login, 'password': password, 'first_name': first_name, 'last_name': last_name, 'patronymic': patronymic, 'role': role})
    except Exception as e:
        cursor.close()
        flash(e, 'danger')
        return render_template('createUser.html', roles=roles, selectedRole=role, errors={}, user={'login': login, 'password': password, 'first_name': first_name, 'last_name': last_name, 'patronymic': patronymic, 'role': role})


@app.route('/editUser/<int:UID>', methods=["GET", "POST"])
@login_required
def editUser(UID: int):
    cursor = db.connection().cursor(named_tuple=True)

    query = "SELECT * FROM `users` WHERE `id` = %s"
    values = (UID,)
    cursor.execute(query, values)
    user = cursor.fetchone()

    query = "SELECT role_name FROM `roles`"
    cursor.execute(query)
    roles = cursor.fetchall()

    query = "SELECT role_name FROM `roles` WHERE `id` = %s"
    cursor.execute(query, (user.role_id,))
    selectedRole = cursor.fetchone()

    if request.method == "GET":
        return render_template('editUser.html', roles=roles, selectedRole=selectedRole.role_name, errors={}, user=user)

    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    patronymic = request.form.get("patronymic")
    role = "Нет" if request.form.get(
        "role") == "Выберите роль" else request.form.get("role")

    errors = {}
    if not first_name:
        # flash('Имя не может быть пустым', 'danger')
        errors["first_name"] = "Имя не может быть пустым"
    if not last_name:
        # flash('Фамилия не может быть пустой', 'danger')
        errors["last_name"] = "Фамилия не может быть пустой"
    if errors:
        return render_template('createUser.html', roles=roles, selectedRole=role, errors=errors, user={'first_name': first_name, 'last_name': last_name, 'patronymic': patronymic, 'role': role})

    query = "UPDATE users \
            SET first_name = %s, last_name = %s, patronymic = %s, role_id = (SELECT id FROM roles WHERE role_name = %s) \
            WHERE id = %s; "
    values = (first_name, last_name, patronymic, role, UID)
    try:
        cursor.execute(query, values)
        db.connection().commit()
        cursor.close()
        flash('Пользователь успешно отредактирован', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(e, 'danger')
        return render_template('editUser.html', roles=roles, selectedRole=role, errors={}, user={'first_name': first_name, 'last_name': last_name, 'patronymic': patronymic, 'role': role})


@app.route('/deleteUser/<int:UID>')
@login_required
def deleteUser(UID: int):
    cursor = db.connection().cursor()
    try:
        query = "DELETE FROM `users` WHERE `id` = %s;"
        values = (UID,)
        cursor.execute(query, values)
        db.connection().commit()
        flash('Пользователь успешно удален', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    finally:
        cursor.close()

    return redirect(url_for('index'))


@app.route('/changePassword', methods=["GET", "POST"])
@login_required
def changePassword():
    if request.method == "GET":
        return render_template('changePassword.html', user={}, errors={})

    oldPassword = request.form.get("oldPassword")
    newPassword = request.form.get("newPassword")
    repeatPassword = request.form.get("repeatPassword")

    old = sha256()
    old.update(oldPassword.encode('UTF-8'))
    oldPasswordSHA2 = old.hexdigest()

    new = sha256()
    new.update(newPassword.encode('UTF-8'))
    newPasswordSHA2 = new.hexdigest()

    cursor = db.connection().cursor(named_tuple=True)
    try:
        query = "SELECT password_hash FROM `users` WHERE `id` = %s"
        values = (current_user.id,)
        cursor.execute(query, values)
        password_hash = cursor.fetchone()
    except Exception as e:
        flash(e, 'danger')
        return render_template('changePassword.html', errors={})

    errors = {}
    if oldPasswordSHA2 != password_hash.password_hash:
        flash('Старый пароль введен неверно', 'danger')
        errors["oldPassword"] = "Старый пароль введен неверно"
    if newPassword != repeatPassword:
        flash('Пароли не совпадают', 'danger')
        errors["repeatPassword"] = "Пароли не совпадают"
    if newPasswordSHA2 == password_hash.password_hash:
        flash('Старый и новый пароли совпадают', 'danger')
        errors["newPassword"] = "Старый и новый пароли совпадают"
    if not re.fullmatch(r"^(?=.+[a-zа-я])(?=.+[A-ZА-Я])(?=.*\d)(?!.*\s)[a-zA-Zа-яА-Я\d~!?@#$%^&*_\-+()\[\]{}><\\/|\"\'.,:;]{8,128}$", newPassword):
        flash(
            'Новый пароль не сответствует требованиям: не менее 8 символов; не более 128 символов; как минимум одна заглавная и одна строчная буква; только латинские или кириллические буквы; как минимум одна цифра; только арабские цифры; без пробелов; Другие допустимые символы:~ ! ? @ # $ % ^ & * _ - + ( ) [ ] { } > < / \ | \" \' . , : ;', 'danger')
        errors[
            "newPassword"] = "Новый пароль не сответствует требованиям: не менее 8 символов; не более 128 символов; как минимум одна заглавная и одна строчная буква; только латинские или кириллические буквы; как минимум одна цифра; только арабские цифры; без пробелов; Другие допустимые символы:~ ! ? @ # $ % ^ & * _ - + ( ) [ ] { } > < / \ | \" \' . , : ;"

    if errors:
        return render_template('changePassword.html', errors=errors)

    query = "UPDATE `users` SET `password_hash` = SHA2(%s, 256) WHERE `id` = %s"
    values = (newPassword, current_user.id)
    try:
        cursor.execute(query, values)
        db.connection().commit()
        cursor.close()
        flash('Пароль успешно изменен', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        cursor.close()
        flash(e, 'danger')
        return render_template('changePassword.html', errors={})
