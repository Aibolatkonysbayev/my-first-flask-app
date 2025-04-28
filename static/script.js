document.addEventListener('DOMContentLoaded', () => {
    // Находим новые элементы на странице по их ID
    const resumeInput = document.getElementById('resumeInput');
    const jobDescriptionInput = document.getElementById('jobDescriptionInput');
    const adaptButton = document.getElementById('adaptButton'); // ID кнопки изменился
    const resultDiv = document.getElementById('result');

    // Добавляем "слушателя" события клика на новую кнопку
    adaptButton.addEventListener('click', async () => {
        // Получаем текст из обоих текстовых полей
        const resumeText = resumeInput.value;
        const jobDescriptionText = jobDescriptionInput.value;

        // Простая проверка на заполненность
        if (!resumeText || !jobDescriptionText) {
            resultDiv.className = 'error'; // Добавляем класс для стилизации ошибки
            resultDiv.textContent = 'Пожалуйста, вставьте и резюме, и описание вакансии.';
            return;
        }

        resultDiv.className = 'loading'; // Добавляем класс для стилизации загрузки
        resultDiv.textContent = 'Отправка данных на бэкенд...';

        try {
            // Отправляем POST-запрос на адрес /greet (пока используем старый маршрут)
            // В теле запроса отправляем ОБЪЕКТ с обоими текстами
            const response = await fetch('/greet', { // Пока отправляем на /greet
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                // Отправляем оба поля в одном JSON объекте
                body: JSON.stringify({
                    resume_text: resumeText,
                    job_description_text: jobDescriptionText
                })
            });

            // Проверяем статус ответа
            if (!response.ok) {
                 const errorText = await response.text(); // Попытаемся получить текст ошибки от сервера
                 throw new Error(`Ошибка HTTP: ${response.status} - ${errorText}`);
            }

            // Парсим JSON-ответ от бэкенда
            const data = await response.json();

            // TODO: Здесь будет отображаться адаптированное резюме от ИИ
            // Пока что бэкенд вернет просто подтверждение
            resultDiv.className = ''; // Убираем классы загрузки/ошибки
            // Ожидаем, что бэкенд вернет объект типа {"status": "received", ...}
            resultDiv.textContent = `Бэкенд успешно получил данные. Ответ: ${JSON.stringify(data, null, 2)}`; // Выводим весь ответ для отладки

        } catch (error) {
            // Обрабатываем ошибки запроса
            console.error('Ошибка при запросе к бэкенду:', error);
            resultDiv.className = 'error';
            resultDiv.textContent = `Произошла ошибка при отправке данных: ${error.message}`;
        }
    });
});