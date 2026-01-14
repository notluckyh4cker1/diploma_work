from PIL.Image import Image
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtOpenGL import QGLWidget, QGLFormat
from OpenGL.GL import *

class OpenGLRasterWidget(QGLWidget):
    def __init__(self, parent=None):
        format = QGLFormat()
        format.setSampleBuffers(True)
        format.setSamples(4)
        format.setDepth(True)
        format.setRgba(True)
        format.setDoubleBuffer(True)

        super().__init__(format, parent)

        self.raster = None
        self.textures = {}
        self.tile_size = (512, 512)  # Уменьшаем для надежности

        # Трансформации
        self.scale = 1.0
        self.translate_x = 0.0
        self.translate_y = 0.0

        # Размеры изображения
        self.image_width = 0
        self.image_height = 0

        # Флаги
        self.needs_center_view = True  # Флаг для центрирования при первой загрузке

        self.setMouseTracking(True)

    def set_raster(self, raster):
        """Устанавливает растр и центрирует вид."""
        if raster is None:
            return False

        self.raster = raster
        info = raster.get_image_info()
        if info:
            self.image_width = info['size'][0]
            self.image_height = info['size'][1]

            print(f"Изображение: {self.image_width}x{self.image_height}")
            print(f"Тайл: {self.tile_size[0]}x{self.tile_size[1]}")

            # Сбрасываем трансформации
            self.scale = 1.0
            self.translate_x = 0.0
            self.translate_y = 0.0

            # Устанавливаем флаг центрирования
            self.needs_center_view = True

            # Загружаем начальные тайлы
            self.load_visible_tiles()

            # Принудительно обновляем
            self.update()

            return True
        return False

    def initializeGL(self):
        """Инициализация OpenGL."""
        try:
            glClearColor(0.0, 0.0, 0.0, 1.0)  # Черный фон
            glEnable(GL_TEXTURE_2D)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            # Включаем сглаживание линий
            glEnable(GL_LINE_SMOOTH)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

            print("OpenGL инициализирован")

        except Exception as e:
            print(f"Ошибка инициализации OpenGL: {e}")

    def resizeGL(self, width, height):
        """Обработка изменения размера окна."""
        glViewport(0, 0, width, height)

        # Если изображение загружено, центрируем вид
        if self.image_width > 0 and self.image_height > 0:
            self.center_view()

        self.load_visible_tiles()

    def paintGL(self):
        """Отрисовка сцены."""
        try:
            # Очищаем буфер
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            # Устанавливаем проекцию
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()

            # Ортографическая проекция - ВАЖНО!
            # Координаты: (0,0) в левом верхнем углу
            glOrtho(0, self.width(), self.height(), 0, -1, 1)

            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            # Если нет изображения, рисуем только фон
            if self.image_width == 0 or self.image_height == 0:
                return

            # Автоматически центрируем при первой отрисовке
            if self.needs_center_view:
                self.center_view()
                self.needs_center_view = False

            # Применяем трансформации
            glTranslatef(self.translate_x, self.translate_y, 0)
            glScalef(self.scale, self.scale, 1.0)

            # Рисуем рамку для изображения (для отладки)
            glColor3f(0.5, 0.5, 0.5)  # Серый
            glLineWidth(1.0)
            glBegin(GL_LINE_LOOP)
            glVertex2f(0, 0)
            glVertex2f(self.image_width, 0)
            glVertex2f(self.image_width, self.image_height)
            glVertex2f(0, self.image_height)
            glEnd()

            # Включаем текстуры
            glEnable(GL_TEXTURE_2D)

            # Рисуем тайлы
            tile_w, tile_h = self.tile_size

            for (tx, ty), texture_id in self.textures.items():
                x = tx * tile_w
                y = ty * tile_h

                # Получаем реальный размер тайла
                actual_w = min(tile_w, self.image_width - x)
                actual_h = min(tile_h, self.image_height - y)

                if actual_w <= 0 or actual_h <= 0:
                    continue

                try:
                    glBindTexture(GL_TEXTURE_2D, texture_id)
                    glColor3f(1.0, 1.0, 1.0)  # Белый цвет

                    glBegin(GL_QUADS)
                    # Важно: координаты текстуры от 0 до 1
                    # Важно: вершины по часовой стрелке
                    glTexCoord2f(0.0, 0.0)
                    glVertex2f(x, y)

                    glTexCoord2f(1.0, 0.0)
                    glVertex2f(x + actual_w, y)

                    glTexCoord2f(1.0, 1.0)
                    glVertex2f(x + actual_w, y + actual_h)

                    glTexCoord2f(0.0, 1.0)
                    glVertex2f(x, y + actual_h)
                    glEnd()

                except Exception as e:
                    print(f"Ошибка отрисовки тайла {tx},{ty}: {e}")

            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)

        except Exception as e:
            print(f"Ошибка в paintGL: {e}")

    def center_view(self):
        """Центрирует изображение в виджете."""
        if self.image_width == 0 or self.image_height == 0:
            return

        widget_width = self.width()
        widget_height = self.height()

        if widget_width == 0 or widget_height == 0:
            return

        # Вычисляем масштаб, чтобы изображение поместилось
        scale_x = widget_width / self.image_width
        scale_y = widget_height / self.image_height
        self.scale = min(scale_x, scale_y) * 0.9  # 90% от полного размера

        # Центрируем
        scaled_width = self.image_width * self.scale
        scaled_height = self.image_height * self.scale

        self.translate_x = (widget_width - scaled_width) / 2
        self.translate_y = (widget_height - scaled_height) / 2

        # Обновляем тайлы
        self.load_visible_tiles()

    def fit_to_view(self):
        """Подгоняет изображение под размер окна."""
        self.center_view()
        self.update()

    def load_visible_tiles(self):
        """Загружает только видимые тайлы."""
        if not self.raster or self.image_width == 0 or self.image_height == 0:
            return

        # Вычисляем видимую область в координатах изображения
        viewport = self.get_visible_viewport()

        if viewport[2] <= viewport[0] or viewport[3] <= viewport[1]:
            return

        # Определяем, какие тайлы нужны
        needed_tiles = self.calculate_needed_tiles(viewport)

        # Загружаем новые тайлы
        for tile_pos in needed_tiles:
            if tile_pos not in self.textures:
                self.load_tile(tile_pos)

        # Удаляем невидимые тайлы
        tiles_to_remove = []
        for tile_pos in self.textures:
            if tile_pos not in needed_tiles:
                tiles_to_remove.append(tile_pos)

        for tile_pos in tiles_to_remove:
            self.unload_tile(tile_pos)

        self.update()

    def get_visible_viewport(self):
        """Возвращает видимую область в координатах изображения."""
        if self.width() == 0 or self.height() == 0:
            return (0, 0, 0, 0)

        # Преобразуем координаты виджета в координаты изображения

        # 1. Координаты углов виджета
        widget_left = 0
        widget_top = 0
        widget_right = self.width()
        widget_bottom = self.height()

        # 2. Применяем обратные трансформации
        #    Сначала перемещение, потом масштаб
        scale = self.scale if self.scale != 0 else 1.0

        # Координаты в системе изображения
        img_left = (widget_left - self.translate_x) / scale
        img_top = (widget_top - self.translate_y) / scale
        img_right = (widget_right - self.translate_x) / scale
        img_bottom = (widget_bottom - self.translate_y) / scale

        # Обрезаем по границам изображения
        img_left = max(0, min(img_left, self.image_width))
        img_top = max(0, min(img_top, self.image_height))
        img_right = max(0, min(img_right, self.image_width))
        img_bottom = max(0, min(img_bottom, self.image_height))

        return (img_left, img_top, img_right, img_bottom)

    def calculate_needed_tiles(self, viewport):
        """Вычисляет, какие тайлы нужны для отображения области."""
        tiles = set()
        x1, y1, x2, y2 = viewport

        if x2 <= x1 or y2 <= y1:
            return tiles

        # Добавляем margin для плавной прокрутки
        margin = self.tile_size[0] // 4  # 25% от размера тайла
        x1 = max(0, x1 - margin)
        y1 = max(0, y1 - margin)
        x2 = min(self.image_width, x2 + margin)
        y2 = min(self.image_height, y2 + margin)

        # Вычисляем индексы тайлов
        tile_w, tile_h = self.tile_size
        start_x = int(x1 // tile_w)
        start_y = int(y1 // tile_h)
        end_x = int(x2 // tile_w) + 1
        end_y = int(y2 // tile_h) + 1

        for tx in range(start_x, end_x):
            for ty in range(start_y, end_y):
                tiles.add((tx, ty))

        return tiles

    def load_tile(self, tile_pos):
        """Загружает тайл в текстуру OpenGL с исправлением памяти."""
        try:
            tx, ty = tile_pos
            tile_w, tile_h = self.tile_size

            x = tx * tile_w
            y = ty * tile_h

            # Получаем тайл из растра
            tile_image = self.raster.get_tile(x, y, tile_w, tile_h)
            if tile_image is None:
                return

            # Проверяем и конвертируем формат
            original_mode = tile_image.mode

            # Конвертируем в поддерживаемый формат
            if original_mode == '1':  # Бинарное
                tile_image = tile_image.convert('L').convert('RGB')
                data_format = GL_RGB
                internal_format = GL_RGB
                bytes_per_pixel = 3
            elif original_mode == 'L':  # Градации серого
                tile_image = tile_image.convert('RGB')
                data_format = GL_RGB
                internal_format = GL_RGB
                bytes_per_pixel = 3
            elif original_mode == 'P':  # Палитровое
                tile_image = tile_image.convert('RGB')
                data_format = GL_RGB
                internal_format = GL_RGB
                bytes_per_pixel = 3
            elif original_mode == 'RGB':
                data_format = GL_RGB
                internal_format = GL_RGB
                bytes_per_pixel = 3
            elif original_mode == 'RGBA':
                data_format = GL_RGBA
                internal_format = GL_RGBA
                bytes_per_pixel = 4
            else:
                # Неизвестный формат - конвертируем в RGB
                tile_image = tile_image.convert('RGB')
                data_format = GL_RGB
                internal_format = GL_RGB
                bytes_per_pixel = 3

            # Получаем данные изображения
            try:
                if data_format == GL_RGB:
                    # Важно: используем правильный порядок байтов
                    image_data = tile_image.tobytes("raw", "RGB")
                else:  # RGBA
                    image_data = tile_image.tobytes("raw", "RGBA")

                expected_size = tile_image.width * tile_image.height * bytes_per_pixel
                actual_size = len(image_data)

                if actual_size != expected_size:
                    print(f"Ошибка: размер данных {actual_size} != ожидаемый {expected_size}")
                    return

            except Exception as e:
                print(f"Ошибка получения данных: {e}")
                return

            self.makeCurrent()

            # Генерируем текстуру
            texture_id = glGenTextures(1)
            if texture_id <= 0:
                print(f"Ошибка генерации текстуры")
                return

            glBindTexture(GL_TEXTURE_2D, texture_id)

            # Настройки текстуры (важно для больших текстур)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

            # Отключаем выравнивание (пакетное чтение может его включать)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

            # Загружаем текстуру
            try:
                glTexImage2D(GL_TEXTURE_2D, 0, internal_format,
                             tile_image.width, tile_image.height, 0,
                             data_format, GL_UNSIGNED_BYTE, image_data)

                # Проверяем ошибки OpenGL
                error = glGetError()
                if error != GL_NO_ERROR:
                    print(f"OpenGL ошибка: {error}")
                    # Пробуем с меньшим размером
                    if tile_image.width > 2048 or tile_image.height > 2048:
                        # Уменьшаем размер в 2 раза
                        small_image = tile_image.resize(
                            (tile_image.width // 2, tile_image.height // 2),
                            Image.Resampling.LANCZOS
                        )
                        if data_format == GL_RGB:
                            small_data = small_image.tobytes("raw", "RGB")
                        else:
                            small_data = small_image.tobytes("raw", "RGBA")

                        glTexImage2D(GL_TEXTURE_2D, 0, internal_format,
                                     small_image.width, small_image.height, 0,
                                     data_format, GL_UNSIGNED_BYTE, small_data)

                        error = glGetError()
                        if error != GL_NO_ERROR:
                            print(f"OpenGL ошибка после уменьшения: {error}")
                            glDeleteTextures([texture_id])
                            return

            except Exception as e:
                print(f"Исключение при glTexImage2D: {e}")
                glDeleteTextures([texture_id])
                return

            # Сохраняем текстуру
            self.textures[tile_pos] = texture_id

            tile_image = None

        except Exception as e:
            print(f"Ошибка загрузки тайла {tile_pos}: {e}")

    def unload_tile(self, tile_pos):
        """Выгружает тайл из памяти."""
        if tile_pos in self.textures:
            try:
                self.makeCurrent()
                glDeleteTextures([self.textures[tile_pos]])
                del self.textures[tile_pos]
            except Exception as e:
                print(f"Ошибка выгрузки тайла {tile_pos}: {e}")

    def wheelEvent(self, event):
        """Масштабирование относительно позиции курсора мыши."""
        if self.image_width == 0 or self.image_height == 0:
            return

        # Сохраняем старый масштаб
        old_scale = self.scale

        # Определяем коэффициент масштабирования
        zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8

        # Получаем позицию курсора в координатах виджета
        mouse_x = event.x()
        mouse_y = event.y()

        # Преобразуем координаты курсора в систему изображения ДО масштабирования
        img_x_before = (mouse_x - self.translate_x) / old_scale
        img_y_before = (mouse_y - self.translate_y) / old_scale

        # Применяем новый масштаб
        self.scale *= zoom_factor

        # Ограничиваем масштаб
        self.scale = max(0.01, min(100.0, self.scale))

        # Вычисляем новые координаты курсора в системе изображения ПОСЛЕ масштабирования
        img_x_after = (mouse_x - self.translate_x) / self.scale
        img_y_after = (mouse_y - self.translate_y) / self.scale

        # Корректируем смещение для сохранения позиции под курсором
        dx = (img_x_after - img_x_before) * self.scale
        dy = (img_y_after - img_y_before) * self.scale

        self.translate_x += dx
        self.translate_y += dy

        # Обновляем тайлы и перерисовываем
        self.load_visible_tiles()
        self.update()

        event.accept()

    def mousePressEvent(self, event):
        """Обработка нажатия кнопки мыши."""
        self.last_mouse_x = event.x()
        self.last_mouse_y = event.y()

    def mouseMoveEvent(self, event):
        """Обработка движения мыши для панорамирования."""
        if event.buttons() & Qt.LeftButton:
            dx = event.x() - self.last_mouse_x
            dy = event.y() - self.last_mouse_y

            # Панорамирование
            self.translate_x += dx
            self.translate_y += dy

            self.load_visible_tiles()
            self.update()

        self.last_mouse_x = event.x()
        self.last_mouse_y = event.y()

    def zoom_in(self):
        """Увеличивает масштаб."""
        self.scale *= 1.25
        self.scale = min(100.0, self.scale)
        self.load_visible_tiles()
        self.update()

    def zoom_out(self):
        """Уменьшает масштаб."""
        self.scale *= 0.8
        self.scale = max(0.01, self.scale)
        self.load_visible_tiles()
        self.update()

    def zoom_original(self):
        """Возвращает исходный масштаб."""
        self.scale = 1.0
        self.translate_x = 0
        self.translate_y = 0
        self.load_visible_tiles()
        self.update()


class RasterCanvas(QWidget):
    """Холст для отображения и оцифровки растрового изображения."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # OpenGL виджет
        self.gl_widget = OpenGLRasterWidget(self)
        layout.addWidget(self.gl_widget)

        print("RasterCanvas инициализирован")

    def set_raster(self, raster):
        """Устанавливает растровое изображение."""

        if raster is None:
            return False

        try:
            success = self.gl_widget.set_raster(raster)

            if success:
                # Принудительно обновляем
                self.gl_widget.update()
                QApplication.processEvents()

                # Ждем немного и снова обновляем
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, self.gl_widget.update)

            return success

        except Exception as e:
            print(f"Ошибка при установке растра: {e}")
            import traceback
            traceback.print_exc()
            return False

    def clear_scene(self):
        """Очищает сцену."""
        self.gl_widget.raster = None
        self.gl_widget.image_width = 0
        self.gl_widget.image_height = 0
        self.gl_widget.textures.clear()
        self.gl_widget.update()

    def fit_to_view(self):
        """Подгоняет изображение под размер окна."""
        self.gl_widget.fit_to_view()

    def zoom_in(self):
        """Увеличивает масштаб."""
        self.gl_widget.zoom_in()

    def zoom_out(self):
        """Уменьшает масштаб."""
        self.gl_widget.zoom_out()

    def zoom_original(self):
        """Возвращает исходный масштаб."""
        self.gl_widget.zoom_original()