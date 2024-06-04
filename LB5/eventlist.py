from flask import render_template, url_for, request, redirect, flash, Blueprint, g, send_file, session
from flask_login import login_required, current_user
from functools import wraps
from app import db
from check_rights import CheckRights
import math
import csv
from io import StringIO, BytesIO
from auth import check_perm

bp_eventlist = Blueprint('eventlist', __name__, url_prefix='/eventlist')
PER_PAGE = 10
FIELDS = ["id", "user_id", "path"]

@bp_eventlist.route('/show-all')
@login_required
def show():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Количество записей на одной странице

    cursor = db.connection().cursor(named_tuple=True)

    # Определение запроса в зависимости от роли пользователя
    if current_user.is_admin() or current_user.role_id != CheckRights.USER_ROLE_ID:
        query_count = "SELECT COUNT(*) as count FROM eventlist"
        cursor.execute(query_count)
    else:
        query_count = "SELECT COUNT(*) as count FROM eventlist WHERE user_id = %s"
        cursor.execute(query_count, (current_user.id,))

    total_count = cursor.fetchone().count
    total_pages = math.ceil(total_count / per_page)  # Вычисление общего количества страниц

    offset = (page - 1) * per_page

    # Определение запроса для получения записей
    if current_user.is_admin() or current_user.role_id != CheckRights.USER_ROLE_ID:
        query = '''
        SELECT el.id, el.user_id, el.path, el.created_at, 
               CASE 
                   WHEN u.id IS NULL THEN 'Неаутентифицированный пользователь' 
                   WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL THEN CONCAT(u.first_name, ' ', u.last_name)
                   ELSE 'Нулевой пользователь' 
               END as user_name
        FROM eventlist el
        LEFT JOIN users3 u ON el.user_id = u.id
        ORDER BY el.created_at DESC
        LIMIT %s OFFSET %s
        '''
        cursor.execute(query, (per_page, offset))
    else:
        query = '''
        SELECT el.id, el.user_id, el.path, el.created_at, 
               CASE 
                   WHEN u.id IS NULL THEN 'Неаутентифицированный пользователь' 
                   WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL THEN CONCAT(u.first_name, ' ', u.last_name)
                   ELSE 'Нулевой пользователь' 
               END as user_name
        FROM eventlist el
        LEFT JOIN users3 u ON el.user_id = u.id
        WHERE el.user_id = %s
        ORDER BY el.created_at DESC
        LIMIT %s OFFSET %s
        '''
        cursor.execute(query, (current_user.id, per_page, offset))

    events = cursor.fetchall()

    user_visit_count_query = "SELECT COUNT(*) as count FROM eventlist WHERE user_id = %s"
    cursor.execute(user_visit_count_query, (current_user.id,))

    user_visit_count = cursor.fetchone().count
    cursor.close()

    return render_template('visits/event.html', events=events, count=total_pages, page=page, per_page=per_page, offset=offset, user_visit_count=user_visit_count)

@bp_eventlist.route('/show-path')
@login_required
def show_path():
    cursor = db.connection().cursor(named_tuple=True)
    query = 'SELECT COUNT(*) as count_path, path FROM eventlist GROUP BY path'
    cursor.execute(query)
    events = cursor.fetchall()
    cursor.close()
    return render_template('visits/event_path.html', events=events)

@bp_eventlist.route('/show-path-user')
@check_perm('show_log')
@login_required
def show_path_user():
    cursor = db.connection().cursor(named_tuple=True)

    query = '''
    SELECT COUNT(*) as count, el.user_id, 
           CASE 
               WHEN u.id IS NULL THEN 'Неаутентифицированный пользователь' 
               WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL THEN CONCAT(u.first_name, ' ', u.last_name)
               ELSE 'Нулевой пользователь' 
           END as user_name
    FROM eventlist el
    LEFT JOIN users3 u ON el.user_id = u.id
    GROUP BY el.user_id, u.first_name, u.last_name, u.id
    '''
    cursor.execute(query)

    events = cursor.fetchall()
    cursor.close()
    return render_template('visits/event_path_user.html', events=events)

@bp_eventlist.route('/show-path-site')
@login_required
def show_path_site():
    cursor = db.connection().cursor(named_tuple=True)
    query = '''
        SELECT COUNT(*) as count, path 
        FROM eventlist 
        WHERE user_id = %s 
        GROUP BY path
    '''
    cursor.execute(query, (current_user.id,))
    events = cursor.fetchall()
    cursor.close()
    return render_template('visits/event_path_site.html', events=events)

@bp_eventlist.route("/csvsave")
@login_required
def save_to_csv():
    template = request.args.get('template')
    limit = 10  # Ограничение на количество записей для общего отчета

    cursor = db.connection().cursor()
    output = StringIO()
    writer = csv.writer(output)

    if template == 'user':
        limit = 18  # Устанавливаем ограничение на 18 записей для отчета по страницам
        query = '''
            SELECT COUNT(*) as count, path 
            FROM eventlist 
            WHERE user_id = %s 
            GROUP BY path
            LIMIT %s
        '''
        cursor.execute(query, (current_user.id, limit))
        path_events = cursor.fetchall()

        writer.writerow(['Журнал посещений по страницам'])
        writer.writerow(['№', 'Страница', 'Количество посещений'])
        for idx, event in enumerate(path_events, start=1):
            writer.writerow([idx, event[1], event[0]])

    elif template == 'all':
        if current_user.is_admin():
            query = '''
            SELECT DISTINCT el.id, el.user_id, el.path, el.created_at, 
                   CASE 
                       WHEN u.id IS NULL THEN 'Неаутентифицированный пользователь' 
                       WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL THEN CONCAT(u.first_name, ' ', u.last_name)
                       ELSE 'Нулевой пользователь' 
                   END as user_name
            FROM eventlist el
            LEFT JOIN users3 u ON el.user_id = u.id
            ORDER BY el.created_at DESC
            LIMIT %s
            '''
            cursor.execute(query, (limit,))
            logs = cursor.fetchall()

            writer.writerow(['Журнал посещений'])
            writer.writerow(['№', 'Пользователь', 'Путь', 'Дата создания'])
            for idx, log in enumerate(logs, start=1):
                writer.writerow([idx, log[4], log[2], log[3]])
        else:
            query = '''
            SELECT DISTINCT el.id, el.user_id, el.path, el.created_at, 
                   CASE 
                       WHEN u.id IS NULL THEN 'Неаутентифицированный пользователь' 
                       WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL THEN CONCAT(u.first_name, ' ', u.last_name)
                       ELSE 'Нулевой пользователь' 
                   END as user_name
            FROM eventlist el
            LEFT JOIN users3 u ON el.user_id = u.id
            WHERE el.user_id = %s
            ORDER BY el.created_at DESC
            LIMIT %s
            '''
            cursor.execute(query, (current_user.id, limit))
            logs = cursor.fetchall()

            writer.writerow(['Журнал посещений'])
            writer.writerow(['№', 'Пользователь', 'Путь', 'Дата создания'])
            for idx, log in enumerate(logs, start=1):
                writer.writerow([idx, log[4], log[2], log[3]])

    elif template == 'user_count' and current_user.is_admin():
        query = '''
        SELECT COUNT(*) as count, el.user_id, 
               CASE 
                   WHEN u.id IS NULL THEN 'Неаутентифицированный пользователь' 
                   WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL THEN CONCAT(u.first_name, ' ', u.last_name)
                   ELSE 'Нулевой пользователь' 
               END as user_name
        FROM eventlist el
        LEFT JOIN users3 u ON el.user_id = u.id
        GROUP BY el.user_id, u.first_name, u.last_name, u.id
        '''
        cursor.execute(query)
        user_events = cursor.fetchall()

        writer.writerow(['Журнал посещений по пользователям'])
        writer.writerow(['№', 'Пользователь', 'Количество посещений'])
        for idx, user_event in enumerate(user_events, start=1):
            writer.writerow([idx, user_event[2], user_event[0]])

    cursor.close()

    output_bytes = BytesIO()
    output_bytes.write(output.getvalue().encode('utf-8'))
    output_bytes.seek(0)

    filename = "logs.csv"
    if template == 'user':
        filename = "user_logs.csv"
    elif template == 'user_count' and current_user.is_admin():
        filename = "user_count_logs.csv"

    return send_file(
        output_bytes, 
        download_name=filename, 
        as_attachment=True, 
        mimetype='text/csv'
    )
