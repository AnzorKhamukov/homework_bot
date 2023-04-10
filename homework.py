import logging
import os
import requests
import telegram
import time
import sys
from http import HTTPStatus

from dotenv import load_dotenv

from exceptions import FormatError, ParsingError, WrongStatus

load_dotenv()


PRACTICUM_TOKEN = os.getenv('Y_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)d'
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Сообщение отправленно: {message}')
    except telegram.TelegramError:
        logger.error(f'Не удалось отправить сообщение {message}')


def get_api_answer(timestamp):
    """Запрос к серверу."""
    timestamp = int(time.time())
    PARAMS = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=PARAMS
        )
        if response.status_code != HTTPStatus.OK:
            logger.error('Не верный статус')
            raise WrongStatus('Не найдет необходимый статус')
    except requests.RequestException as err:
        logger.error('не удается получить ответ от сервера ЯП', err)
        raise ConnectionError from err

    try:
        response = response.json()
    except FormatError as err:
        logger.error('ошибка формата', err)
        raise FormatError from err
    return response


def check_response(response):
    """Проверяем корректность данных."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logger.error('отсутсвтуют ожидаемые ключи')

    if type(response) != dict:
        raise TypeError

    if type(homeworks) != list:
        logger.error('Получили неверные данные')
        raise TypeError('ошибка в данных')
    if len(homeworks) == 0:
        logger.error('Список пуст.')
        raise ValueError('Полученный список пуст')
    return homeworks


def parse_status(homework):
    """Проверяем статус домашней работы."""
    try:
        homework_status = homework['status']
        verdict = HOMEWORK_VERDICTS[homework_status]
    except ParsingError('не удалось получить статус домашней работы'):
        logger.error('не удалось получить статус домашней работы')
    try:
        homework_name = homework['homework_name']
    except ParsingError('Не правильное имя домашней работы'):
        logger.error('Не правильное имя домашней работы')

    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('отсутствуют обязательные данные')
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homeworks = check_response(response)
            last_homework = homeworks[0]
            message = parse_status(last_homework)
            if message != last_message:
                send_message(bot, message)
                message = last_message

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != last_message:
                message = last_message
                send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
