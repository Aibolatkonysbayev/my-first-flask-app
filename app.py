# Импортируем необходимые классы из Flask
# Добавляем render_template для отображения HTML-файлов из папки templates
from flask import Flask, request, jsonify, render_template

# Создаем экземпляр приложения Flask
app = Flask(__name__)

# Новый маршрут для отображения главной страницы (корня сайта '/')
@app.route('/')
def index():
    # render_template ищет файл index.html в папке templates
    return render_template('index.html')

# Определяем маршрут (endpoint) /greet, который будет принимать POST-запросы
@app.route('/greet', methods=['POST'])
def greet():
    # Проверяем, что запрос пришел в формате JSON
    if not request.json:
        return jsonify({"error": "Request must be JSON"}), 415 # Код 415 Unsupported Media Type

    # Получаем данные из JSON-тела запроса. Ожидаем ключ 'name'.
    # Используем .get() для безопасного доступа на случай отсутствия ключа.
    name = request.json.get('name')

    # Проверяем, было ли передано имя
    if not name:
        return jsonify({"error": "Name not provided"}), 400 # Код 400 Bad Request

    # Формируем приветственное сообщение
    greeting_message = f"Привет, {name}!"

    # Возвращаем ответ в формате JSON
    return jsonify({"greeting": greeting_message})

# Этот блок запускает веб-сервер Flask, если файл запускается напрямую
if __name__ == '__main__':
    # debug=True позволяет видеть ошибки в браузере и автоматически перезапускать сервер при изменениях
    # host='0.0.0.0' нужен для развертывания на некоторых хостингах (для локальной разработки можно опустить)
    app.run(debug=True)