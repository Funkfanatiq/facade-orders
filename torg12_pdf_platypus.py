"""
Генератор PDF ТОРГ-12 через ReportLab Platypus Table.
Структура как в 1С: отдельные Table для секций, repeatRows для товаров.
"""
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from xml.sax.saxutils import escape

from torg12_excel_dims import (
    LEFT_BLOCK_MM, CODES_LABEL_MM, CODES_VAL_MM,
    GOODS_TABLE_COLS_MM, ROW_HEIGHTS_MM, DEFAULT_ROW_MM,
)


def generate_torg12_pdf(invoice, counterparty, config, font_name="Helvetica", amount_to_words=None, unit_to_okei=None):
    """Генерирует PDF ТОРГ-12 через Platypus Table (подход 1С/адаптивных форм)."""
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
    margin_mm = 10
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        topMargin=margin_mm * mm, bottomMargin=margin_mm * mm,
        leftMargin=margin_mm * mm, rightMargin=margin_mm * mm,
    )
    styles = getSampleStyleSheet()

    fs6 = ParagraphStyle("FS6", parent=styles["Normal"], fontName=font_name, fontSize=6)
    fs7 = ParagraphStyle("FS7", parent=styles["Normal"], fontName=font_name, fontSize=7)
    fs8 = ParagraphStyle("FS8", parent=styles["Normal"], fontName=font_name, fontSize=8)
    fs9 = ParagraphStyle("FS9", parent=styles["Normal"], fontName=font_name, fontSize=9)

    org_str = esc(config.get("COMPANY_NAME", "")) + ", " + esc(config.get("COMPANY_ADDRESS", ""))
    org_str += ", ИНН " + esc(config.get("COMPANY_INN", ""))
    org_str += ", р/с " + esc(config.get("COMPANY_ACCOUNT", "")) + " в банке " + esc(config.get("COMPANY_BANK", ""))
    org_str += " БИК " + esc(config.get("COMPANY_BIK", "")) + ", корр/с " + esc(config.get("COMPANY_CORR_ACCOUNT", ""))

    consignee = esc(counterparty.full_name or counterparty.name)
    if counterparty.address or counterparty.legal_address:
        consignee += ", " + esc(counterparty.address or counterparty.legal_address)
    consignee += ", ИНН " + esc(counterparty.inn or "")
    if counterparty.payment_account and counterparty.bank:
        consignee += ", р/с " + esc(counterparty.payment_account) + " в банке " + esc(counterparty.bank)

    inv_num = esc(invoice.invoice_number)
    inv_dt = (invoice.invoice_date or __import__("datetime").date.today()).strftime("%d.%m.%Y")
    basis = f"Счет на оплату № {inv_num} от {inv_dt}"

    seller_okpo = esc(config.get("COMPANY_OKPO") or "—")
    buyer_okpo = esc(counterparty.okpo or "—")

    flow = []

    # 1. Заголовок
    header_style = ParagraphStyle("H", parent=styles["Normal"], fontName=font_name, fontSize=8, alignment=TA_CENTER)
    flow.append(Paragraph("Унифицированная форма № ТОРГ-12", header_style))
    flow.append(Paragraph("Утверждена постановлением Госкомстата России от 25.12.98 № 132", header_style))
    flow.append(Spacer(1, 2 * mm))

    # 2. Верхний блок: левая часть + коды (структура как в 1С)
    left_w = LEFT_BLOCK_MM * mm
    codes_label_w = CODES_LABEL_MM * mm
    codes_val_w = CODES_VAL_MM * mm
    top_cols = [left_w, codes_label_w, codes_val_w]

    top_rows = [
        [Paragraph(org_str, fs7), "Коды", ""],
        ["", "Форма по ОКУД", "0330212"],
        ["", "по ОКПО", seller_okpo],
        [Paragraph("структурное подразделение", fs7), "Вид деятельности по ОКДП", "—"],
        ["", "по ОКПО", buyer_okpo],
        [Paragraph("Грузополучатель", fs7), "по ОКПО", buyer_okpo],
        [Paragraph(consignee, fs7), "", ""],
        [Paragraph("Поставщик", fs7), "по ОКПО", seller_okpo],
        [Paragraph(org_str, fs7), "", ""],
        [Paragraph("Плательщик", fs7), "по ОКПО", buyer_okpo],
        [Paragraph(consignee, fs7), "", ""],
        ["", "номер", inv_num],
        [Paragraph("Основание", fs7), "дата", inv_dt],
        [Paragraph(basis, fs7), "Номер документа", inv_num],
        ["", "Дата составления", inv_dt],
    ]

    top_style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (0, -1), 7),
        ("FONTSIZE", (1, 0), (1, -1), 6),
        ("FONTSIZE", (2, 0), (2, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("SPAN", (0, 0), (0, 2)),
        ("SPAN", (0, 3), (0, 4)),
        ("SPAN", (0, 5), (0, 6)),
        ("SPAN", (0, 7), (0, 8)),
        ("SPAN", (0, 9), (0, 10)),
        ("SPAN", (0, 11), (0, 12)),
        ("SPAN", (0, 13), (0, 14)),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("LINEAFTER", (0, 0), (0, -1), 0.5, colors.black),
        ("LINEAFTER", (1, 0), (1, -1), 0.5, colors.black),
        ("INNERGRID", (1, 0), (2, -1), 0.5, colors.black),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("RIGHTPADDING", (1, 0), (1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ])

    top_tbl = Table(top_rows, colWidths=top_cols)
    top_tbl.setStyle(top_style)
    flow.append(top_tbl)
    flow.append(Spacer(1, 3 * mm))

    # 3. ТОВАРНАЯ НАКЛАДНАЯ + Номер документа, Дата составления
    goods_cols = [w * mm for w in GOODS_TABLE_COLS_MM]
    total_goods_w = sum(goods_cols)
    title_cell_w = 25 * mm
    title_left = total_goods_w - 2 * title_cell_w
    title_block = Table([
        [Paragraph("ТОВАРНАЯ НАКЛАДНАЯ", ParagraphStyle("T", parent=styles["Normal"], fontName=font_name, fontSize=10, fontWeight="bold")), "Номер документа", "Дата составления"],
        ["", inv_num, inv_dt],
    ], colWidths=[title_left, title_cell_w, title_cell_w])
    title_block.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (0, -1), "MIDDLE"),
        ("SPAN", (0, 0), (0, -1)),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("INNERGRID", (1, 0), (2, -1), 0.5, colors.black),
        ("ALIGN", (1, 0), (2, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(title_block)
    flow.append(Spacer(1, 1 * mm))

    # 4. Таблица товаров — 15 колонок по GOODS_TABLE_COLS_MM
    header_r0 = ["Номер\nпо порядку", "Товар", "код", "Ед.изм.", "ОКЕИ", "Вид упак.", "в 1 месте", "мест", "", "Кол-во", "Цена", "Сумма без НДС", "НДС", "Сумма НДС"]
    header_r1 = ["", "наименование, характеристика", "", "наименование", "код", "", "", "шт", "", "нетто", "руб.коп.", "руб.коп.", "ставка %", "руб.коп."]
    data = [header_r0, header_r1]
    total_sum = 0.0
    total_qty = 0.0

    for i, it in enumerate(invoice.items, 1):
        qty = float(it.quantity or 0)
        prc = float(it.price or 0)
        s = round(qty * prc, 2)
        total_sum += s
        total_qty += qty
        unit = it.unit or "шт"
        okei = (unit_to_okei or (lambda u: "796"))(unit)
        code = str(it.price_list_item_id) if it.price_list_item_id else ""
        data.append([
            str(i),
            Paragraph(esc(it.name), fs7),
            code,
            unit,
            okei,
            "", "", "", "",
            fmt_num(qty),
            fmt_num(prc),
            fmt_num(s),
            "0%",
            "0,00",
            fmt_num(s),
        ])

    total_row = ["Всего по накладной"] + [""] * 8 + [fmt_num(total_qty), "х", fmt_num(total_sum), "х", "0,00", fmt_num(total_sum)]
    data.append(total_row)

    row_h_mm = ROW_HEIGHTS_MM.get(22, DEFAULT_ROW_MM)
    row_heights = [
        ROW_HEIGHTS_MM.get(20, DEFAULT_ROW_MM) * mm,
        ROW_HEIGHTS_MM.get(21, DEFAULT_ROW_MM) * mm,
    ]
    row_heights += [row_h_mm * mm] * (len(data) - 2)

    goods_tbl = Table(data, colWidths=goods_cols, rowHeights=row_heights, repeatRows=2)
    goods_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (9, 0), (-1, -1), "RIGHT"),
        ("SPAN", (0, 0), (0, 1)),
        ("SPAN", (1, 0), (2, 0)),
        ("SPAN", (3, 0), (4, 0)),
        ("SPAN", (0, -1), (8, -1)),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    flow.append(goods_tbl)
    flow.append(Spacer(1, 2 * mm))

    # 5. Нижняя часть
    n = len(invoice.items)
    rec = "записей" if n >= 5 else "записи" if 2 <= n % 10 <= 4 else "запись"
    flow.append(Paragraph(f"Товарная накладная имеет приложение на ___ листах и содержит {n} порядковых номера {rec}", fs7))
    flow.append(Paragraph("Масса груза (нетто) ___ прописью   Масса груза (брутто) ___ прописью   Всего мест ___ прописью", fs7))
    flow.append(Paragraph("Приложение (паспорта, сертификаты и т.п.) на ___ листах   По доверенности № ___ от ___ выданной ___", fs7))
    flow.append(Paragraph(f"Всего отпущено на сумму {amount_to_words(total_sum)}", fs8))
    flow.append(Spacer(1, 3 * mm))

    # 6. Подписи
    sig_w = left_w / 2
    sig_tbl = Table([
        ["Отпуск груза разрешил", "Груз принял"],
        ["Генеральный директор", "Груз получил"],
        ["", "грузополучатель"],
        [f"Отпуск груза произвел ___ {(__import__('datetime').date.today()).strftime('%d.%m.%Y')} г.   м.п.", ""],
    ], colWidths=[sig_w, sig_w])
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
