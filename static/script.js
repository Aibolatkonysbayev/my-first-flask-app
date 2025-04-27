// Ждем полной загрузки HTML-документа
document.addEventListener('DOMContentLoaded', () => {
    // Находим элементы на странице по их ID
    const nameInput = document.getElementById('nameInput');
    const greetButton = document.getElementById('greetButton');
    const resultDiv = document.getElementById('result');

    // Добавляем "слушателя" события клика на кнопку
    greetButton.addEventListener('click', async () => {
        // Получаем значение из поля ввода
        const name = nameInput.value;

        if (!name) {
            resultDiv.textContent = 'Пожалуйста, введите имя!';
            return; // Если имя не введено, прекращаем выполнение
        }

        // Очищаем предыдущий результат
        resultDiv.textContent = 'Загрузка...';

        try {
            // Отправляем POST-запрос на адрес /greet нашего бэкенда
            // Указываем метод POST, тип содержимого JSON
            // В теле запроса отправляем объект с именем
            const response = await fetch('/greet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: name }) // Преобразуем JavaScript объект в строку JSON
            });

            // Проверяем, успешен ли был HTTP-ответ (код 2xx)
            if (!response.ok) {
                throw new Error(`Ошибка HTTP: ${response.status}`);
            }

            // Парсим JSON-ответ от бэкенда
            const data = await response.json();

            // Выводим полученное приветствие в блок result
            resultDiv.textContent = `Бэкенд ответил: ${data.greeting}`;

        } catch (error) {
            // Обрабатываем ошибки (например, если бэкенд недоступен)
            console.error('Ошибка при запросе к бэкенду:', error);
            resultDiv.textContent = `Произошла ошибка: ${error.message}`;
        }
    });
});