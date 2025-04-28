# Импортируем необходимые классы из Flask
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, abort, current_app, send_from_directory
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

# --- КОД: Импорты для файлов и извлечения текста (Шаг 26) ---
from werkzeug.utils import secure_filename
import fitz # PyMuPDF для PDF
from docx import Document # python-docx для DOCX
import io
# --- КОНЕЦ КОДА: Импорты для файлов и извлечения текста (Шаг 26) ---

# --- КОД: Импорт для AI (Шаг 27) ---
import openai
from openai import OpenAI, APIStatusError, APIConnectionError, RateLimitError # Импорты ошибок для v1.0.0+
import json # Может пригодиться для работы с JSON ответами от API
# --- КОНЕЦ КОДА: Импорт для AI (Шаг 27) ---


# Создаем экземпляр приложения Flask
app = Flask(__name__)

# --- НАСТРОЙКА SECRET_KEY (Шаг 19) ---
app.config['SECRET_KEY'] = 'xgj6_6mu,_j7kem_5_e5h7_ko69;_c25vl_vbj6_m,,l' # >>> ОБЯЗАТЕЛЬНО ЗАМЕНИ НА СВОЮ <<<
# --- КОНЕЦ НАСТРОЙКИ SECRET_KEY ---


# --- НАЧАЛО КОДА: Конфигурация Папки Загрузки (Шаг 29.1) ---
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# --- КОНЕЦ КОДА: Конфигурация Папки Загрузки (Шаг 29.1) ---


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

# --- НАЧАЛО НОВОГО КОДА: Фильтр Jinja для JSON (Шаг 28.1) ---
# Регистрируем фильтр from_json для шаблонов Jinja2
@app.template_filter('from_json')
def from_json_filter(json_string):
    if isinstance(json_string, str):
        try:
            return json.loads(json_string)
        except (json.JSONDecodeError, TypeError):
            return None
    return json_string
# --- КОНЕЦ НОВОГО КОДА: Фильтр Jinja для JSON (Шаг 28.1) ---


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

    # --- Связь с кандидатами (Шаг 25, ИЗМЕНЕНО в Шаге 25) ---
    candidates = db.relationship('Candidate', backref='vacancy', lazy=True, cascade='all, delete-orphan', order_by="Candidate.created_at.desc()")
    # --- Конец Связи с кандидатами (Шаг 25, ИЗМЕНЕНО) ---


    def __repr__(self):
        return f"Vacancy('{self.title}', '{self.created_at}')"
# --- КОНЕЦ КОДА ДЛЯ МОДЕЛИ ВАКАНСИИ (Шаг 21, ИЗМЕНЕНО) ---


# --- КОД ДЛЯ МОДЕЛИ КАНДИДАТА (Шаг 25) ---
class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vacancy_id = db.Column(db.Integer, db.ForeignKey('vacancy.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(255), nullable=True)
    extracted_text = db.Column(db.Text, nullable=True)

    ai_score = db.Column(db.Float, nullable=True)
    keywords = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='uploaded')

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"Candidate('{self.original_filename}', VacancyID:{self.vacancy_id}, Status:'{self.status}')"
# --- КОНЕЦ КОДА ДЛЯ МОДЕЛИ КАНДИДАТА (Шаг 25) ---


# --- КОД: Функции извлечения текста (Шаг 26) ---
def extract_text_from_pdf(pdf_content):
    """Извлекает текст из PDF-файла."""
    text = ""
    try:
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Ошибка при извлечении текста из PDF: {e}")
        text = None
    return text

def extract_text_from_docx(docx_content):
    """Извлекает текст из DOCX-файла."""
    text = ""
    try:
        doc = Document(io.BytesIO(docx_content))
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Ошибка при извлечении текста из DOCX: {e}")
        text = None
    return text

def get_file_extension(filename):
    """Возвращает расширение файла в нижнем регистре."""
    return os.path.splitext(filename)[1].lower()
# --- КОНЕЦ КОДА: Функции извлечения текста (Шаг 26) ---


# --- КОД: Функция AI Скрининга (Шаг 27 - ИСПРАВЛЕНО для openai v1.0.0+) ---
# Создаем клиент OpenAI здесь (один раз)
# Ключ API берется из переменной окружения AI_API_KEY автоматически при инициализации клиента
try:
    ai_client = OpenAI(api_key=os.environ.get('AI_API_KEY'))
    print("OpenAI клиент инициализирован. Ключ API найден." if os.environ.get('AI_API_KEY') else "OpenAI клиент инициализирован. Ключ API НЕ найден.")
except Exception as e:
     ai_client = None
     print(f"Ошибка инициализации OpenAI клиента: {e}")
     print("AI Screening будет недоступен.")


def perform_ai_screening(candidate_id):
    """Выполняет AI-скрининг для заданного кандидата."""
    # Важно получить кандидата в текущем контексте
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or not candidate.extracted_text:
        print(f"AI Screening: Кандидат с ID {candidate_id} не найден или текст не извлечен.")
        return

    if candidate.status == 'processing':
        print(f"AI Screening: Кандидат ID {candidate_id} уже в процессе обработки.")
        return # Не запускаем повторно

    candidate.status = 'processing'
    db.session.commit() # Сохраняем статус "в процессе"

    job = candidate.vacancy
    if not job:
        print(f"AI Screening: Вакансия для кандидата {candidate.id} не найдена через связь.")
        candidate.status = 'failed_ai_novacancy'
        db.session.commit()
        return

    job_description = job.description
    resume_text = candidate.extracted_text

    if not ai_client:
        print(f"AI Screening: Клиент OpenAI не инициализирован (нет ключа). Кандидат ID {candidate_id} обработан не будет.")
        candidate = db.session.get(Candidate, candidate.id) # Получаем объект еще раз в новой сессии, если commit был ранее
        if candidate:
            candidate.status = 'failed_ai_nokey'
            db.session.commit()
        return

    # --- Формируем промпт для AI модели ---
    prompt_messages = [
        {"role": "system", "content": "Ты опытный рекрутер, специализирующийся на подборе персонала. Твоя задача - сравнить предоставленное резюме кандидата с описанием вакансии и оценить релевантность в процентах (от 0 до 100%). Также выдели ключевые навыки и опыт кандидата, которые соответствуют требованиям вакансии. Предоставь ответ строго в формате JSON с полями `relevance_score` (целое число) и `matching_keywords` (список строк)."},
        {"role": "user", "content": f"Описание Вакансии:\n---\n{job_description}\n---\n\nРезюме Кандидата:\n---\n{resume_text}\n---\n"},
    ]

    # --- Вызов AI API (OpenAI) - ИСПРАВЛЕНО для openai v1.0.0+ ---
    try:
        response = ai_client.chat.completions.create(
            model="gpt-3.5-turbo", # или "gpt-4", "gpt-4-turbo-preview"
            messages=prompt_messages,
            temperature=0.0,
            max_tokens=500,
        )

        ai_output_text = response.choices[0].message.content
        print(f"AI Response Text for Candidate {candidate.id}: {ai_output_text}")

        ai_result = json.loads(ai_output_text)

        score = ai_result.get('relevance_score')
        keywords = ai_result.get('matching_keywords')

        if isinstance(score, (int, float)) and 0 <= score <= 100:
            candidate.ai_score = float(score)
            candidate.keywords = json.dumps(keywords) if isinstance(keywords, list) else None
            candidate.status = 'scored'
            print(f"AI Screening Успех для Кандидата {candidate.id}. Оценка: {candidate.ai_score}%. Статус: scored.")
        else:
            print(f"AI Screening Ошибка: AI вернул некорректный формат оценки для Кандидата {candidate.id}. Ответ: {ai_output_text}")
            candidate.status = 'failed_ai_format'
            candidate.ai_score = None
            candidate.keywords = ai_output_text
            # TODO: Логировать ошибку формата

    except (APIStatusError, APIConnectionError, RateLimitError) as e:
        print(f"AI Screening Ошибка API для Кандидата {candidate.id}: {e}")
        candidate.status = f'failed_ai_api_{e.__class__.__name__}'
        candidate.ai_score = None
        candidate.keywords = str(e)
        # TODO: Логировать ошибку API

    except json.JSONDecodeError as e:
        print(f"AI Screening Ошибка парсинга JSON для Кандидата {candidate.id}: {e}. Ответ AI: {ai_output_text}")
        candidate.status = 'failed_ai_format'
        candidate.ai_score = None
        candidate.keywords = ai_output_text
        # TODO: Логировать ошибку парсинга

    except Exception as e:
        print(f"AI Screening Неизвестная ошибка для Кандидата {candidate.id}: {e}")
        import traceback
        traceback.print_exc()
        candidate.status = 'failed_ai_unknown'
        candidate.ai_score = None
        candidate.keywords = str(e)
        # TODO: Логировать неизвестную ошибку

    finally:
        db.session.commit() # Важно сохранить изменения статуса и результатов


# --- КОНЕЦ КОДА: Функция AI Скрининга (Шаг 27 - ИСПРАВЛЕНО) ---


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
    user_vacancies = current_user.vacancies

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


# Маршрут для просмотра деталей конкретной вакансии (Шаг 24, ИЗМЕНЕНО в Шаге 28.1)
@app.route('/jobs/<int:job_id>')
@login_required
def view_job(job_id):
    job = Vacancy.query.get_or_404(job_id)

    if job.user_id != current_user.id:
        abort(403)

    # Получаем список кандидатов (Шаг 28.1)
    candidates = job.candidates

    # Передаем объект вакансии, пользователя И список кандидатов в шаблон
    return render_template('view_job.html', job=job, user=current_user, candidates=candidates)


# Маршрут для загрузки резюме для конкретной вакансии (Шаг 26, ИЗМЕНЕНО в Шаге 27, 29.2)
@app.route('/jobs/<int:job_id>/upload_resume', methods=['POST'])
@login_required
def upload_resume(job_id):
    job = Vacancy.query.get_or_404(job_id)

    if job.user_id != current_user.id:
        abort(403)

    if 'resume_file' not in request.files:
        flash('Файл не был выбран.', 'error')
        return redirect(url_for('view_job', job_id=job.id))

    file = request.files['resume_file']

    if file.filename == '':
        flash('Файл не был выбран.', 'error')
        return redirect(url_for('view_job', job_id=job.id))

    original_filename = secure_filename(file.filename)
    file_extension = get_file_extension(original_filename)

    if file_extension.strip('.') not in ALLOWED_EXTENSIONS:
         flash(f'Неподдерживаемый формат файла: {file_extension}. Разрешены только {", ".join(ALLOWED_EXTENSIONS)}.', 'error')
         return redirect(url_for('view_job', job_id=job.id))

    # --- Сохранение файла на диске (Шаг 29.2) ---
    # TODO: Использовать уникальные имена файлов, чтобы избежать перезаписи!
    # Например: unique_filename = f"{uuid.uuid4()}_{original_filename}"
    # from uuid import uuid4
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)

    try:
        file.save(file_path)
        storage_path = original_filename # В базе пока храним только имя файла относительно папки uploads
        print(f"Файл {original_filename} сохранен в {file_path}")
    except Exception as e:
        print(f"Ошибка при сохранении файла {original_filename}: {e}")
        flash(f'Не удалось сохранить файл {original_filename}.', 'error')
        return redirect(url_for('view_job', job_id=job.id))

    # --- Извлечение текста из сохраненного файла (Шаг 26, ИЗМЕНЕНО в Шаге 29.2) ---
    extracted_text = None
    try:
        with open(file_path, 'rb') as f:
             file_content = f.read()

        if file_extension == '.pdf':
            extracted_text = extract_text_from_pdf(file_content)
        elif file_extension == '.docx':
            extracted_text = extract_text_from_docx(file_content)

        if not extracted_text or len(extracted_text.strip()) == 0:
             print(f"Извлечен пустой текст из файла {original_filename}. Удаляем файл.")
             os.remove(file_path)
             flash(f'Не удалось извлечь текст или текст пуст из файла {original_filename}.', 'error')
             return redirect(url_for('view_job', job_id=job.id))
    except Exception as e:
        print(f"Ошибка при извлечении текста из сохраненного файла {original_filename}: {e}")
        os.remove(file_path)
        flash(f'Ошибка при извлечении текста из файла {original_filename}.', 'error')
        return redirect(url_for('view_job', job_id=job.id))

    # --- Сохранение кандидата в базу данных (Шаг 26, ИЗМЕНЕНО для Шага 29.2) ---
    # !!! TODO: Проверить на дубликаты по имени файла и вакансии, или добавить UUID !!!
    existing_candidate = Candidate.query.filter_by(vacancy_id=job.id, original_filename=original_filename).first()

    if existing_candidate:
        print(f"Кандидат с именем файла {original_filename} для вакансии {job.id} уже существует. Обновляем его.")
        candidate_to_process = existing_candidate
        candidate_to_process.storage_path = storage_path
        candidate_to_process.extracted_text = extracted_text
        candidate_to_process.status = 'uploaded' # Сбрасываем статус для повторной обработки
        candidate_to_process.ai_score = None
        candidate_to_process.keywords = None
    else:
        print(f"Создаем нового кандидата с именем файла {original_filename} для вакансии {job.id}.")
        new_candidate = Candidate(
            vacancy_id=job.id,
            original_filename=original_filename,
            storage_path=storage_path,
            extracted_text=extracted_text,
            status='uploaded'
        )
        db.session.add(new_candidate)
        candidate_to_process = new_candidate

    db.session.commit()

    # --- Запуск AI Скрининга после сохранения (Шаг 27) ---
    print(f"Кандидат {candidate_to_process.id} создан/обновлен. Запускаем AI скрининг...")
    try:
        perform_ai_screening(candidate_to_process.id)
    except Exception as e:
         print(f"Ошибка синхронного вызова perform_ai_screening для кандидата {candidate_to_process.id}: {e}")
         db.session.rollback()
         candidate_failed = db.session.get(Candidate, candidate_to_process.id)
         if candidate_failed and 'failed' not in candidate_failed.status:
             candidate_failed.status = 'failed_screening_sync_error'
             candidate_failed.keywords = str(e)
             db.session.commit()

    flash(f'Резюме "{original_filename}" загружено и обработка завершена (см. статус кандидата ниже).', 'success')
    return redirect(url_for('view_job', job_id=job.id))


# --- КОД: Маршрут Скачивания Резюме (Шаг 29.3) ---
@app.route('/candidates/<int:candidate_id>/download_resume')
@login_required
def download_resume(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)

    job = candidate.vacancy
    if not job:
         print(f"Ошибка: Вакансия для кандидата {candidate_id} не найдена при попытке скачивания.")
         abort(404)

    if job.user_id != current_user.id:
        print(f"Ошибка доступа: Пользователь {current_user.id} пытается скачать резюме {candidate_id} чужой вакансии {job.id}.")
        abort(403)

    if not candidate.storage_path:
        print(f"Ошибка: Для кандидата {candidate.id} не указан storage_path.")
        abort(404)

    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], candidate.storage_path, as_attachment=True)
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден на диске по пути {os.path.join(app.config['UPLOAD_FOLDER'], candidate.storage_path)} для кандидата {candidate.id}.")
        abort(404)


# --- КОДЕ: Маршрут Просмотра Извлеченного Текста (Шаг 30.2) ---
@app.route('/candidates/<int:candidate_id>/text')
@login_required
def view_extracted_text(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)

    job = candidate.vacancy
    if not job:
         print(f"Ошибка: Вакансия для кандидата {candidate.id} не найдена при попытке просмотра текста.")
         abort(404)

    if job.user_id != current_user.id:
        print(f"Ошибка доступа: Пользователь {current_user.id} пытается посмотреть текст резюме {candidate.id} чужой вакансии {job.id}.")
        abort(403)

    return render_template('view_extracted_text.html', candidate=candidate, user=current_user)
# --- КОНЕЦ КОДА: Маршрут Просмотра Извлеченного Текста (Шаг 30.2) ---

# --- НАЧАЛО НОВОГО КОДА: Маршрут Ручного Запуска AI Скрининга (Шаг 31.1) ---
@app.route('/candidates/<int:candidate_id>/rescreen', methods=['POST'])
@login_required
def rescreen_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)

    job = candidate.vacancy
    if not job:
         print(f"Ошибка: Вакансия для кандидата {candidate.id} не найдена при попытке ручного скрининга.")
         flash('Ошибка: Вакансия для этого кандидата не найдена.', 'error')
         return redirect(url_for('list_jobs'))

    if job.user_id != current_user.id:
        print(f"Ошибка доступа: Пользователь {current_user.id} пытается запустить скрининг резюме {candidate.id} чужой вакансии {job.id}.")
        abort(403)

    if not candidate.extracted_text or len(candidate.extracted_text.strip()) == 0:
        print(f"Нельзя запустить скрининг для кандидата {candidate.id}: нет извлеченного текста.")
        flash('Нельзя запустить скрининг: текст резюме отсутствует.', 'error')
        return redirect(url_for('view_job', job_id=job.id))

    print(f"Ручной запуск скрининга для Кандидата {candidate.id}...")
    try:
        perform_ai_screening(candidate.id)
        flash(f'AI скрининг для "{candidate.original_filename}" запущен (см. статус).', 'success')
    except Exception as e:
         print(f"Ошибка синхронного вызова perform_ai_screening для кандидата {candidate.id} при ручном запуске: {e}")
         flash(f'Произошла ошибка при запуске AI скрининга для "{candidate.original_filename}".', 'error')

    return redirect(url_for('view_job', job_id=job.id))
# --- КОНЕЦ НОВОГО КОДА: Маршрут Ручного Запуска AI Скрининга (Шаг 31.1) ---


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
    # База данных уже создана на шаге 18.2 (или пересоздана на шаге 21.2, 25.2)
    app.run(debug=True, host='0.0.0.0', port=5000)