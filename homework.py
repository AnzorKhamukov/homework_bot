import logging
import os
import requests
import telegram
import time
import sys

from dotenv import load_dotenv

from exceptions import FailedConnection, FormatError, ParsingError

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
    '%(asctime)s, %(levelname)s, %(message)s'
)
handler = logging.StreamHandler()


def check_tokens():
    """Проверка переменных окружения."""
    TOKEN_DICT = {
        PRACTICUM_TOKEN: 'PRACTICUM_TOKEN',
        TELEGRAM_TOKEN: 'TELEGRAM_TOKEN',
        TELEGRAM_CHAT_ID: 'TELEGRAM_CHAT_ID'
    }

    for token in TOKEN_DICT:
        if token is None:
            logger.critical('отсутствуют обязательные данные')
            return False
        return True


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
        if response.status_code != 200:
            logger.error('Сервер не доступен')
            raise FailedConnection('не удалось подключиться к серверу')
    except requests.RequestException:
        logger.error('не удается получить ответ от сервера ЯП')

    try:
        response = response.json()
    except FormatError:
        logger.error('ошибка формата')
    return response


def check_response(response):
    """Проверяем корректность данных."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logger.error('отсутсвтуют ожидаемые ключи')
    if 'homeworks' not in response:
        logger.error('нет нужного ключа')
        raise TypeError

    if type(response) != dict:
        raise TypeError

    if type(homeworks) != list:
        logger.error('Получили неверные данные')
        raise TypeError('ошибка в данных')
    return homeworks


def parse_status(homework):
    """Проверяем статус домашней работы."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_VERDICTS[homework_status]
    except ParsingError('не удалось получить статус домашней работы'):
        logger.error('ParsingError')
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def main():
    """Основная логика работы бота."""
    if not check_tokens():
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
