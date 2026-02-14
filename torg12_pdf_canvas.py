"""
Генератор PDF ТОРГ-12 через ReportLab Canvas.
Рисует форму попиксельно по координатам из Excel — рамки только где они есть в образце.
"""
import io
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors

# Ширины колонок Excel A-AO (1-41) — из torg12_excel_spec + AO
from torg12_excel_spec import COL_WIDTHS_EXCEL
_COL_WIDTHS = list(COL_WIDTHS_EXCEL) + [0.5] * max(0, 41 - len(COL_WIDTHS_EXCEL))
# Высоты строк (1-48), в pt
_ROW_HEIGHTS = {
    1: 15.95, 2: 12.95, 3: 12, 4: 12, 5: 8.1, 6: 12, 7: 14.1, 8: 21.95,
    9: 8.1, 10: 21.95, 11: 8.1, 12: 21.95, 13: 8.1, 14: 12, 15: 12, 16: 12,
    17: 12, 18: 12, 19: 11.1, 20: 11.1, 21: 44.1, 22: 11.1, 23: 11.1, 24: 11.1,
    25: 11.1, 26: 11.1, 27: 11.1, 28: 12, 29: 11.1, 30: 8.1, 31: 11.1, 32: 8.1,
    33: 11.1, 34: 8.1, 35: 5.1, 36: 9.95, 37: 11.1, 38: 9.95, 39: 11.1,
    40: 11.1, 41: 21.95, 42: 9, 43: 11.1, 44: 11.1, 45: 11.1, 46: 11.1,
    47: 5.1, 48: 11.1,
}
DEFAULT_ROW_PT = 11.45

# Конверсия: Excel width unit -> mm (0.852), pt (1pt=0.353mm)
EXCEL_TO_MM = 0.852
PT_PER_MM = 2.834645669

def _col_letter_to_num(s):
    n = 0
    for c in s.upper():
        n = n * 26 + (ord(c) - ord('A') + 1)
    return n

def _parse_range(ref):
    if ':' in ref:
        a, b = ref.split(':')
        m1 = re.match(r'([A-Z]+)(\d+)', a, re.I)
        m2 = re.match(r'([A-Z]+)(\d+)', b, re.I)
        r1, c1 = int(m1.group(2)), _col_letter_to_num(m1.group(1))
        r2, c2 = int(m2.group(2)), _col_letter_to_num(m2.group(1))
        return (r1, c1, r2, c2)
    m = re.match(r'([A-Z]+)(\d+)', ref, re.I)
    r, c = int(m.group(2)), _col_letter_to_num(m.group(1))
    return (r, c, r, c)

def _get_col_width_pt(col_1based):
    idx = col_1based - 1
    if 0 <= idx < len(_COL_WIDTHS):
        w_mm = _COL_WIDTHS[idx] * EXCEL_TO_MM
        return w_mm * PT_PER_MM
    return 15

def _get_row_height_pt(row_1based):
    return _ROW_HEIGHTS.get(row_1based, DEFAULT_ROW_PT)

def _compute_layout():
    """Возвращает: col_positions, row_positions (в pt от верха страницы)"""
    col_pos = [0]
    for c in range(1, 42):  # A..AO (41 колонок)
        col_pos.append(col_pos[-1] + _get_col_width_pt(c))
    row_pos = [0]
    for r in range(1, 49):
        row_pos.append(row_pos[-1] + _get_row_height_pt(r))
    return col_pos, row_pos

# Все merged cells из Excel — для рисования полной сетки формы
from torg12_excel_spec import MERGED_CELLS

def generate_torg12_pdf(invoice, counterparty, config, font_name="Helvetica", amount_to_words=None, unit_to_okei=None):
    """Генерирует PDF ТОРГ-12 — идеальная копия Excel по размерам и рамкам."""
    from xml.sax.saxutils import escape
    def esc(s):
        return escape(str(s or ""))
    def fmt_num(x):
        try:
            return f"{float(x or 0):.2f}".replace(".", ",")
        except (TypeError, ValueError):
            return "0,00"

    buf = io.BytesIO()
    pw, ph = landscape(A4)
    margin_pt = 19 * PT_PER_MM  # 0.75"
    margin_r = 25.4 * PT_PER_MM  # 1"

    # Вычисляем позиции колонок и строк в pt
    col_pos, row_pos = _compute_layout()
    total_w_pt = col_pos[-1]
    usable_w = pw - margin_pt - margin_r
    scale_w = usable_w / total_w_pt if total_w_pt > 0 else 1
    # Высота листа для масштаба по Y
    total_h_pt = row_pos[-1]
    usable_h = ph - 2 * margin_pt
    scale_h = usable_h / total_h_pt if total_h_pt > 0 else 1
    scale = min(scale_w, scale_h)

    c = canvas.Canvas(buf, pagesize=landscape(A4))
    c.setFont(font_name, 8)
    c.translate(margin_pt, ph - margin_pt)

    def x_pt(col):
        return col_pos[col - 1] * scale
    def y_pt(row):
        """Y верхней границы строки row (origin — верх страницы, вниз отрицательно)"""
        return -row_pos[row - 1] * scale
    def w_pt(c1, c2):
        return (col_pos[c2] - col_pos[c1 - 1]) * scale
    def h_pt(r1, r2):
        return (row_pos[r2] - row_pos[r1 - 1]) * scale if r1 <= r2 else 0

    # Рисуем объединённые области с рамками
    thin = 0.5
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(thin)
    for ref in MERGED_CELLS:
        r1, c1, r2, c2 = _parse_range(ref)
        x1 = x_pt(c1)
        y1 = y_pt(r1)
        w = w_pt(c1, c2)
        h = h_pt(r1, r2)
        c.rect(x1, y1 - h, w, h, stroke=1, fill=0)

    # Заполняем динамические данные
    org_str = esc(config.get('COMPANY_NAME', '')) + ", " + esc(config.get('COMPANY_ADDRESS', ''))
    org_str += ", ИНН " + esc(config.get('COMPANY_INN', ''))
    org_str += ", р/с " + esc(config.get('COMPANY_ACCOUNT', '')) + " в банке " + esc(config.get('COMPANY_BANK', ''))
    org_str += " БИК " + esc(config.get('COMPANY_BIK', '')) + ", корр/с " + esc(config.get('COMPANY_CORR_ACCOUNT', ''))

    consignee = esc(counterparty.full_name or counterparty.name)
    if counterparty.address or counterparty.legal_address:
        consignee += ", " + esc(counterparty.address or counterparty.legal_address)
    consignee += ", ИНН " + esc(counterparty.inn or "")
    if counterparty.payment_account and counterparty.bank:
        consignee += ", р/с " + esc(counterparty.payment_account) + " в банке " + esc(counterparty.bank)

    inv_num = esc(invoice.invoice_number)
    inv_dt = (invoice.invoice_date or __import__('datetime').date.today()).strftime('%d.%m.%Y')
    basis = f"Счет на оплату № {inv_num} от {inv_dt}"

    # Заголовок A1:AM1
    c.setFont(font_name, 8)
    center_x = total_w_pt * scale / 2
    c.drawCentredString(center_x, y_pt(1) - 4, "Унифицированная форма № ТОРГ-12")
    c.drawCentredString(center_x, y_pt(1) - 10, "Утверждена постановлением Госкомстата России от 25.12.98 № 132")

    # Блок B3:AC4 - грузоотправитель
    c.setFont(font_name, 7)
    c.drawString(x_pt(2) + 2, y_pt(3) - 8, org_str[:200])
    if len(org_str) > 200:
        c.drawString(x_pt(2) + 2, y_pt(3) - 14, org_str[200:400])

    # Коды справа
    c.drawRightString(x_pt(38) - 2, y_pt(2) - 6, "Коды")
    c.drawRightString(x_pt(38) - 2, y_pt(3) - 6, "Форма по ОКУД")
    c.drawString(x_pt(39) + 2, y_pt(3) - 6, "0330212")
    c.drawRightString(x_pt(38) - 2, y_pt(4) - 6, "по ОКПО")
    c.drawString(x_pt(39) + 2, y_pt(4) - 6, esc(config.get('COMPANY_OKPO') or '—'))

    # Структурное подразделение D5
    c.drawString(x_pt(4) + 2, y_pt(5) - 6, "структурное подразделение")
    c.drawRightString(x_pt(38) - 2, y_pt(5) - 6, "Вид деятельности по ОКДП")
    c.drawString(x_pt(39) + 2, y_pt(5) - 6, "—")

    # Грузополучатель D7
    c.drawString(x_pt(4) + 2, y_pt(7) - 6, "Грузополучатель")
    c.drawString(x_pt(5) + 2, y_pt(7) - 6, consignee[:150])
    c.drawRightString(x_pt(38) - 2, y_pt(7) - 6, "по ОКПО")
    c.drawString(x_pt(39) + 2, y_pt(7) - 6, esc(counterparty.okpo or '—'))

    # Поставщик B8, ТОВАРНАЯ НАКЛАДНАЯ D8
    c.drawString(x_pt(2) + 2, y_pt(8) - 8, "Поставщик")
    c.drawString(x_pt(4) + 2, y_pt(8) - 8, org_str[:120])
    c.drawRightString(x_pt(38) - 2, y_pt(8) - 8, "по ОКПО")
    c.drawString(x_pt(39) + 2, y_pt(8) - 8, esc(config.get('COMPANY_OKPO') or '—'))

    # Плательщик B10
    c.drawString(x_pt(2) + 2, y_pt(10) - 8, "Плательщик")
    c.drawString(x_pt(4) + 2, y_pt(10) - 8, consignee[:120])
    c.drawRightString(x_pt(38) - 2, y_pt(10) - 8, "по ОКПО")
    c.drawString(x_pt(39) + 2, y_pt(10) - 8, esc(counterparty.okpo or '—'))

    # Номер, дата AK13, AM13
    c.drawRightString(x_pt(38) - 2, y_pt(13) - 6, "номер")
    c.drawRightString(x_pt(37) - 2, y_pt(13) - 6, "дата")
    c.drawString(x_pt(39) + 2, y_pt(13) - 6, inv_num)
    c.drawString(x_pt(38) + 2, y_pt(13) - 6, inv_dt)

    # Основание C14
    c.drawString(x_pt(3) + 2, y_pt(14) - 6, "Основание")
    c.drawString(x_pt(4) + 2, y_pt(14) - 6, basis[:80])
    c.drawRightString(x_pt(38) - 2, y_pt(14) - 6, "Номер документа")
    c.drawRightString(x_pt(37) - 2, y_pt(14) - 6, "Дата составления")
    c.drawString(x_pt(39) + 2, y_pt(14) - 6, inv_num)
    c.drawString(x_pt(38) + 2, y_pt(14) - 6, inv_dt)

    # ТОВАРНАЯ НАКЛАДНАЯ J17, Вид операции AL18
    c.setFont(font_name, 9)
    c.drawString(x_pt(10) + 2, y_pt(17) - 10, "ТОВАРНАЯ НАКЛАДНАЯ")
    c.drawRightString(x_pt(38) - 2, y_pt(18) - 6, "Вид операции")

    # Таблица товаров - заголовки и данные
    if amount_to_words is None:
        from app import _amount_to_words_rub as amount_to_words
    total_sum = 0.0
    for i, it in enumerate(invoice.items, 1):
        qty = float(it.quantity or 0)
        prc = float(it.price or 0)
        total_sum += qty * prc

    # Товарные строки (упрощённо - одна таблица с рамками)
    row = 22
    for i, it in enumerate(invoice.items, 1):
        qty = float(it.quantity or 0)
        prc = float(it.price or 0)
        s = round(qty * prc, 2)
        unit = it.unit or "шт"
        c.setFont(font_name, 7)
        c.drawCentredString(x_pt(2) + w_pt(2, 2) / 2, y_pt(row) - 7, str(i))
        c.drawString(x_pt(3) + 2, y_pt(row) - 7, esc(it.name)[:60])
        c.drawString(x_pt(8) + 2, y_pt(row) - 7, unit)
        c.drawRightString(x_pt(16) - 2, y_pt(row) - 7, fmt_num(qty))
        c.drawRightString(x_pt(23) - 2, y_pt(row) - 7, fmt_num(prc))
        c.drawRightString(x_pt(32) - 2, y_pt(row) - 7, fmt_num(s))
        c.drawString(x_pt(33) + 2, y_pt(row) - 7, "0%")
        c.drawRightString(x_pt(38) - 2, y_pt(row) - 7, fmt_num(s))
        row += 1

    # Итого
    c.drawString(x_pt(3) + 2, y_pt(row) - 7, "Всего по накладной")
    c.drawRightString(x_pt(16) - 2, y_pt(row) - 7, fmt_num(sum(float(x.quantity or 0) for x in invoice.items)))
    c.drawRightString(x_pt(32) - 2, y_pt(row) - 7, fmt_num(total_sum))
    c.drawRightString(x_pt(38) - 2, y_pt(row) - 7, fmt_num(total_sum))

    # Нижняя часть
    n = len(invoice.items)
    rec = "записей" if n >= 5 else "записи" if 2 <= n % 10 <= 4 else "запись"
    c.drawString(x_pt(2) + 2, y_pt(28) - 8, f"Товарная накладная имеет приложение на ___ листах и содержит {n} порядковых номера {rec}")
    c.drawString(x_pt(2) + 2, y_pt(29) - 8, "Масса груза (нетто) ___ прописью   Масса груза (брутто) ___ прописью   Всего мест ___ прописью")
    c.drawString(x_pt(2) + 2, y_pt(30) - 8, "Приложение (паспорта, сертификаты и т.п.) на ___ листах   По доверенности № ___ от ___ выданной ___")
    amount_w = amount_to_words(total_sum)
    c.drawString(x_pt(2) + 2, y_pt(31) - 8, f"Всего отпущено на сумму {amount_w}")

    # Подписи
    c.drawString(x_pt(2) + 2, y_pt(41) - 8, "Отпуск груза разрешил")
    c.drawString(x_pt(5) + 2, y_pt(41) - 8, "Генеральный директор")
    c.drawString(x_pt(10) + 2, y_pt(41) - 8, "Груз принял")
    c.drawString(x_pt(15) + 2, y_pt(41) - 8, "Груз получил")
    c.drawString(x_pt(20) + 2, y_pt(41) - 8, "грузополучатель")
    doc_date = __import__('datetime').date.today()
    c.drawString(x_pt(2) + 2, y_pt(42) - 8, f"Отпуск груза произвел ___ {doc_date.strftime('%d.%m.%Y')} г.   м.п.")

    c.save()
    buf.seek(0)
    return buf
