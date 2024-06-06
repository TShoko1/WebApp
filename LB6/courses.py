from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import db, Course, Category, User, Review
from tools import CoursesFilter, ImageSaver
from datetime import datetime

bp = Blueprint('courses', __name__, url_prefix='/courses')

COURSE_PARAMS = [
    'author_id', 'name', 'category_id', 'short_desc', 'full_desc'
]

def params():
    return { p: request.form.get(p) or None for p in COURSE_PARAMS }

def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': [x for x in request.args.getlist('category_ids') if x],
    }

@bp.route('/')
def index():
    courses = CoursesFilter(**search_params()).perform()
    pagination = db.paginate(courses)
    courses = pagination.items
    categories = db.session.execute(db.select(Category)).scalars()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())

@bp.route('/new')
@login_required
def new():
    course = Course()
    categories = db.session.execute(db.select(Category)).scalars()
    users = db.session.execute(db.select(User)).scalars()
    return render_template('courses/new.html',
                           categories=categories,
                           users=users,
                           course=course)

@bp.route('/create', methods=['POST'])
@login_required
def create():
    f = request.files.get('background_img')
    img = None
    course = Course()
    try:
        if f and f.filename:
            img = ImageSaver(f).save()

        image_id = img.id if img else None
        course = Course(**params(), background_image_id=image_id)
        db.session.add(course)
        db.session.commit()
    except IntegrityError as err:
        flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных. ({err})', 'danger')
        db.session.rollback()
        categories = db.session.execute(db.select(Category)).scalars()
        users = db.session.execute(db.select(User)).scalars()
        return render_template('courses/new.html',
                            categories=categories,
                            users=users,
                            course=course)

    flash(f'Курс {course.name} был успешно добавлен!', 'success')

    return redirect(url_for('courses.index'))

@bp.route('/<int:course_id>')
def show(course_id):
    course = db.get_or_404(Course, course_id)
    reviews = db.session.execute(
        db.select(Review).where(Review.course_id == course_id).order_by(Review.created_at.desc()).limit(5)
    ).scalars()
    user_review = None
    if current_user.is_authenticated:
        user_review = db.session.execute(
            db.select(Review).where(Review.course_id == course_id, Review.user_id == current_user.id)
        ).scalar()

    return render_template('courses/show.html', course=course, reviews=reviews, user_review=user_review)

@bp.route('/<int:course_id>/reviews', methods=['GET', 'POST'])
def all_reviews(course_id):
    course = db.get_or_404(Course, course_id)
    page = request.args.get('page', 1, type=int)
    sort_order = request.args.get('sort_order', 'newest')

    sort_column = {
        'newest': Review.created_at.desc(),
        'positive': Review.rating.desc(),
        'negative': Review.rating.asc()
    }.get(sort_order, Review.created_at.desc())

    reviews_query = db.select(Review).where(Review.course_id == course_id).order_by(sort_column)
    pagination = db.paginate(reviews_query, page=page, per_page=5)
    reviews = pagination.items

    return render_template('courses/all_reviews.html', course=course, reviews=reviews, pagination=pagination, sort_order=sort_order)

@bp.route('/<int:course_id>/reviews/add', methods=['POST'])
@login_required
def add_review(course_id):
    course = db.get_or_404(Course, course_id)
    rating = request.form.get('rating', type=int)
    text = request.form.get('text')

    existing_review = db.session.execute(
        db.select(Review).where(Review.course_id == course_id, Review.user_id == current_user.id)
    ).scalar()

    if existing_review:
        flash('Вы уже оставили отзыв на этот курс.', 'warning')
        return redirect(url_for('courses.show', course_id=course_id))

    review = Review(
        rating=rating,
        text=text,
        created_at=datetime.now(),
        course_id=course_id,
        user_id=current_user.id
    )

    db.session.add(review)

    # Пересчитать рейтинг курса
    course.rating_sum += rating
    course.rating_num += 1

    try:
        db.session.commit()
        flash('Ваш отзыв был успешно добавлен.', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Произошла ошибка при добавлении отзыва.', 'danger')

    return redirect(url_for('courses.show', course_id=course_id))
