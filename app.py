# Импортируем необходимые классы из Flask
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, abort # Добавляем abort
# Импортируем библиотеку os для работы с переменными окружения
import os
# --- КОД ДЛЯ БАЗЫ ДАННЫХ (Шаг 18) ---
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
# --- КОНЕЦ КОДА ДЛЯ БАЗЫ ДАННЫХ (Шаг 18) ---

# --- КОД: Flask-Login (Шаг 20) ---
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# --- КОНЕЦ КОДА: Flask-Login (Шаг 20) ---

# Создаем экземпляр приложения Flask
app = Flask(__name__)

# --- НАСТРОЙКА SECRET_KEY (Шаг 19) ---
app.config['SECRET_KEY'] = 'ggn_grgsn_nt_gen_bnmy5_bsy_,,,_vdgtn_b5k' # >>> ОБЯЗАТЕЛЬНО ЗАМЕНИ НА СВОЮ <<<
# --- КОНЕЦ НАСТРОЙКИ SECRET_KEY ---


# --- КОД ДЛЯ БАЗЫ ДАННЫХ (Шаг 18) ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# --- КОНЕЦ КОДА ДЛЯ БАЗЫ ДАННЫХ (Шаг 18) ---

# --- КОД: Flask-Login (Шаг 20) ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Пожалуйста, войдите, чтобы получить доступ к этой странице.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# --- КОНЕЦ КОДА: Flask-Login (Шаг 20) ---


# --- КОД ДЛЯ МОДЕЛИ ПОЛЬЗОВАТЕЛЯ (Шаг 18, ИЗМЕНЕНО в Шаге 20, 21) ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # --- Связь с вакансиями (Шаг 21, ИЗМЕНЕНО в Шаге 23) ---
    vacancies = db.relationship('Vacancy', backref='author', lazy=True, order_by="Vacancy.created_at.desc()")
    # --- Конец Связи с вакансиями (Шаг 21, ИЗМЕНЕНО) ---

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"User('{self.email}')"

# --- КОНЕЦ КОДА ДЛЯ МОДЕЛИ ПОЛЬЗОВАТЕЛЯ (Шаг 18, ИЗМЕНЕНО) ---


# --- КОД ДЛЯ МОДЕЛИ ВАКАНСИИ (Шаг 21) ---
class Vacancy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # --- Внешний ключ для связи с пользователем ---
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # --- Конец Внешнего ключа ---

    # !!! TODO: СЮДА ПОЗЖЕ ДОБАВИТЬ СВЯЗЬ С КАНДИДАТАМИ (Шаг 21) !!!

    def __repr__(self):
        return f"Vacancy('{self.title}', '{self.created_at}')"
# --- КОНЕЦ КОДА ДЛЯ МОДЕЛИ ВАКАНСИИ (Шаг 21) ---


# Маршрут для отображения главной страницы
@app.route('/')
def index():
     # Если пользователь авторизован, можно показать приветствие и ссылку на его вакансии
     if current_user.is_authenticated:
         flash(f'Привет, {current_user.email}!', 'success') # Пример приветствия
         # TODO: Добавить ссылку на список вакансий в index.html - Сделано в Шаге 23.3
     return render_template('index.html', user=current_user)


# Маршрут Списка Вакансий (Шаг 23)
@app.route('/jobs')
@login_required # Только авторизованные пользователи могут видеть список
def list_jobs():
    # Получаем ВСЕ вакансии текущего пользователя, отсортированные по дате создания (см. модель User relationship)
    user_vacancies = current_user.vacancies # Благодаря relationship и order_by в модели User

    # Передаем список вакансий в шаблон
    return render_template('list_jobs.html', jobs=user_vacancies, user=current_user)


# Маршрут для Создания Вакансии (Шаг 22)
@app.route('/jobs/create', methods=['GET', 'POST'])
@login_required
def create_job():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')

        if not title or not description:
            flash('Пожалуйста, заполните название и описание вакансии.', 'error')
            return render_template('create_job.html', user=current_user)

        new_job = Vacancy(
            title=title,
            description=description,
            user_id=current_user.id
        )

        db.session.add(new_job)
        db.session.commit()

        flash('Вакансия успешно создана!', 'success')
        # Перенаправляем на страницу списка вакансий после создания
        return redirect(url_for('list_jobs'))

    return render_template('create_job.html', user=current_user)


# --- НАЧАЛО НОВОГО КОДА: Маршрут Деталей Вакансии (Шаг 24) ---
# Маршрут для просмотра деталей конкретной вакансии
# <int:job_id> - означает, что часть URL будет целым числом (ID вакансии)
@app.route('/jobs/<int:job_id>')
@login_required # Только авторизованные пользователи могут видеть детали
def view_job(job_id):
    # Находим вакансию по ID. get_or_404() автоматически вернет страницу 404 Not Found,
    # если вакансия с таким ID не существует.
    job = Vacancy.query.get_or_404(job_id)

    # !!! ВАЖНАЯ ПРОВЕРКА: Убеждаемся, что текущий пользователь является автором этой вакансии !!!
    # Это нужно, чтобы пользователь не мог посмотреть вакансии других пользователей,
    # просто подставив другой ID в адресную строку.
    if job.user_id != current_user.id:
        # Если пользователь не является автором, возвращаем ошибку 403 Forbidden (Запрещено)
        # Необходимо импортировать abort из flask
        abort(403) # Или можно перенаправить куда-то, или показать сообщение об ошибке

    # Передаем найденный объект вакансии в шаблон для отображения
    return render_template('view_job.html', job=job, user=current_user)
# --- КОНЕЦ НОВОГО КОДА: Маршрут Деталей Вакансии (Шаг 24) ---


# Маршрут для РЕГИСТРАЦИИ (Шаг 19)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('Вы уже вошли в систему.', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not email or not password or not confirm_password:
            flash('Пожалуйста, заполните все поля.', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Пароли не совпадают!', 'error')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Пользователь с таким email уже существует.', 'error')
            return redirect(url_for('register'))

        new_user = User(email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Учетная запись успешно создана! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# Маршрут для ВХОДА (LOGIN) (Шаг 20)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('Вы уже вошли в систему.', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            # Перенаправляем на страницу списка вакансий после входа
            return redirect(url_for('list_jobs'))

        else:
            flash('Неверный email или пароль.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


# Маршрут для ВЫХОДА (LOGOUT) (Шаг 20)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'success')
    return redirect(url_for('index'))


# Маршрут для обработки данных от фронтенда (резюме и вакансия) - пока остается как было
# TODO: Этот маршрут должен быть доступен ТОЛЬКО авторизованным HR-пользователям!
@app.route('/greet', methods=['POST'])
# @login_required # Раскомментировать, когда логин будет готов и протестирован
def greet():
    if not request.json:
        return jsonify({"error": "Request must be JSON"}), 415

    resume_text = request.json.get('resume_text')
    job_description_text = request.json.get('job_description_text')

    if not resume_text or not job_description_text:
        return jsonify({"error": "Resume text and job description text are required"}), 400

    ai_api_key = os.environ.get('AI_API_KEY')
    key_status = "set" if ai_api_key else "not set"
    if not ai_api_key:
        pass # print("Ошибка: Переменная окружения 'AI_API_KEY' не установлена!")

    # !!! ВНИМАНИЕ: СЮДА ПОЗЖЕ БУДЕТ ДОБАВЛЕН КОД ДЛЯ ВЫЗОВА AI API !!!

    response_data = {
        "status": "success",
        "message": "Данные получены бэкендом. Подготовлена база данных и регистрация.",
        "api_key_status": key_status,
        "received_resume_length": len(resume_text),
        "received_job_description_length": len(job_description_text)
    }

    return jsonify(response_data)


# Этот блок запускает веб-сервер Flask для локальной разработки
if __name__ == '__main__':
    # База данных уже создана на шаге 18.2 (или пересоздана на шаге 21.2)
    app.run(debug=True, host='0.0.0.0', port=5000)