"""
Генератор PDF ТОРГ-12 через ReportLab Platypus Table.
Упрощённая рабочая версия — компактная таблица без сложных SPAN.
"""
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from xml.sax.saxutils import escape


def generate_torg12_pdf(invoice, counterparty, config, font_name="Helvetica", amount_to_words=None, unit_to_okei=None):
    """Генерирует PDF ТОРГ-12."""
    if amount_to_words is None:
        from app import _amount_to_words_rub as amount_to_words

    def esc(s):
        return escape(str(s or ""))

    def fmt_num(x):
        try:
            return f"{float(x or 0):.2f}".replace(".", ",")
        except (TypeError, ValueError):
            return "0,00"

    buf = io.BytesIO()
    margin = 12 * mm
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        topMargin=margin, bottomMargin=margin,
        leftMargin=margin, rightMargin=margin,
    )
    styles = getSampleStyleSheet()
    fs7 = ParagraphStyle("FS7", parent=styles["Normal"], fontName=font_name, fontSize=7)
    fs8 = ParagraphStyle("FS8", parent=styles["Normal"], fontName=font_name, fontSize=8)

    org = esc(config.get("COMPANY_NAME", "")) + ", " + esc(config.get("COMPANY_ADDRESS", ""))
    org += ", ИНН " + esc(config.get("COMPANY_INN", ""))
    org += ", р/с " + esc(config.get("COMPANY_ACCOUNT", "")) + " в " + esc(config.get("COMPANY_BANK", ""))

    buyer = esc(counterparty.full_name or counterparty.name)
    if counterparty.address or counterparty.legal_address:
        buyer += ", " + esc(counterparty.address or counterparty.legal_address)
    buyer += ", ИНН " + esc(counterparty.inn or "")

    inv_num = esc(invoice.invoice_number)
    inv_dt = (invoice.invoice_date or __import__("datetime").date.today()).strftime("%d.%m.%Y")
    basis = f"Счет на оплату № {inv_num} от {inv_dt}"

    flow = []
    page_w = 297 * mm - 2 * margin  # A4 landscape ширина минус поля
    col_n = 10 * mm
    col_qty = 18 * mm
    col_prc = 22 * mm
    col_sum = 25 * mm
    col_name = page_w - col_n - col_qty - col_prc - col_sum

    # 1. Заголовок
    h_style = ParagraphStyle("H", parent=styles["Normal"], fontName=font_name, fontSize=8, alignment=TA_CENTER)
    flow.append(Paragraph("Унифицированная форма № ТОРГ-12", h_style))
    flow.append(Paragraph("Утверждена постановлением Госкомстата России от 25.12.98 № 132", h_style))
    flow.append(Spacer(1, 3 * mm))

    # 2. Реквизиты — простая таблица 2 колонки
    info_data = [
        ["Грузоотправитель:", Paragraph(org[:300], fs7)],
        ["Грузополучатель:", Paragraph(buyer[:200], fs7)],
        ["Поставщик:", Paragraph(org[:300], fs7)],
        ["Плательщик:", Paragraph(buyer[:200], fs7)],
        ["Основание:", Paragraph(basis, fs7)],
    ]
    info_w = [35 * mm, page_w - 35 * mm]
    info_tbl = Table(info_data, colWidths=info_w)
    info_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(info_tbl)
    flow.append(Spacer(1, 2 * mm))

    # 3. Номер и дата
    num_data = [
        ["Номер документа", "Дата составления", "Коды", "Форма по ОКУД", "по ОКПО"],
        [inv_num, inv_dt, "", "0330212", esc(config.get("COMPANY_OKPO") or "—")],
    ]
    num_tbl = Table(num_data, colWidths=[40 * mm, 40 * mm, 25 * mm, 35 * mm, 35 * mm])
    num_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(num_tbl)
    flow.append(Spacer(1, 2 * mm))

    # 4. Товары — простая таблица 5 колонок
    goods_cols = [col_n, col_name, col_qty, col_prc, col_sum]
    goods_data = [
        ["№", "Наименование", "Кол-во", "Цена", "Сумма"],
    ]
    total_sum = 0.0
    total_qty = 0.0
    for i, it in enumerate(invoice.items, 1):
        qty = float(it.quantity or 0)
        prc = float(it.price or 0)
        s = round(qty * prc, 2)
        total_sum += s
        total_qty += qty
        goods_data.append([
            str(i),
            Paragraph(esc(it.name), fs7),
            fmt_num(qty),
            fmt_num(prc),
            fmt_num(s),
        ])
    goods_data.append([
        "Всего",
        "",
        fmt_num(total_qty),
        "х",
        fmt_num(total_sum),
    ])

    goods_tbl = Table(goods_data, colWidths=goods_cols, repeatRows=1)
    goods_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
    ]))
    flow.append(goods_tbl)
    flow.append(Spacer(1, 3 * mm))

    # 5. Нижняя часть
    n = len(invoice.items)
    rec = "записей" if n >= 5 else "записи" if 2 <= n % 10 <= 4 else "запись"
    flow.append(Paragraph(f"Товарная накладная имеет приложение на ___ листах и содержит {n} порядковых номера {rec}", fs7))
    flow.append(Paragraph("Масса груза (нетто) ___ прописью   Масса груза (брутто) ___ прописью   Всего мест ___ прописью", fs7))
    flow.append(Paragraph("Приложение (паспорта, сертификаты и т.п.) на ___ листах   По доверенности № ___ от ___ выданной ___", fs7))
    flow.append(Paragraph(f"Всего отпущено на сумму {amount_to_words(total_sum)}", fs8))
    flow.append(Spacer(1, 4 * mm))

    # 6. Подписи
    sig_data = [
        ["Отпуск груза разрешил", "Груз принял"],
        ["Генеральный директор", "Груз получил"],
        ["", "грузополучатель"],
        [f"Отпуск груза произвел ___ {(__import__('datetime').date.today()).strftime('%d.%m.%Y')} г.   м.п.", ""],
    ]
    sig_tbl = Table(sig_data, colWidths=[page_w / 2, page_w / 2])
    sig_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BOX", (0, 0), (0, 2), 0.5, colors.black),
        ("BOX", (1, 0), (1, 2), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("SPAN", (0, 3), (1, 3)),
    ]))
    flow.append(sig_tbl)

    doc.build(flow)
    buf.seek(0)
    return buf
