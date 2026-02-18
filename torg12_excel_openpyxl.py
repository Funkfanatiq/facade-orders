"""
Генератор ТОРГ-12 через openpyxl + Excel-шаблон.
Заполняет шаблон ТОРГ-12 (образец 11 от 12.07.2016) данными счёта.
Вывод: Excel (xlsx).
"""
import io
from pathlib import Path

# Путь к шаблону (рядом с этим модулем)
_TEMPLATE_PATH = Path(__file__).parent / "torg12_template.xlsx"

# Стиль рамок
_THIN = "thin"


def _apply_border(ws, min_row, min_col, max_row, max_col, style=_THIN):
    """Применить рамки ко всем ячейкам в диапазоне."""
    try:
        from openpyxl.styles import Border, Side
        side = Side(border_style=style, color="000000")
        border = Border(left=side, top=side, right=side, bottom=side)
        for row in ws.iter_rows(min_row=min_row, min_col=min_col, max_row=max_row, max_col=max_col):
            for cell in row:
                cell.border = border
    except Exception:
        pass


def _fmt_num(x):
    try:
        return f"{float(x or 0):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return "0,00"


def _org_string(config):
    """Полная строка реквизитов организации для грузоотправителя/поставщика."""
    parts = [
        config.get("COMPANY_NAME", ""),
        config.get("COMPANY_ADDRESS", ""),
    ]
    inn = config.get("COMPANY_INN", "")
    kpp = config.get("COMPANY_KPP", "")
    if inn:
        parts.append(f"ИНН {inn}")
    if kpp:
        parts.append(f"КПП {kpp}")
    acc = config.get("COMPANY_ACCOUNT", "")
    bank = config.get("COMPANY_BANK", "")
    if acc and bank:
        parts.append(f"р/с {acc} в {bank}")
    bik = config.get("COMPANY_BIK", "")
    corr = config.get("COMPANY_CORR_ACCOUNT", "")
    if bik:
        parts.append(f"БИК {bik}")
    if corr:
        parts.append(f"к/с {corr}")
    return ", ".join(p for p in parts if p)


def _buyer_string(counterparty):
    """Реквизиты грузополучателя/плательщика."""
    parts = [counterparty.full_name or counterparty.name]
    addr = counterparty.address or counterparty.legal_address
    if addr:
        parts.append(addr)
    if counterparty.inn:
        parts.append(f"ИНН {counterparty.inn}")
    if counterparty.kpp:
        parts.append(f"КПП {counterparty.kpp}")
    if counterparty.payment_account or counterparty.bank:
        acc = counterparty.payment_account or ""
        bank = counterparty.bank or ""
        if acc and bank:
            parts.append(f"р/с {acc} в {bank}")
        elif acc:
            parts.append(f"р/с {acc}")
        elif bank:
            parts.append(f"в {bank}")
    if counterparty.bik:
        parts.append(f"БИК {counterparty.bik}")
    if counterparty.corr_account:
        parts.append(f"к/с {counterparty.corr_account}")
    return ", ".join(p for p in parts if p)


def generate_torg12_xlsx(invoice, counterparty, config, template_path=None):
    """
    Заполняет Excel-шаблон ТОРГ-12 и возвращает BytesIO с xlsx.
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ImportError("Установите openpyxl: pip install openpyxl")

    path = Path(template_path or _TEMPLATE_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Шаблон ТОРГ-12 не найден: {path}")

    wb = load_workbook(path)
    ws = wb.active

    inv_num = str(invoice.invoice_number or "")
    inv_dt = (invoice.invoice_date or __import__("datetime").date.today()).strftime("%d.%m.%Y")
    # Дата составления = дата создания документа ТОРГ-12 (сегодня)
    doc_dt_str = __import__("datetime").date.today().strftime("%d.%m.%Y")
    basis = f"Счет на оплату № {inv_num} от {inv_dt}"

    org = _org_string(config)
    buyer = _buyer_string(counterparty)

    # Верхний блок — пишем в левую ячейку объединённой области
    ws["B3"] = org
    ws["B6"] = buyer
    ws["D10"] = org
    ws["D12"] = buyer
    ws["D14"] = basis

    # Номер документа = номер счёта, Дата составления = день отгрузки
    # Ячейки: K17 (top-left K17:N17), O17 (top-left O17:R17)
    ws["K17"] = inv_num
    ws["O17"] = doc_dt_str

    # ОКПО (если есть в шаблоне)
    okpo = config.get("COMPANY_OKPO") or ""
    if okpo:
        ws["AM13"] = okpo

    # Форма по ОКУД
    ws["AK15"] = "0330212"

    # Таблица товаров: данные с строки 22
    # Merged: C22:F22 имя, H22:K22 ед., N22:P22 кол-во, Q=цена, R22:U22 сумма
    # Пишем в top-left объединённой ячейки (иначе MergedCell read-only)
    DATA_START_ROW = 22
    DEFAULT_DATA_ROWS = 6  # строк в шаблоне для товаров
    total_sum = 0.0
    total_qty = 0.0

    items = list(invoice.items)
    insert_count = max(0, len(items) - DEFAULT_DATA_ROWS)
    if insert_count > 0:
        insert_at = DATA_START_ROW + DEFAULT_DATA_ROWS
        ws.insert_rows(insert_at, insert_count)
        # Для новых строк добавляем merge, чтобы колонки не сползали
        for k in range(insert_count):
            r = insert_at + k
            for start, end in [(3, 6), (8, 11), (14, 16), (18, 21)]:
                try:
                    ws.merge_cells(start_row=r, start_column=start, end_row=r, end_column=end)
                except Exception:
                    pass

    for i, it in enumerate(items):
        row = DATA_START_ROW + i
        qty = float(it.quantity or 0)
        prc = float(it.price or 0)
        s = round(qty * prc, 2)
        total_sum += s
        total_qty += qty

        ws.cell(row=row, column=2, value=i + 1)
        ws.cell(row=row, column=3, value=str(it.name or ""))
        ws.cell(row=row, column=8, value=str(it.unit or "шт"))
        ws.cell(row=row, column=14, value=_fmt_num(qty))
        ws.cell(row=row, column=17, value=_fmt_num(prc))
        ws.cell(row=row, column=18, value=_fmt_num(s))

    last_data_row = DATA_START_ROW + len(items)
    ws.cell(row=last_data_row, column=2, value="Всего")
    ws.cell(row=last_data_row, column=14, value=_fmt_num(total_qty))
    ws.cell(row=last_data_row, column=17, value="х")
    ws.cell(row=last_data_row, column=18, value=_fmt_num(total_sum))

    # Рамки для верхнего блока (грузоотправитель, грузополучатель, поставщик, плательщик)
    _apply_border(ws, 3, 2, 15, 35)
    # Рамки для блока «Номер документа» / «Дата составления»
    _apply_border(ws, 16, 11, 17, 22)
    # Рамки для таблицы товаров (заголовки + данные + итого)
    _apply_border(ws, 20, 2, last_data_row, 21)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
