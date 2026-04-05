import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import RadialGradiantColorMask, SolidFillColorMask
from qrcode.image.styles.moduledrawers import CircleModuleDrawer
from qrcode.main import QRCode

data = "https://www.example.com"

# Создаем и сохраняем изображение
qr = QRCode(
    version=1,  # Размер сетки (1 — 21x21, 40 — 177x177). None — подобрать автоматически.
    error_correction=qrcode.constants.ERROR_CORRECT_H,  # Высокий уровень коррекции (30%)
    box_size=5,  # Размер одного "пикселя" QR-кода в итоговом изображении
    border=5,  # Толщина белой рамки вокруг кода (в "пикселях" QR-кода)
)
qr.add_data("https://www.example.com")
qr.make(fit=True)

# Создаем стилизованное изображение
img = qr.make_image(
    image_factory=StyledPilImage,  # Используем "стилизованную" фабрику
    module_drawer=CircleModuleDrawer(),  # Рисуем пиксели кружочками, а не квадратами
    color_mask=SolidFillColorMask(),  # Красим в радиальный градиент
    embeded_image_path="my_qrcode.png",  # Внедряем картинку в центр
)
img.save("styled_qrcode.png")
