"""
Генератор ТОРГ-12 через openpyxl + Excel-шаблон.
Заполняет шаблон ТОРГ-12 (образец 11 от 12.07.2016) данными счёта.
Вывод: Excel (xlsx).
"""
import io
from pathlib import Path

# Путь к шаблону (рядом с этим модулем)
_TEMPLATE_PATH = Path(__file__).parent / "torg12_template.xlsx"


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
    if inn:
        parts.append(f"ИНН {inn}")
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
    parts = [counterparty.full_name or counterparty.name]
    if counterparty.address or counterparty.legal_address:
        parts.append(counterparty.address or counterparty.legal_address)
    if counterparty.inn:
        parts.append(f"ИНН {counterparty.inn}")
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
    # Merged cells: C22:F22 имя, H22:K22 ед., N22:P22 кол-во, R22:U22 сумма
    # Пишем ТОЛЬКО в top-left ячейку merge (иначе MergedCell read-only)
    # B=2 №, C=3 имя, H=8 ед., N=14 кол-во, Q=17 цена (не в merge), R=18 сумма
    DATA_START_ROW = 22
    DEFAULT_DATA_ROWS = 6  # строк в шаблоне для товаров
    total_sum = 0.0
    total_qty = 0.0

    items = list(invoice.items)
    if len(items) > DEFAULT_DATA_ROWS:
        # Вставляем дополнительные строки
        insert_count = len(items) - DEFAULT_DATA_ROWS
        ws.insert_rows(DATA_START_ROW + DEFAULT_DATA_ROWS, insert_count)

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

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
