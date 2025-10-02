from PyQt5.QtGui import QImage, QPixmap

def convert_cv_qt(cv_img, width, height):
    """Convert from an opencv image to QPixmap"""
    h, w, ch = cv_img.shape
    bytes_per_line = ch * w
    convert_to_Qt_format = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
    p = convert_to_Qt_format.scaled(width, height, aspectRatioMode=0)
    return QPixmap.fromImage(p)