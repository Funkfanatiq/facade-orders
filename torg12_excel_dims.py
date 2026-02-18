# Размеры из Excel ТОРГ-12 (образец 11 от 12.07.2016)
# Извлечено из xlsx: cols width, row heights
# Excel width: 1 unit = ширина символа "0" в Normal font.
# Конверсия: 1 Excel unit = 0.852 mm (стандартная)

_COL_WIDTHS_EXCEL = [
    1.1640625, 5.83203125, 12.6640625, 2.33203125, 18.6640625, 2, 12.1640625,
    5.1640625, 2.1640625, 1.6640625, 0.5, 7.5, 7.83203125, 0.6640625, 5.1640625,
    1.33203125, 9.33203125, 0.6640625, 2.6640625, 2.6640625, 2.33203125, 7,
    3.5, 3.5, 10, 5.33203125, 1.83203125, 4.6640625, 0.6640625, 2.5,
    0.33203125, 7.1640625, 2, 0.83203125, 3.5, 3, 7, 1.1640625, 13
]

_EXCEL_TO_MM = 0.852
_COL_WIDTHS_MM_RAW = [w * _EXCEL_TO_MM for w in _COL_WIDTHS_EXCEL]
# A4 landscape: 297mm. Excel margins left 0.75"=19mm, right 1"=25.4mm -> usable 252.6mm
_USABLE_PAGE_MM = 297 - 19 - 25.4
_SCALE = _USABLE_PAGE_MM / sum(_COL_WIDTHS_MM_RAW) if sum(_COL_WIDTHS_MM_RAW) > 0 else 1.0
_COL_WIDTHS_MM = [w * _SCALE for w in _COL_WIDTHS_MM_RAW]

# Индексы 0-based: A=0, B=1, ..., AM=38
# Левая часть верхнего блока: B-AC = cols 1..28
LEFT_BLOCK_MM = sum(_COL_WIDTHS_MM[1:29])
# Секция кодов: AK, AL, AM = cols 36,37,38
CODES_LABEL_MM = _COL_WIDTHS_MM[36] + _COL_WIDTHS_MM[37]  # AK+AL
CODES_VAL_MM = _COL_WIDTHS_MM[38]  # AM

# Высоты строк (pt -> mm: 1pt = 0.3528mm)
ROW_HEIGHTS_MM = {r: h * 0.3528 * _SCALE for r, h in {
    1: 15.95, 2: 12.95, 3: 12, 4: 12, 5: 8.1, 6: 12, 7: 14.1, 8: 21.95,
    9: 8.1, 10: 21.95, 11: 8.1, 12: 21.95, 13: 8.1, 14: 12, 15: 12, 16: 12,
    17: 12, 18: 12, 19: 11.1, 20: 11.1, 21: 44.1, 22: 11.1, 23: 11.1, 24: 11.1,
    25: 11.1, 26: 11.1, 27: 11.1, 28: 12, 29: 11.1, 30: 8.1, 31: 11.1, 32: 8.1,
    33: 11.1, 34: 8.1, 35: 5.1, 36: 9.95, 37: 11.1, 38: 9.95, 39: 11.1,
    40: 11.1, 41: 21.95, 42: 9, 43: 11.1, 44: 11.1, 45: 11.1, 46: 11.1,
    47: 5.1, 48: 11.1,
}.items()}
DEFAULT_ROW_MM = 11.45 * 0.3528 * _SCALE

# Таблица товаров 15 колонок — соответствие Excel (B-AM). По merge cells:
# 0:Номер B | 1:Товар наим C-E | 2:код F | 3:Ед.наим G-H | 4:ОКЕИ I | 5:Упаковка J |
# 6-8:Кол-во K-M | 9:Масса брутто N | 10:Нетто O | 11:Цена P-Q | 12:Сумма R-U |
# 13:НДС ставка V-AD | 14:НДС сумма AE-AK | 15:Сумма с НДС AL-AM
# У нас 15 колонок: объединяем 13+14 в одну НДС
GOODS_TABLE_COLS_MM = [
    sum(_COL_WIDTHS_MM[1:2]),   # 0: Номер
    sum(_COL_WIDTHS_MM[2:6]),   # 1: Товар наименование
    sum(_COL_WIDTHS_MM[6:7]),   # 2: код
    sum(_COL_WIDTHS_MM[7:9]),   # 3: Ед.изм наименование
    sum(_COL_WIDTHS_MM[9:10]),  # 4: код ОКЕИ
    sum(_COL_WIDTHS_MM[10:11]), # 5: Вид упаковки
    sum(_COL_WIDTHS_MM[11:12]), # 6: в одном месте
    sum(_COL_WIDTHS_MM[12:13]), # 7: мест
    sum(_COL_WIDTHS_MM[13:14]), # 8: (резерв)
    sum(_COL_WIDTHS_MM[14:16]), # 9: Масса брутто + Кол-во нетто
    sum(_COL_WIDTHS_MM[16:18]), # 10: Цена
    sum(_COL_WIDTHS_MM[18:22]), # 11: Сумма без НДС
    sum(_COL_WIDTHS_MM[22:30]), # 12: НДС ставка (Y-AD)
    sum(_COL_WIDTHS_MM[30:37]), # 13: НДС сумма (AE-AK)
    sum(_COL_WIDTHS_MM[37:39]), # 14: Сумма с НДС (AL-AM)
]
