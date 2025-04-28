# Импортируем необходимые классы из Flask
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, abort, current_app
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

# --- НАЧАЛО НОВОГО КОДА: Импорт для AI (Шаг 27 - ИСПРАВЛЕНО для openai v1.0.0+) ---
# Импортируем новый клиент OpenAI и конкретные классы ошибок
import openai
from openai import OpenAI, APIStatusError, APIConnectionError, RateLimitError # Импорты ошибок для v1.0.0+
import json # Может пригодиться для работы с JSON ответами от API
# --- КОНЕЦ НОВОГО КОДА: Импорт для AI (Шаг 27 - ИСПРАВЛЕНО) ---


# Создаем экземпляр приложения Flask
app = Flask(__name__)

# --- НАСТРОЙКА SECRET_KEY (Шаг 19) ---
app.config['SECRET_KEY'] = 'xgj6_6mu,_j7kem_5_e5h7_ko69;_c25vl_vbj6_m,,l' # >>> ОБЯЗАТЕЛЬНО ЗАМЕНИ НА СВОЮ <<<
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

# --- КОД: Фильтр Jinja для JSON (Шаг 28.1) ---
# Регистрируем фильтр from_json для шаблонов Jinja2
@app.template_filter('from_json')
def from_json_filter(json_string):
    if isinstance(json_string, str):
        try:
            return json.loads(json_string)
        except (json.JSONDecodeError, TypeError):
            return None
    return json_string
# --- КОНЕЦ КОДА: Фильтр Jinja для JSON (Шаг 28.1) ---


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


# --- НАЧАЛО НОВОГО КОДА: Функция AI Скрининга (Шаг 27 - ИСПРАВЛЕНО для openai v1.0.0+) ---
# Создаем клиент OpenAI здесь (один раз), а не внутри функции
# Ключ API берется из переменной окружения AI_API_KEY автоматически при инициализации клиента
try:
    ai_client = OpenAI(api_key=os.environ.get('AI_API_KEY'))
    print("OpenAI клиент инициализирован. Ключ API найден." if os.environ.get('AI_API_KEY') else "OpenAI клиент инициализирован. Ключ API НЕ найден.")
except Exception as e:
     ai_client = None # Клиент не будет создан, если ключ невалиден или ошибка
     print(f"Ошибка инициализации OpenAI клиента: {e}")
     print("AI Screening будет недоступен.")


def perform_ai_screening(candidate_id):
    """Выполняет AI-скрининг для заданного кандидата."""
    # Вызов этой функции должен выполняться в контексте приложения Flask,
    # если она обращается к db или моделям.

    # Если клиент AI не был создан (например, нет ключа), сразу отмечаем ошибку
    if not ai_client:
        print(f"AI Screening: Клиент OpenAI не инициализирован. Кандидат ID {candidate_id} обработан не будет.")
        candidate = db.session.get(Candidate, candidate_id)
        if candidate:
            candidate.status = 'failed_ai_nokey' # Используем тот же статус ошибки ключа
            # flash("Ошибка AI: Не настроен или невалиден API ключ.", 'error') # Flash не работает здесь
            db.session.commit()
        return

    # Важно получить кандидата в текущем контексте
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or not candidate.extracted_text:
        print(f"AI Screening: Кандидат с ID {candidate_id} не найден или текст не извлечен.")
        return # Нечего обрабатывать

    # Обновляем статус на "в процессе", прежде чем начать долгую операцию
    candidate.status = 'processing'
    db.session.commit() # Сохраняем статус "в процессе"

    job = candidate.vacancy
    if not job:
        print(f"AI Screening: Вакансия для кандидата {candidate_id} не найдена.")
        candidate.status = 'failed_ai_novacancy'
        db.session.commit()
        # TODO: Логировать
        return

    job_description = job.description
    resume_text = candidate.extracted_text

    # --- Формируем промпт для AI модели ---
    prompt_messages = [
        {"role": "system", "content": "Ты опытный рекрутер, специализирующийся на подборе персонала. Твоя задача - сравнить предоставленное резюме кандидата с описанием вакансии и оценить релевантность в процентах (от 0 до 100%). Также выдели ключевые навыки и опыт кандидата, которые соответствуют требованиям вакансии. Предоставь ответ строго в формате JSON с полями `relevance_score` (целое число) и `matching_keywords` (список строк)."},
        {"role": "user", "content": f"Описание Вакансии:\n---\n{job_description}\n---\n\nРезюме Кандидата:\n---\n{resume_text}\n---\n"},
    ]

    # --- Вызов AI API (OpenAI) - ИСПРАВЛЕНО для openai v1.0.0+ ---
    try:
        # Теперь вызываем через объект клиента и используем .create() для чатов
        response = ai_client.chat.completions.create(
            model="gpt-3.5-turbo", # или "gpt-4", "gpt-4-turbo-preview"
            messages=prompt_messages,
            temperature=0.0,
            max_tokens=500,
            # response_format={"type": "json_object"}, # Эта опция требует новых моделей
        )

        ai_output_text = response.choices[0].message.content # Доступ к содержимому изменился

        print(f"AI Response Text for Candidate {candidate.id}: {ai_output_text}")

        # Попытка парсить JSON из строки.
        ai_result = json.loads(ai_output_text)

        score = ai_result.get('relevance_score')
        keywords = ai_result.get('matching_keywords')

        # Валидируем полученные данные
        if isinstance(score, (int, float)) and 0 <= score <= 100:
            candidate.ai_score = float(score)
            candidate.keywords = json.dumps(keywords) if isinstance(keywords, list) else None
            candidate.status = 'scored' # Статус: успешно оценено
            print(f"AI Screening Успех для Кандидата {candidate.id}. Оценка: {candidate.ai_score}%. Статус: scored.")
        else:
            print(f"AI Screening Ошибка: AI вернул некорректный формат оценки для Кандидата {candidate.id}. Ответ: {ai_output_text}")
            candidate.status = 'failed_ai_format' # Статус: ошибка формата ответа AI
            candidate.ai_score = None
            candidate.keywords = ai_output_text # Сохраним raw ответ для анализа
            # TODO: Логировать

    # --- Обработка Ошибок API - ИСПРАВЛЕНО для openai v1.0.0+ ---
    except APIStatusError as e:
        # Обработка ошибок, связанных со статусом HTTP (4xx, 5xx)
        print(f"AI Screening Ошибка HTTP API для Кандидата {candidate.id}: {e.status_code} - {e.response.text}")
        candidate.status = f'failed_ai_http_{e.status_code}' # Более специфичный статус
        candidate.ai_score = None
        candidate.keywords = str(e) # Сохраним текст ошибки
        # Особо обрабатываем 401 (неавторизован) и 429 (лимит запросов)
        if e.status_code == 401:
             candidate.status = 'failed_ai_auth'
        elif e.status_code == 429:
             candidate.status = 'failed_ai_ratelimit'

    except APIConnectionError as e:
        # Обработка ошибок подключения к API
        print(f"AI Screening Ошибка подключения API для Кандидата {candidate.id}: {e}")
        candidate.status = 'failed_ai_connection'
        candidate.ai_score = None
        candidate.keywords = str(e)

    except RateLimitError as e:
        # Обработка ошибки превышения лимита запросов (на всякий случай, может быть частью APIStatusError)
        print(f"AI Screening Ошибка Rate Limit для Кандидата {candidate.id}: {e}")
        candidate.status = 'failed_ai_ratelimit'
        candidate.ai_score = None
        candidate.keywords = str(e)

    except json.JSONDecodeError as e:
        print(f"AI Screening Ошибка парсинга JSON для Кандидата {candidate.id}: {e}. Ответ AI: {ai_output_text}")
        candidate.status = 'failed_ai_format'
        candidate.ai_score = None
        candidate.keywords = ai_output_text
        # TODO: Логировать

    except Exception as e:
        print(f"AI Screening Неизвестная ошибка для Кандидата {candidate.id}: {e}")
        import traceback
        traceback.print_exc()
        candidate.status = 'failed_ai_unknown'
        candidate.ai_score = None
        candidate.keywords = str(e)
        # TODO: Логировать

    finally:
        # Важно сохранить изменения статуса и результатов, даже если произошла ошибка
        db.session.commit()


# --- КОНЕЦ НОВОГО КОДА: Функция AI Скрининга (Шаг 27 - ИСПРАВЛЕНО) ---


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


# Маршрут для просмотра деталей конкретной вакансии (Шаг 24, ИЗМЕНЕНО в Шаге 28.1)
@app.route('/jobs/<int:job_id>')
@login_required
def view_job(job_id):
    job = Vacancy.query.get_or_404(job_id)

    if job.user_id != current_user.id:
        abort(403)

    # Получаем список кандидатов (Шаг 28.1)
    candidates = job.candidates # Благодаря relationship в модели Vacancy, они уже отсортированы

    # Передаем объект вакансии, пользователя И список кандидатов в шаблон
    return render_template('view_job.html', job=job, user=current_user, candidates=candidates)


# Маршрут для загрузки резюме для конкретной вакансии (Шаг 26, ИЗМЕНЕНО в Шаге 27)
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

    if file_extension not in ['.pdf', '.docx']:
        flash('Неподдерживаемый формат файла. Разрешены только .pdf и .docx.', 'error')
        return redirect(url_for('view_job', job_id=job.id))

    extracted_text = None
    file_content = file.read()

    if file_extension == '.pdf':
        extracted_text = extract_text_from_pdf(file_content)
    elif file_extension == '.docx':
        extracted_text = extract_text_from_docx(file_content)

    if not extracted_text or len(extracted_text.strip()) == 0:
        flash(f'Не удалось извлечь текст или текст пуст из файла {original_filename}.', 'error')
        # TODO: Можно сохранить кандидата со статусом extraction_failed
        return redirect(url_for('view_job', job_id=job.id))

    # !!! TODO: Проверить на дубликаты по имени файла и вакансии, или добавить UUID !!!

    new_candidate = Candidate(
        vacancy_id=job.id,
        original_filename=original_filename,
        extracted_text=extracted_text,
        status='uploaded'
    )

    db.session.add(new_candidate)
    db.session.commit() # Сохраняем кандидата, чтобы у него появился ID в БД

    # --- Запуск AI Скрининга после сохранения (Шаг 27) ---
    print(f"Кандидат {new_candidate.id} создан. Запускаем AI скрининг...")
    # Важно выполнить в контексте приложения, т.к. perform_ai_screening обращается к БД.
    # current_app уже доступен в контексте запроса.
    # Если это синхронный вызов, контекст запроса уже есть.
    # Если это асинхронный вызов (TODO), потребуется app.app_context()
    perform_ai_screening(new_candidate.id) # Вызываем функцию скрининга
    # --- Конец Запуск AI Скрининга (Шаг 27) ---


    # Flash сообщение после завершения всего процесса (включая синхронный AI скрининг)
    flash(f'Резюме "{original_filename}" загружено и обработка завершена (см. статус кандидата ниже).', 'success') # Изменяем сообщение
    return redirect(url_for('view_job', job_id=job.id))


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