# -*- coding: utf-8 -*-

"""
Use python3.8

Работа с картинками
"""

import requests

from io import BytesIO

from cairosvg import svg2png
from PIL import Image, ImageDraw, ImageFont


TEMPLATE_PATH = 'files/air_ticket_sample.jpg'

FONT_PATH = 'files/ofont.ru_Lifehack.ttf'
FONT_SIZE = 25

BLACK = (0, 0, 0, 255)

NAME_OFFSET = (15, 245)
PHONE_OFFSET = (15, 380)
EMAIL_OFFSET = (15, 310)
DEPARTURE_OFFSET = (15, 445)
ARRIVAL_OFFSET = (245, 445)
DATE_OFFSET = (15, 510)
SPACES_OFFSET = (245, 510)

AVATAR_URL = 'https://avatars.dicebear.com/api/bottts/'
AVATAR_OFFSET = (260, 215)


def generate_ticket(phone, email, name, departure, arrival, date, spaces):
    """
    Создание картинки билета
    :param phone: телефон пользователя
    :param email: email пользователя
    :param name: имя пользователя
    :param departure: город отправления
    :param arrival: город назначения
    :param date: дата вылета
    :param spaces: количество мест
    :return: .png в байтах
    """
    base = Image.open(TEMPLATE_PATH).convert("RGBA")
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    draw = ImageDraw.Draw(base)
    draw.text(NAME_OFFSET, name, font=font, fill=BLACK)
    draw.text(PHONE_OFFSET, phone, font=font, fill=BLACK)
    draw.text(EMAIL_OFFSET, email, font=font, fill=BLACK)
    draw.text(DEPARTURE_OFFSET, departure, font=font, fill=BLACK)
    draw.text(ARRIVAL_OFFSET, arrival, font=font, fill=BLACK)
    draw.text(DATE_OFFSET, date, font=font, fill=BLACK)
    draw.text(SPACES_OFFSET, spaces, font=font, fill=BLACK)

    response = requests.get(url=f'{AVATAR_URL}{email}.svg')
    svg_to_png = svg2png(bytestring=response.content, background_color='white')
    avatar_file_like = BytesIO(svg_to_png)
    avatar = Image.open(avatar_file_like)

    base.paste(avatar, AVATAR_OFFSET)

    temp_file = BytesIO()
    base.save(temp_file, 'png')
    temp_file.seek(0)

    return temp_file

    # base.show()
    # with open('files/example_ticket.png', 'wb') as ff:
    #     base.save(ff, 'png')
    #     base.show()


# generate_ticket(phone='+7-966-866-36-66',
#                 email='ivan@yandex.ru',
#                 name='Ivan',
#                 departure='Moscow',
#                 arrival='London',
#                 date='31-12-2020 23:59',
#                 spaces='1')
