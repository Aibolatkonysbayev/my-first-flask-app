# Импортируем необходимые классы из Flask
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
# Импортируем библиотеку os для работы с переменными окружения
import os
# --- КОД ДЛЯ БАЗЫ ДАННЫХ (Шаг 18) ---
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
# --- КОНЕЦ КОДА ДЛЯ БАЗЫ ДАННЫХ (Шаг 18) ---

# --- НОВЫЙ КОД: Flask-Login (Шаг 20) ---
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# --- КОНЕЦ НОВОГО КОДА: Flask-Login (Шаг 20) ---

# Создаем экземпляр приложения Flask
app = Flask(__name__)

# --- НАСТРОЙКА SECRET_KEY (Шаг 19) ---
# Секретный ключ нужен для безопасности сессий и сообщений flash.
# В продакшене нужно брать его из переменной окружения!
# Например: app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
# Для локальной разработки пока зададим прямо здесь:
app.config['SECRET_KEY'] = 'bty_yoiot5_xnr66_t_vg34_5vrui_zcnuk_3f43hl_9v47' # >>> ОБЯЗАТЕЛЬНО ЗАМЕНИ НА СВОЮ <<<
# --- КОНЕЦ НАСТРОЙКИ SECRET_KEY ---


# --- КОД ДЛЯ БАЗЫ ДАННЫХ (Шаг 18) ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# --- КОНЕЦ КОДА ДЛЯ БАЗЫ ДАННЫХ (Шаг 18) ---

# --- НАЧАЛО КОДА: Flask-Login (Шаг 20) ---
# Инициализируем LoginManager
login_manager = LoginManager()
# Связываем LoginManager с приложением Flask
login_manager.init_app(app)
# Указываем страницу входа (Flask-Login будет перенаправлять туда неавторизованных пользователей)
login_manager.login_view = 'login'
# Сообщение, которое показывается при перенаправлении на страницу входа (можно настроить)
login_manager.login_message_category = 'info'
login_manager.login_message = 'Пожалуйста, войдите, чтобы получить доступ к этой странице.'

# Функция, которую Flask-Login использует для загрузки пользователя по его ID из сессии
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) # Возвращаем объект пользователя или None
# --- КОНЕЦ КОДА: Flask-Login (Шаг 20) ---


# --- КОД ДЛЯ МОДЕЛИ ПОЛЬЗОВАТЕЛЯ (Шаг 18) ---
# !!! ИЗМЕНЕНИЕ: Класс User теперь наследует от UserMixin для работы с Flask-Login !!!
class User(db.Model, UserMixin): # <--- НАСЛЕДУЕМ ОТ UserMixin
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Методы set_password и check_password остаются без изменений
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"User('{self.email}', '{self.created_at}')"

    # !!! Дополнительный метод для Flask-Login (опционально, но полезно) !!!
    # Flask-Login использует свойство is_authenticated и другие, которые UserMixin предоставляет.
    # Если бы мы не наследовали от UserMixin, нам бы пришлось реализовать их самим.
# --- КОНЕЦ КОДА ДЛЯ МОДЕЛИ ПОЛЬЗОВАТЕЛЯ (Шаг 18, ИЗМЕНЕНО) ---


# Маршрут для отображения главной страницы (остается без изменений)
# Теперь можно добавить декоратор @login_required, чтобы только авторизованные могли видеть главную
# @app.route('/')
# @login_required # Сделаем главную страницу доступной только после входа
# def index():
#    # Можно передавать в шаблон информацию о текущем пользователе: current_user.email
#    return render_template('index.html', user=current_user)

# Временно оставим главную страницу без @login_required для удобства навигации во время разработки
@app.route('/')
def index():
     # current_user доступен даже если пользователь не авторизован (он будет анонимным объектом)
     return render_template('index.html', user=current_user)


# Маршрут для РЕГИСТРАЦИИ (Шаг 19, остается без изменений, кроме перенаправления)
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Если пользователь уже авторизован, перенаправляем его куда-то (например, на главную)
    if current_user.is_authenticated:
        flash('Вы уже вошли в систему.', 'info')
        return redirect(url_for('index')) # Перенаправить на главную, если уже вошел

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
        return redirect(url_for('login')) # <<< ИЗМЕНЕНИЕ: ПЕРЕНАПРАВЛЯЕМ НА СТРАНИЦУ ВХОДА /login

    return render_template('register.html')
# --- КОНЕЦ МАРШРУТА ДЛЯ РЕГИСТРАЦИИ (Шаг 19, ИЗМЕНЕНО) ---


# --- НАЧАЛО НОВОГО МАРШРУТА ДЛЯ ВХОДА (LOGIN) (Шаг 20) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем его куда-то (например, на главную)
    if current_user.is_authenticated:
        flash('Вы уже вошли в систему.', 'info')
        return redirect(url_for('index')) # Перенаправить на главную, если уже вошел

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # checkbox_remember = request.form.get('remember_me') # Если бы была галочка "Запомнить меня"

        user = User.query.filter_by(email=email).first() # Ищем пользователя в БД по email

        # Проверяем, найден ли пользователь И правильный ли пароль
        if user and user.check_password(password):
            # Если пользователь найден и пароль совпал:
            login_user(user) # Логиним пользователя с помощью Flask-Login (записываем ID в сессию)
            # next_page = request.args.get('next') # Можно получить URL, куда хотел попасть пользователь до логина
            flash('Вы успешно вошли в систему!', 'success')
            # Перенаправляем пользователя после успешного входа (сейчас на главную)
            # return redirect(next_page or url_for('index')) # Перенаправить на запрашиваемую страницу или главную
            return redirect(url_for('index')) # Пока просто перенаправляем на главную

        else:
            # Если пользователь не найден или пароль неверный
            flash('Неверный email или пароль.', 'error')
            return redirect(url_for('login')) # Перенаправляем обратно на страницу входа

    # Отображение формы входа при GET-запросе
    return render_template('login.html')
# --- КОНЕЦ НОВОГО МАРШРУТА ДЛЯ ВХОДА (LOGIN) (Шаг 20) ---


# --- НАЧАЛО НОВОГО МАРШРУТА ДЛЯ ВЫХОДА (LOGOUT) (Шаг 20) ---
@app.route('/logout')
@login_required # Этот маршрут доступен только авторизованным пользователям
def logout():
    logout_user() # Вылогиниваем пользователя с помощью Flask-Login (удаляем ID из сессии)
    flash('Вы вышли из системы.', 'success')
    return redirect(url_for('index')) # Перенаправляем на главную или страницу входа после выхода
# --- КОНЕЦ НОВОГО МАРШРУТА ДЛЯ ВЫХОДА (LOGOUT) (Шаг 20) ---


# Маршрут для обработки данных от фронтенда (резюме и вакансия) - пока остается как было
# TODO: Этот маршрут должен быть доступен ТОЛЬКО авторизованным HR-пользователям!
@app.route('/greet', methods=['POST'])
# @login_required # Раскомментировать, когда логин будет готов и протестирован
def greet():
    # ... (остальная часть функции greet без изменений) ...
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
        "message": "Данные получены бэкендом. Подготовлена база данных и регистрация.", # Обновляем сообщение
        "api_key_status": key_status,
        "received_resume_length": len(resume_text),
        "received_job_description_length": len(job_description_text)
    }

    return jsonify(response_data)


# Этот блок запускает веб-сервер Flask для локальной разработки
if __name__ == '__main__':
    # База данных уже создана на шаге 18.2
    # Теперь просто запускаем сервер.
    app.run(debug=True, host='0.0.0.0', port=5000)