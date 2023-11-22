import staticmaps
from PIL import Image, ImageDraw, ImageFont
import gzip
from typing import Any
import pandas as pd
import pickle as pkl
from math import radians, sin, cos, sqrt, atan2
import warnings
import os


warnings.filterwarnings("ignore", category=DeprecationWarning)


class Intervals:
    def __init__(self, data):
        self.data = data

    def __repr__(self) -> str:
        return f'Intervals(data={self.data})'

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, index):
        return self.data[index]

    @classmethod
    def from_gzip(cls, filepath):
        data = cls.open_gzip_file(filepath)
        data_adr8 = data['PNK']['ADR8']
        data_intervals = cls.get_intervals(data['FLIGHT_DATA'])
        data_intervals = cls.set_info_about_intervals(
            data_adr8, data_intervals)
        return cls(data_intervals)

    @staticmethod
    def open_gzip_file(filepath):
        with gzip.open(filepath, 'rb') as f:
            data = pkl.load(f)
            return data

    @staticmethod
    def get_intervals(data):
        str_intervals = data['intervals'].split('\n')
        intervals = [x.split('-') for x in str_intervals]
        intervals = [
            Interval(i, float(x[0]), float(x[1])) for i, x in enumerate(intervals, 1)
        ]
        if not intervals:
            raise ValueError('Нет интервалов в gzip файле')
        return intervals

    @staticmethod
    def get_stroke_in_data(data, time):
        min_value = data[data['time'] >= time]['time'].min()
        return data[data['time'] == min_value]

    @classmethod
    def set_info_about_intervals(cls, data, intervals):
        try:
            for interval in intervals:
                current_stroke_start = cls.get_stroke_in_data(
                    data, interval.time_start)
                interval.latitude_start = current_stroke_start['latitude'].values[0]
                interval.longitude_start = current_stroke_start['longitude'].values[0]
                interval.real_time_start = current_stroke_start['time'].values[0]
                current_stroke_finish = cls.get_stroke_in_data(
                    data, interval.time_finish)
                interval.latitude_finish = current_stroke_finish['latitude'].values[0]
                interval.longitude_finish = current_stroke_finish['longitude'].values[0]
                interval.real_time_finish = current_stroke_finish['time'].values[0]
        except:
            raise ValueError('Не найдены координаты в gzip файле')
        return intervals

    @classmethod
    def from_txt(cls, filepath, intervals):
        data = cls.open_txt_file(filepath)
        intervals = [
            Interval(i, start, stop) for i, (start, stop) in enumerate(intervals, 1)]
        intervals = cls.set_info_about_intervals(data, intervals)
        return cls(intervals)

    @staticmethod
    def open_txt_file(filepath):
        data = None
        try:
            data = pd.read_csv(filepath, sep='\t')
        except:
            try:
                data = pd.read_csv(filepath, sep=',')
            except:
                data = pd.read_csv(filepath, sep=';')
        if data is None or data.empty:
            raise ValueError('Нет данных в txt файле')
        if 'name' in data.columns:
            data['time'] = data['name']
        return data

    def create_maps(self):
        for interval in self.data:
            interval.create_map()


class Interval:
    def __init__(self,
                 num: int,
                 time_start: float,
                 time_finish: float,
                 latitude_start=None,
                 longitude_start=None,
                 latitude_finish=None,
                 longitude_finish=None):
        self.num = num
        self.time_start = time_start
        self.time_finish = time_finish
        self.real_time_start: Any = None
        self.real_time_finish: Any = None
        self.latitude_start: Any = latitude_start
        self.latitude_finish: Any = latitude_finish
        self.longitude_start: Any = longitude_start
        self.longitude_finish: Any = longitude_finish
        self.distance: Any = None
        self.template_start: Any = None
        self.move_x_start: Any = None
        self.move_y_start: Any = None
        self.template_finish: Any = None
        self.move_x_finish: Any = None
        self.move_y_finish: Any = None
        self.main_template_path: str = 'templates/main_template.png'

    def __repr__(self) -> str:
        result = f'Interval(num={self.num}, time_start={self.time_start}, time_finish={self.time_finish}, '
        result += f'latitude_start={self.latitude_start}, longitude_start={self.longitude_start}, '
        result += f'latitude_finish={self.latitude_finish}, longitude_finish={self.longitude_finish})'
        return result

    def get_distance(self):
        if not all([
            self.latitude_start,
            self.latitude_finish,
            self.longitude_start,
            self.longitude_finish
        ]):
            raise ValueError('Не найдены координаты')

        R = 6371.0

        lat1_rad = radians(self.latitude_start)
        lon1_rad = radians(self.longitude_start)
        lat2_rad = radians(self.latitude_finish)
        lon2_rad = radians(self.longitude_finish)

        # Разница координат
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad

        # Вычисление расстояния с использованием формулы гаверсинусов
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        # Расстояние между точками
        distance = R * c

        return round(distance, 1)

    def create_templates(self):
        try:
            main_template = Image.open('templates/main_template.png', mode='r')
        except:
            raise FileNotFoundError(
                'Не найден шаблон main_template.png в папке templates')
        main_template_width, main_template_height = main_template.size

        if self.latitude_start >= self.latitude_finish:
            if self.longitude_start >= self.longitude_finish:
                self.template_start = 'templates/template4.png'
                self.move_x_start, self.move_y_start = 0, main_template_height
                self.template_finish = 'templates/template2.png'
                self.move_x_finish, self.move_y_finish = main_template_width, 0
            else:
                self.template_start = 'templates/template3.png'
                self.move_x_start, self.move_y_start = main_template_width, main_template_height
                self.template_finish = 'templates/template1.png'
                self.move_x_finish, self.move_y_finish = 0, 0
        else:
            if self.longitude_start >= self.longitude_finish:
                self.template_start = 'templates/template1.png'
                self.move_x_start, self.move_y_start = 0, 0
                self.template_finish = 'templates/template3.png'
                self.move_x_finish, self.move_y_finish = main_template_width, main_template_height
            else:
                self.template_start = 'templates/template2.png'
                self.move_x_start, self.move_y_start = main_template_width, 0
                self.template_finish = 'templates/template4.png'
                self.move_x_finish, self.move_y_finish = 0, main_template_height

        self.template_start = self.create_template(
            self.template_start, self.time_start, 'start')
        self.template_finish = self.create_template(
            self.template_finish, self.time_finish, 'finish')

    @staticmethod
    def create_template(template, text, name):
        if not os.path.exists('temp'):
            os.mkdir('temp')
        width, height = 220, 55

        try:
            image = Image.open(template, mode='r')
        except:
            raise FileNotFoundError(
                f'Не найден шаблон {template} в папке templates')
        # Получаем объект ImageDraw для рисования
        draw = ImageDraw.Draw(image)

        # Задаем текст и его стиль
        image_text = f'{text} c'

        font = ImageFont.truetype("arial.ttf", 35)

        # Определяем положение текста
        text_width, text_height = draw.textsize(image_text, font)
        x = 5 + (width - text_width) // 2
        y = 10 + (height - text_height) // 2

        # Рисуем текст на изображении
        draw.text((x, y), image_text, font=font, fill=(0, 0, 255, 255))

        # Сохраняем изображение в формате PNG
        image.save(f'temp/{name}.png', "PNG")
        return f'temp/{name}.png'

    def create_map_with_point(self):
        if not os.path.exists('img'):
            os.mkdir('img')
        context = staticmaps.Context()
        context.set_tile_provider(staticmaps.tile_provider_OSM)

        start = staticmaps.create_latlng(
            self.latitude_start, self.longitude_start)
        finish = staticmaps.create_latlng(
            self.latitude_finish, self.longitude_finish)
        try:
            context.add_object(staticmaps.Line(
                [start, finish], color=staticmaps.RED, width=3))
            context.add_object(staticmaps.ImageMarker(
                start, self.template_start, origin_x=self.move_x_start, origin_y=self.move_y_start))
            context.add_object(staticmaps.ImageMarker(
                finish, self.template_finish, origin_x=self.move_x_finish, origin_y=self.move_y_finish))
        except FileNotFoundError:
            raise FileNotFoundError(
                'Не найдены файлы шаблонов старта или/и финиша в папке temp')
        image = context.render_pillow(1024, 1024)
        self.map_filepath = f'img/{self.num}-{self.time_start}-{self.time_finish}.png'
        image.save(self.map_filepath)

    def add_info_to_map(self):
        image = Image.open(self.map_filepath, mode='r')
        draw = ImageDraw.Draw(image)

        text = f'Участок {self.num} Расстояние: {self.get_distance()} км.'
        font = ImageFont.truetype("arial.ttf", 35)

        width, height = image.size

        text_width, text_height = draw.textsize(text, font)
        x = (width - text_width) // 2
        y = height - text_height * 1.5

        points = [(0, height - text_height * 2), (width, height -
                                                  text_height * 2), (width, height), (0, height)]
        draw.polygon(points, fill=(
            255, 255, 255, 255), outline=(255, 255, 255, 255))

        draw.text((x, y), text, font=font, fill=(0, 0, 255, 255))
        image.save(self.map_filepath)

    def create_map(self):
        self.create_templates()
        self.create_map_with_point()
        self.add_info_to_map()
        print(f'Файл {self.map_filepath} создан')


if __name__ == '__main__':
    # intervals = Intervals.from_gzip('source/230922_ДИСС_курс эталон.gzip')
    t_intervals = [(50000, 66000)]
    intervals = Intervals.from_txt(
        'e:\\телеметрия\\1808_со средним креном и тангажом_курс по и2.txt', t_intervals)
    intervals.create_maps()
