# Импортируем необходимые классы из Flask
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, abort, current_app # Добавляем current_app
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

# --- НАЧАЛО НОВОГО КОДА: Импорты для файлов и извлечения текста (Шаг 26) ---
from werkzeug.utils import secure_filename # Для безопасного получения имени файла
import fitz # PyMuPDF для PDF
from docx import Document # python-docx для DOCX (внимательно: Docx с большой буквы!)
import io # Для работы с файлами в памяти
# --- КОНЕЦ НОВОГО КОДА: Импорты для файлов и извлечения текста (Шаг 26) ---


# Создаем экземпляр приложения Flask
app = Flask(__name__)

# --- НАСТРОЙКА SECRET_KEY (Шаг 19) ---
app.config['SECRET_KEY'] = 'xgj6_6mu,_j7kem_5_e5h7_ko69;_c25vl_vbj6_m,,l' # >>> ОБЯЗАТЕЛЬНО ЗАМЕНИ НА СВОЮ <<<
# --- КОНЕЦ НАСТРОЙКИ SECRET_KEY ---

# --- НАСТРОЙКА ПАПКИ ЗАГРУЗКИ (НОВОЕ для Шага 26) ---
# Определяем папку для временного хранения загруженных файлов, если нужно
# Для MVP мы можем извлекать текст прямо из памяти без сохранения, но для полноты оставим
# app.config['UPLOAD_FOLDER'] = 'uploads' # Пример настройки папки
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True) # Создаем папку, если ее нет
# --- КОНЕЦ НАСТРОЙКИ ПАПКИ ЗАГРУЗКИ ---


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


# --- КОД ДЛЯ МОДЕЛИ ВАКАНСИИ (Шаг 21, ИЗМЕНЕНО в Шаге 25) ---
class Vacancy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # --- Связь с кандидатами (Шаг 25) ---
    candidates = db.relationship('Candidate', backref='vacancy', lazy=True, cascade='all, delete-orphan')
    # --- Конец Связи с кандидатами (Шаг 25) ---


    def __repr__(self):
        return f"Vacancy('{self.title}', '{self.created_at}')"
# --- КОНЕЦ КОДА ДЛЯ МОДЕЛИ ВАКАНСИИ (Шаг 21, ИЗМЕНЕНО) ---


# --- КОД ДЛЯ МОДЕЛИ КАНДИДАТА (Шаг 25) ---
class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vacancy_id = db.Column(db.Integer, db.ForeignKey('vacancy.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(255), nullable=True) # Путь, где хранится файл (опционально)
    extracted_text = db.Column(db.Text, nullable=True) # Извлеченный текст резюме

    ai_score = db.Column(db.Float, nullable=True)
    keywords = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='uploaded') # Статус обработки

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"Candidate('{self.original_filename}', VacancyID:{self.vacancy_id}, Status:'{self.status}')"
# --- КОНЕЦ КОДА ДЛЯ МОДЕЛИ КАНДИДАТА (Шаг 25) ---


# --- НАЧАЛО НОВОГО КОДА: Функции извлечения текста (Шаг 26) ---
def extract_text_from_pdf(pdf_content):
    """Извлекает текст из PDF-файла."""
    text = ""
    try:
        # fitz.open требует либо путь к файлу, либо объект BytesIO
        # Используем BytesIO для чтения из памяти
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Ошибка при извлечении текста из PDF: {e}")
        text = None # Возвращаем None или пустую строку в случае ошибки
    return text

def extract_text_from_docx(docx_content):
    """Извлекает текст из DOCX-файла."""
    text = ""
    try:
        # Document требует либо путь к файлу, либо объект файлового потока
        # Используем BytesIO для чтения из памяти
        doc = Document(io.BytesIO(docx_content))
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n" # Добавляем перенос строки после каждого параграфа
    except Exception as e:
        print(f"Ошибка при извлечении текста из DOCX: {e}")
        text = None # Возвращаем None или пустую строку в случае ошибки
    return text

def get_file_extension(filename):
    """Возвращает расширение файла в нижнем регистре."""
    return os.path.splitext(filename)[1].lower()
# --- КОНЕЦ НОВОГО КОДА: Функции извлечения текста (Шаг 26) ---


# Маршрут для отображения главной страницы
@app.route('/')
def index():
     if current_user.is_authenticated:
         flash(f'Привет, {current_user.email}!', 'success')
     return render_template('index.html', user=current_user)


# Маршрут Списка Вакансий (Шаг 23)
@app.route('/jobs')
@login_required
def list_jobs():
    user_vacancies = current_user.vacancies # Вакансии уже отсортированы по дате создания по умолчанию

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
        return redirect(url_for('list_jobs'))

    return render_template('create_job.html', user=current_user)


# Маршрут для просмотра деталей конкретной вакансии (Шаг 24)
@app.route('/jobs/<int:job_id>')
@login_required
def view_job(job_id):
    job = Vacancy.query.get_or_404(job_id)

    # ВАЖНАЯ ПРОВЕРКА: Убеждаемся, что текущий пользователь является автором этой вакансии
    if job.user_id != current_user.id:
        abort(403) # 403 Forbidden

    # TODO: СЮДА ПОЗЖЕ ПОЛУЧАТЬ И ПЕРЕДАВАТЬ В ШАБЛОН СПИСОК КАНДИДАТОВ для этой вакансии
    # Например: candidates = job.candidates # Благодаря relation в Vacancy
    # return render_template('view_job.html', job=job, user=current_user, candidates=candidates)

    # Временно передаем только job и user
    return render_template('view_job.html', job=job, user=current_user)


# --- НАЧАЛО НОВОГО КОДА: Маршрут Загрузки Резюме (Шаг 26) ---
# Маршрут для загрузки резюме для конкретной вакансии
@app.route('/jobs/<int:job_id>/upload_resume', methods=['POST'])
@login_required # Только авторизованные пользователи могут загружать
def upload_resume(job_id):
    # Находим вакансию по ID (ту же логику, что и в view_job)
    job = Vacancy.query.get_or_404(job_id)

    # ВАЖНАЯ ПРОВЕРКА: Убеждаемся, что текущий пользователь является автором этой вакансии
    if job.user_id != current_user.id:
        abort(403) # 403 Forbidden - Нельзя загружать резюме для чужой вакансии

    # Проверяем, был ли файл вообще отправлен в запросе
    if 'resume_file' not in request.files:
        flash('Файл не был выбран.', 'error')
        return redirect(url_for('view_job', job_id=job.id))

    file = request.files['resume_file']

    # Если пользователь не выбрал файл и форма пуста
    if file.filename == '':
        flash('Файл не был выбран.', 'error')
        return redirect(url_for('view_job', job_id=job.id))

    # Проверяем расширение файла
    original_filename = secure_filename(file.filename) # Безопасно получаем имя файла
    file_extension = get_file_extension(original_filename)

    # Проверяем, поддерживается ли формат файла
    if file_extension not in ['.pdf', '.docx']:
        flash('Неподдерживаемый формат файла. Разрешены только .pdf и .docx.', 'error')
        return redirect(url_for('view_job', job_id=job.id))

    # --- Извлечение текста из файла ---
    extracted_text = None
    file_content = file.read() # Читаем содержимое файла в байты

    if file_extension == '.pdf':
        extracted_text = extract_text_from_pdf(file_content)
    elif file_extension == '.docx':
        extracted_text = extract_text_from_docx(file_content)

    # Проверяем, успешно ли извлечен текст
    if not extracted_text or len(extracted_text.strip()) == 0:
        flash(f'Не удалось извлечь текст из файла {original_filename}.', 'error')
        # !!! TODO: Логировать ошибку извлечения текста !!!
        # В реальном приложении можно сохранить файл и попробовать позже или уведомить пользователя
        return redirect(url_for('view_job', job_id=job.id))

    # --- Сохранение кандидата в базу данных ---
    # !!! TODO: Проверить на дубликаты по имени файла и вакансии, или добавить UUID !!!

    new_candidate = Candidate(
        vacancy_id=job.id, # Связываем кандидата с текущей вакансией
        original_filename=original_filename,
        extracted_text=extracted_text,
        # storage_path= # TODO: Если нужно сохранять сам файл, указать путь
        status='uploaded' # Начальный статус
        # ai_score, keywords пока NULL
    )

    db.session.add(new_candidate)
    db.session.commit()

    flash(f'Резюме "{original_filename}" успешно загружено и текст извлечен!', 'success')

    # !!! TODO: ТУТ ДОЛЖЕН ЗАПУСТИТЬСЯ ПРОЦЕСС AI-СКРИНИНГА ДЛЯ ЭТОГО КАНДИДАТА !!!

    return redirect(url_for('view_job', job_id=job.id)) # Перенаправляем обратно на страницу деталей вакансии
# --- КОНЕЦ НОВОГО КОДА: Маршрут Загрузки Резюме (Шаг 26) ---


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
            return redirect(url_for('list_jobs')) # Перенаправляем на список вакансий после входа

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
    # База данных уже создана на шаге 18.2 (или пересоздана на шаге 21.2, 25.2)
    app.run(debug=True, host='0.0.0.0', port=5000)