from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, EmailField, SubmitField, PasswordField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange, EqualTo
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ваш-секретный-ключ-измените-это'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sportcareer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ============================================
# МОДЕЛИ БАЗЫ ДАННЫХ
# ============================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(200), nullable=False)
    sport = db.Column(db.String(50))
    position = db.Column(db.String(100))
    experience = db.Column(db.Integer, default=0)
    level = db.Column(db.String(50))
    city = db.Column(db.String(100))
    goals = db.Column(db.String(100))
    about = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_type = db.Column(db.String(20), default='seeker')
    
    # Отношения для сообщений
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def unread_messages_count(self):
        """Количество непрочитанных сообщений"""
        return Message.query.filter_by(receiver_id=self.id, is_read=False).count()

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    favorite_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id], backref='favorites')
    favorite_user = db.relationship('User', foreign_keys=[favorite_user_id])

# НОВАЯ МОДЕЛЬ: Сообщения
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    def formatted_time(self):
        """Форматированное время для отображения"""
        now = datetime.utcnow()
        if self.timestamp.date() == now.date():
            return self.timestamp.strftime('%H:%M')
        elif self.timestamp.year == now.year:
            return self.timestamp.strftime('%d %b')
        else:
            return self.timestamp.strftime('%d.%m.%Y')

class ResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Создаем таблицы в базе данных
with app.app_context():
    db.create_all()

# ============================================
# ФОРМЫ
# ============================================

class ContactForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired(message="Введите ваше имя")])
    email = EmailField('Email', validators=[DataRequired(message="Введите email"), Email()])
    message = TextAreaField('Сообщение', validators=[
        DataRequired(message="Введите сообщение"),
        Length(min=10, message="Сообщение должно быть не менее 10 символов")
    ])
    submit = SubmitField('Отправить сообщение')

class RegistrationForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired(message="Введите ваше имя")])
    surname = StringField('Фамилия', validators=[DataRequired(message="Введите вашу фамилию")])
    email = EmailField('Email', validators=[DataRequired(message="Введите email"), Email()])
    phone = StringField('Телефон')
    password = PasswordField('Пароль', validators=[
        DataRequired(message="Введите пароль"),
        Length(min=6, message="Пароль должен быть не менее 6 символов")
    ])
    confirm_password = PasswordField('Подтвердите пароль', validators=[
        DataRequired(message="Подтвердите пароль"),
        EqualTo('password', message='Пароли должны совпадать')
    ])
    sport = SelectField('Вид спорта', choices=[
        ('', 'Выберите вид спорта'),
        ('football', 'Футбол'),
        ('basketball', 'Баскетбол'),
        ('volleyball', 'Волейбол'),
        ('hockey', 'Хоккей'),
        ('tennis', 'Теннис'),
        ('other', 'Другой')
    ], validators=[DataRequired(message="Выберите вид спорта")])
    position = StringField('Позиция / Роль')
    experience = IntegerField('Опыт (лет)', validators=[NumberRange(min=0, max=50)])
    level = SelectField('Уровень подготовки', choices=[
        ('beginner', 'Начинающий'),
        ('amateur', 'Любитель'),
        ('professional', 'Профессионал')
    ])
    city = StringField('Город', validators=[DataRequired(message="Введите город")])
    goals = SelectField('Что вы ищете?', choices=[
        ('', 'Выберите вариант'),
        ('team', 'Хочу найти человека в команду'),
        ('partner', 'Ищу напарника для тренировок'),
        ('coach', 'Ищу тренера'),
        ('participant', 'Хочу участника на мероприятия')
    ], validators=[DataRequired(message="Выберите цель")])
    about = TextAreaField('О себе', validators=[
        Length(max=500, message="Не более 500 символов")
    ])
    submit = SubmitField('Зарегистрироваться')

# ============================================
# МАРШРУТЫ
# ============================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/choice')
def choice_page():
    return render_template('volunteer_or_sport.html')

@app.route('/volunteer')
def volunteer():
    return render_template('volunteer.html', page_type='volunteer')

@app.route('/sport')
def sport():
    return render_template('find_person.html', page_type='sport')

@app.route('/find_person')
def find_person():
    users_count = 0
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        if current_user:
            if current_user.profile_type == 'seeker':
                users_count = User.query.filter_by(profile_type='volunteer').count()
            else:
                users_count = User.query.filter_by(profile_type='seeker').count()
    return render_template('find_person.html', page_type='sport', users_count=users_count)

@app.route('/register', methods=['GET', 'POST'])
@app.route('/register/<page_type>', methods=['GET', 'POST'])
def register(page_type='sport'):
    form = RegistrationForm()
    
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('❌ Пользователь с таким email уже зарегистрирован', 'error')
            return redirect(url_for('register', page_type=page_type))
        
        if page_type == 'volunteer':
            profile_type = 'volunteer'
        else:
            profile_type = 'seeker'
        
        new_user = User(
            name=form.name.data,
            surname=form.surname.data,
            email=form.email.data,
            phone=form.phone.data,
            sport=form.sport.data,
            position=form.position.data,
            experience=form.experience.data,
            level=form.level.data,
            city=form.city.data,
            goals=form.goals.data,
            about=form.about.data,
            profile_type=profile_type
        )
        
        new_user.set_password(form.password.data)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            session['user_id'] = new_user.id
            session['user_name'] = new_user.name
            session['user_email'] = new_user.email
            session['profile_type'] = profile_type
            
            flash('✅ Регистрация успешна! Добро пожаловать в систему.', 'success')
            
            if page_type == 'volunteer':
                return redirect(url_for('volunteer'))
            else:
                return redirect(url_for('find_person'))
            
        except Exception as e:
            db.session.rollback()
            flash('❌ Ошибка при регистрации. Попробуйте еще раз.', 'error')
            print(f"Ошибка: {str(e)}")
    
    return render_template('register.html', form=form, page_type=page_type)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_email'] = user.email
            session['profile_type'] = user.profile_type
            
            flash('✅ Вход выполнен успешно! Добро пожаловать!', 'success')
            return redirect(url_for('find_person'))
        else:
            flash('❌ Неверный email или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('✅ Вы вышли из системы', 'success')
    return redirect(url_for('home'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            reset_token = ResetToken(
                token=token,
                email=email,
                expires_at=expires_at
            )
            
            try:
                db.session.add(reset_token)
                db.session.commit()
                
                reset_link = f"http://localhost:5000/reset_password/{token}"
                
                flash('✅ Инструкции по восстановлению пароля отправлены на вашу почту!', 'success')
                flash(f'Для теста перейдите по ссылке: {reset_link}', 'info')
                
            except Exception as e:
                db.session.rollback()
                flash('❌ Ошибка при создании токена', 'error')
                
        else:
            flash('❌ Пользователь с таким email не найден', 'error')
        
        return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token=None):
    if request.method == 'GET' and token:
        token_data = ResetToken.query.filter_by(token=token, used=False).first()
        
        if not token_data:
            flash('❌ Неверная или устаревшая ссылка', 'error')
            return redirect(url_for('forgot_password'))
        
        if datetime.utcnow() > token_data.expires_at:
            token_data.used = True
            db.session.commit()
            flash('❌ Срок действия ссылки истек', 'error')
            return redirect(url_for('forgot_password'))
        
        return render_template('reset_password.html', token=token)
    
    elif request.method == 'POST':
        token = request.form.get('token')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not token:
            flash('❌ Неверная ссылка для сброса пароля', 'error')
            return redirect(url_for('forgot_password'))
        
        token_data = ResetToken.query.filter_by(token=token, used=False).first()
        
        if not token_data:
            flash('❌ Неверная ссылка для сброса пароля', 'error')
            return redirect(url_for('forgot_password'))
        
        if datetime.utcnow() > token_data.expires_at:
            token_data.used = True
            db.session.commit()
            flash('❌ Срок действия ссылки истек', 'error')
            return redirect(url_for('forgot_password'))
        
        if password != confirm_password:
            flash('❌ Пароли не совпадают', 'error')
            return render_template('reset_password.html', token=token)
        
        if len(password) < 6:
            flash('❌ Пароль должен быть не менее 6 символов', 'error')
            return render_template('reset_password.html', token=token)
        
        user = User.query.filter_by(email=token_data.email).first()
        if user:
            user.set_password(password)
            token_data.used = True
            
            try:
                db.session.commit()
                flash('✅ Пароль успешно изменен! Теперь вы можете войти.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash('❌ Ошибка при изменении пароля', 'error')
        else:
            flash('❌ Пользователь не найден', 'error')
    
    return redirect(url_for('forgot_password'))

@app.route('/create')
def create_redirect():
    if 'user_id' not in session:
        flash('❌ Для создания анкеты необходимо войти в систему', 'error')
        return redirect(url_for('login'))
    return redirect(url_for('create_profile'))

@app.route('/create_profile', methods=['GET', 'POST'])
def create_profile():
    if 'user_id' not in session:
        flash('❌ Для создания анкеты необходимо войти в систему', 'error')
        return redirect(url_for('login'))
    
    session['profile_type'] = 'volunteer'
    
    if request.method == 'POST':
        sport = request.form.get('sport')
        position = request.form.get('position')
        experience = request.form.get('experience')
        level = request.form.get('level')
        city = request.form.get('city')
        goals = request.form.get('goals')
        about = request.form.get('about')
        
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        if user:
            if sport:
                user.sport = sport
            if position:
                user.position = position
            if experience:
                user.experience = int(experience) if experience.isdigit() else 0
            if level:
                user.level = level
            if city:
                user.city = city
            if goals:
                user.goals = goals
            if about:
                user.about = about
            
            user.profile_type = 'volunteer'
            
            try:
                db.session.commit()
                flash('✅ Анкета успешно создана/обновлена! Теперь вас будут видеть в поиске.', 'success')
                return redirect(url_for('profile'))
            except Exception as e:
                db.session.rollback()
                flash('❌ Ошибка при сохранении анкеты', 'error')
                print(f"Ошибка: {str(e)}")
        else:
            flash('❌ Пользователь не найден', 'error')
    
    return render_template('create_profile.html', page_type='volunteer')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    
    if form.validate_on_submit():
        try:
            message = ContactMessage(
                name=form.name.data,
                email=form.email.data,
                message=form.message.data
            )
            
            db.session.add(message)
            db.session.commit()
            
            flash('✅ Ваше сообщение отправлено! Мы свяжемся с вами в ближайшее время.', 'success')
            return redirect(url_for('contact'))
            
        except Exception as e:
            db.session.rollback()
            flash('❌ Произошла ошибка при отправке сообщения. Попробуйте еще раз.', 'error')
    
    return render_template('contact.html', form=form)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('❌ Для просмотра профиля необходимо войти в систему', 'error')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        flash('❌ Пользователь не найден', 'error')
        session.clear()
        return redirect(url_for('login'))
    
    return render_template('profile.html', user=user)

@app.route('/search', methods=['GET', 'POST'])
def search_users():
    if 'user_id' not in session:
        flash('❌ Для поиска необходимо войти в систему', 'error')
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    if not current_user:
        flash('❌ Пользователь не найден', 'error')
        return redirect(url_for('login'))
    
    if current_user.profile_type == 'volunteer':
        search_profile_type = 'seeker'
        search_title = "Поиск"
    else:
        search_profile_type = 'volunteer'
        search_title = "Поиск"
    
    sport = request.args.get('sport', '')
    city = request.args.get('city', '')
    level = request.args.get('level', '')
    goals = request.args.get('goals', '')
    
    city_custom = request.args.get('city_custom', '')
    if city_custom and not city:
        city = city_custom
    
    query = User.query.filter(
        User.id != session['user_id'],
        User.profile_type == search_profile_type
    )
    
    if sport:
        query = query.filter(User.sport == sport)
    if city:
        query = query.filter(User.city.ilike(f'%{city}%'))
    if level:
        query = query.filter(User.level == level)
    if goals:
        query = query.filter(User.goals == goals)
    
    users = query.all()
    
    cities = db.session.query(User.city).filter(User.profile_type == search_profile_type).distinct().all()
    sports = db.session.query(User.sport).filter(User.profile_type == search_profile_type).distinct().all()
    
    favorite_ids = []
    if 'user_id' in session:
        favorites = Favorite.query.filter_by(user_id=session['user_id']).all()
        favorite_ids = [fav.favorite_user_id for fav in favorites]
    
    return render_template('search.html', 
                         users=users,
                         cities=[c[0] for c in cities if c[0]],
                         sports=[s[0] for s in sports if s[0]],
                         search_title=search_title,
                         current_user=current_user,
                         favorite_ids=favorite_ids,
                         search_params={
                             'sport': sport,
                             'city': city,
                             'level': level,
                             'goals': goals
                         })

@app.route('/profile/<int:user_id>')
def view_profile(user_id):
    if 'user_id' not in session:
        flash('❌ Для просмотра профилей необходимо войти в систему', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == session['user_id']:
        return redirect(url_for('profile'))
    
    is_favorite = False
    if 'user_id' in session:
        favorite = Favorite.query.filter_by(
            user_id=session['user_id'],
            favorite_user_id=user_id
        ).first()
        is_favorite = favorite is not None
    
    return render_template('view_profile.html', user=user, is_favorite=is_favorite)

# ============================================
# МАРШРУТЫ ДЛЯ ИЗБРАННОГО
# ============================================

@app.route('/favorites')
def favorites():
    if 'user_id' not in session:
        flash('❌ Для просмотра избранного необходимо войти в систему', 'error')
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    if not current_user:
        flash('❌ Пользователь не найден', 'error')
        return redirect(url_for('login'))
    
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    favorite_users = [fav.favorite_user for fav in favorites]
    
    return render_template('favorites.html', 
                         favorites=favorite_users,
                         current_user=current_user)

@app.route('/api/add_favorite/<int:user_id>', methods=['POST'])
def add_favorite(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходимо войти в систему'})
    
    current_user_id = session['user_id']
    
    if current_user_id == user_id:
        return jsonify({'success': False, 'message': 'Нельзя добавить себя в избранное'})
    
    existing = Favorite.query.filter_by(
        user_id=current_user_id, 
        favorite_user_id=user_id
    ).first()
    
    if existing:
        return jsonify({'success': False, 'message': 'Уже в избранном'})
    
    user_to_add = User.query.get(user_id)
    if not user_to_add:
        return jsonify({'success': False, 'message': 'Пользователь не найден'})
    
    new_favorite = Favorite(
        user_id=current_user_id,
        favorite_user_id=user_id
    )
    
    try:
        db.session.add(new_favorite)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Добавлено в избранное'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/api/remove_favorite/<int:user_id>', methods=['POST'])
def remove_favorite(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходимо войти в систему'})
    
    current_user_id = session['user_id']
    
    favorite = Favorite.query.filter_by(
        user_id=current_user_id, 
        favorite_user_id=user_id
    ).first()
    
    if not favorite:
        return jsonify({'success': False, 'message': 'Не найдено в избранном'})
    
    try:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Удалено из избранного'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/api/check_favorite/<int:user_id>')
def check_favorite(user_id):
    if 'user_id' not in session:
        return jsonify({'is_favorite': False})
    
    current_user_id = session['user_id']
    
    favorite = Favorite.query.filter_by(
        user_id=current_user_id,
        favorite_user_id=user_id
    ).first()
    
    return jsonify({'is_favorite': favorite is not None})

# ============================================
# НОВЫЕ МАРШРУТЫ ДЛЯ СООБЩЕНИЙ
# ============================================

@app.route('/messages')
def messages():
    """Список всех диалогов пользователя"""
    if 'user_id' not in session:
        flash('❌ Для просмотра сообщений необходимо войти в систему', 'error')
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    if not current_user:
        flash('❌ Пользователь не найден', 'error')
        return redirect(url_for('login'))
    
    # Получаем всех пользователей, с которыми был диалог
    sent_users = db.session.query(User).join(Message, Message.receiver_id == User.id).filter(Message.sender_id == current_user.id).distinct().all()
    received_users = db.session.query(User).join(Message, Message.sender_id == User.id).filter(Message.receiver_id == current_user.id).distinct().all()
    
    # Объединяем и убираем дубликаты
    all_chat_users = list(set(sent_users + received_users))
    
    # Для каждого собеседника получаем последнее сообщение и количество непрочитанных
    chats = []
    for user in all_chat_users:
        last_message = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == user.id)) |
            ((Message.sender_id == user.id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.timestamp.desc()).first()
        
        unread_count = Message.query.filter_by(
            sender_id=user.id,
            receiver_id=current_user.id,
            is_read=False
        ).count()
        
        chats.append({
            'user': user,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    # Сортируем по дате последнего сообщения (сначала новые)
    chats.sort(key=lambda x: x['last_message'].timestamp if x['last_message'] else datetime(1900, 1, 1), reverse=True)
    
    return render_template('messages.html', chats=chats, current_user=current_user)

@app.route('/messages/<int:user_id>', methods=['GET', 'POST'])
def chat(user_id):
    """Чат с конкретным пользователем"""
    if 'user_id' not in session:
        flash('❌ Для отправки сообщений необходимо войти в систему', 'error')
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    other_user = User.query.get_or_404(user_id)
    
    if current_user.id == other_user.id:
        flash('❌ Нельзя отправить сообщение самому себе', 'error')
        return redirect(url_for('messages'))
    
    # Обработка отправки сообщения
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            message = Message(
                sender_id=current_user.id,
                receiver_id=other_user.id,
                content=content
            )
            try:
                db.session.add(message)
                db.session.commit()
                flash('✅ Сообщение отправлено!', 'success')
            except Exception as e:
                db.session.rollback()
                flash('❌ Ошибка при отправке сообщения', 'error')
                print(f"Ошибка: {str(e)}")
        else:
            flash('❌ Сообщение не может быть пустым', 'error')
        
        return redirect(url_for('chat', user_id=user_id))
    
    # Получаем все сообщения между пользователями
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == other_user.id)) |
        ((Message.sender_id == other_user.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    
    # Отмечаем все непрочитанные сообщения как прочитанные
    unread_messages = Message.query.filter_by(
        sender_id=other_user.id,
        receiver_id=current_user.id,
        is_read=False
    ).all()
    
    for msg in unread_messages:
        msg.is_read = True
    
    if unread_messages:
        db.session.commit()
    
    return render_template('chat.html', 
                         messages=messages, 
                         current_user=current_user, 
                         other_user=other_user)

@app.route('/api/unread_count')
def unread_count():
    """API для получения количества непрочитанных сообщений"""
    if 'user_id' not in session:
        return jsonify({'count': 0})
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'count': 0})
    
    count = user.unread_messages_count()
    return jsonify({'count': count})

@app.route('/api/send_message/<int:user_id>', methods=['POST'])
def api_send_message(user_id):
    """API для отправки сообщения (для AJAX)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходимо войти в систему'})
    
    current_user_id = session['user_id']
    if current_user_id == user_id:
        return jsonify({'success': False, 'message': 'Нельзя отправить сообщение самому себе'})
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'success': False, 'message': 'Сообщение не может быть пустым'})
    
    message = Message(
        sender_id=current_user_id,
        receiver_id=user_id,
        content=content
    )
    
    try:
        db.session.add(message)
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Сообщение отправлено',
            'data': {
                'id': message.id,
                'content': message.content,
                'timestamp': message.formatted_time()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/admin/users')
def admin_users():
    users = User.query.all()
    result = []
    for user in users:
        result.append({
            'id': user.id,
            'name': user.name,
            'surname': user.surname,
            'email': user.email,
            'city': user.city,
            'sport': user.sport,
            'profile_type': user.profile_type,
            'about': user.about[:100] + '...' if user.about else ''
        })
    return {'users': result}

# ============================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Создаем тестовых пользователей, если их нет
        if not User.query.filter_by(email='ignatic@yandex.com').first():
            test_user = User(
                name='Игнат',
                surname='Васильев',
                email='ignatic@yandex.com',
                phone='+7 (911) 913-76-67',
                sport='football',
                position='Нападающий',
                city='Москва',
                goals='team',
                experience=5,
                level='amateur',
                about='Люблю футбол с детства, играю на позиции нападающего. Участвовал в городских соревнованиях.',
                profile_type='seeker'
            )
            test_user.set_password('123456')
            db.session.add(test_user)
            
            test_users = [
                User(name='Алексей', surname='Иванов', email='alexiz@mail.com', city='Москва',
                     sport='football', position='Защитник', experience=5, level='amateur',
                     goals='team', phone='+7 (903) 187-21-09', 
                     about='Играю в футбол с 10 лет. Ответственный, дисциплинированный, люблю командную игру.',
                     profile_type='volunteer'),
                
                User(name='Мария', surname='Петрова', email='mariar@gmail.com', city='Санкт-Петербург',
                     sport='tennis', position=None, experience=3, level='beginner',
                     goals='partner', phone='+7 (956) 578-23-89',
                     about='Начинающая теннисистка, ищу партнера для совместных тренировок.',
                     profile_type='seeker'),
                
                User(name='Дмитрий', surname='Сидоров', email='dmitryf@mail.com', city='Москва',
                     sport='basketball', position='Защитник', experience=8, level='professional',
                     goals='team', phone='+79993562901',
                     about='Профессиональный баскетболист, ищу команду для участия в чемпионате.',
                     profile_type='volunteer'),
                
                User(name='Анна', surname='Смирнова', email='annasmirna@yandex.com', city='Казань',
                     sport='volleyball', position='Связующий', experience=2, level='beginner',
                     goals='participant', phone='+79035672098',
                     about='Ищу участников для волейбольного турнира среди любителей.',
                     profile_type='seeker'),
                
                User(name='Иван', surname='Кузнецов', email='ivanovic@mail.com', city='Новосибирск',
                     sport='hockey', position='Вратарь', experience=10, level='professional',
                     goals='coach', phone='+79560982134',
                     about='Опытный хоккеист, ищу тренера для подготовки к профессиональным соревнованиям.',
                     profile_type='volunteer'),
            ]
            
            for user in test_users:
                existing = User.query.filter_by(email=user.email).first()
                if not existing:
                    user.set_password('123456')
                    db.session.add(user)
            
            # Создаем тестовые сообщения
            db.session.commit()
            
            # Получаем пользователей для создания тестовых сообщений
            user1 = User.query.filter_by(email='ignatic@yandex.com').first()
            user2 = User.query.filter_by(email='alexiz@mail.com').first()
            user3 = User.query.filter_by(email='mariar@gmail.com').first()
            
            if user1 and user2 and not Message.query.first():
                # Создаем несколько тестовых сообщений
                messages = [
                    Message(sender_id=user1.id, receiver_id=user2.id, content='Привет! Ищешь команду?', is_read=True),
                    Message(sender_id=user2.id, receiver_id=user1.id, content='Да, я защитник, ищу команду в Москве', is_read=True),
                    Message(sender_id=user1.id, receiver_id=user2.id, content='Отлично! У нас как раз есть место. Можем обсудить детали.', is_read=False),
                    Message(sender_id=user1.id, receiver_id=user3.id, content='Мария, привет! Интересует теннис?', is_read=False),
                ]
                
                for msg in messages:
                    db.session.add(msg)
                
                db.session.commit()
            
            print("=" * 50)
            print("Созданы тестовые пользователи:")
            print("1. ignatic@yandex.com / 123456 (ищет спортсменов)")
            print("2. alexiz@mail.com / 123456 (ищет команду)")
            print("3. mariar@gmail.com / 123456 (ищет спортсменов)")
            print("4. dmitryf@mail.com / 123456 (ищет команду)")
            print("5. annasmirna@yandex.com / 123456 (ищет спортсменов)")
            print("6. ivanovic@mail.com / 123456 (ищет команду)")
            print("=" * 50)
            print("✅ Созданы тестовые сообщения между пользователями!")
    
    app.run(debug=True, port=5000)