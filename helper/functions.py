import os
import sys
import json
import re
import urllib.request
import urllib.parse
import configparser


# ==================== Màu sắc & Style ====================
BG_COLOR = "#f0f4f8"
HEADER_BG = "#1e3a5f"
HEADER_FG = "#ffffff"
ACCENT = "#2980b9"
ACCENT_HOVER = "#3498db"
BTN_DANGER = "#c0392b"
BTN_DANGER_HOVER = "#e74c3c"
TEXT_COLOR = "#2c3e50"
CARD_BG = "#ffffff"
STATUS_BG = "#eaf2f8"
ROW_EVEN = "#ffffff"
ROW_ODD = "#f7fafc"
ROW_SELECT = "#d4e6f1"
BTN_SUCCESS = "#27ae60"
BTN_SUCCESS_HOVER = "#2ecc71"


# ==================== API config ====================
API_BASE_PRICES = "https://ems-api.vemedim.vn/api/ns/farm-price/customer-prices"
API_BASE_CUSTOMERS = "https://ems-api.vemedim.vn/api/ns/customer/simple-list"
API_TOKEN = "7a98712bb4c31e2feb4f927a4206faa006bac054e506fe37c945a1cff05f5a1abcb4d0c9200ebaa400ad201ddce8d15b"


# ==================== Dữ liệu dùng chung ====================
ALL_CUSTOMERS = []  # [{"customerCode": ..., "customerName": ..., "saleOrg": ...}]
SAP_SESSION = None  # Lưu session SAP để tái sử dụng


# ==================== Data Maps ====================
CHI_NHANH_MAP = {
    "CN ĐBSCL": "2001",
    "CỬA HÀNG TRUNG TÂM": "2002",
    "KINH DOANH ONLINE": "2003",
    "CN HÀ NỘI": "2501",
    "CN ĐÀ NẴNG": "2502",
    "CN NHA TRANG": "2505",
    "CN SÀI GÒN": "2506",
    "CN SÔNG TIỀN": "2507",
    "CN TÂY NGUYÊN": "2509",
}

CUSTOMER_GROUP_MAP = {
    "T1 - Trang trại loại B5": "T1",
    "T2 - Trang trại loại B4": "T2",
    "T3 - Trang trại loại B3": "T3",
    "T5 - Trang trại loại B2": "T5",
    "T6 - Trang trại loại B1": "T6",
    "T7 - Trang trại loại B0": "T7",
    "T8 - Trang trại loại C": "T8",
    "Z1 - Đại lý loại I": "Z1",
    "Z2 - Đại lý loại II": "Z2",
    "Z3 - Kinh Doanh Online": "Z3",
    "Z5 - Trang trại loại A": "Z5",
    "Z6 - Trang trại loại B": "Z6",
    "Z7 - KH đại lý hưởng CKTT": "Z7",
    "Z9 - Nhóm Khách hàng khác": "Z9",
}


# ==================== Utility ====================
def get_app_dir():
    """Lấy thư mục gốc project (chứa version.txt, config.ini)"""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    # helper/functions.py → lùi 1 cấp về thư mục gốc
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_version():
    """Đọc version từ version.txt trong thư mục app"""
    app_dir = get_app_dir()
    vf = os.path.join(app_dir, "version.txt")
    if os.path.exists(vf):
        try:
            with open(vf, "r", encoding="utf-8-sig") as f:
                return f.read().strip()
        except Exception:
            pass
    return "--"


def _parse_ver(v):
    """Parse version string thành tuple số để so sánh chính xác."""
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0,)


VERSION = _read_version()


# ==================== API ====================
def _api_get(url):
    """Gọi GET API với bearer token."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {API_TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_compare_so(main_vbeln, sub_vbeln):
    """Gọi API so sánh SO chính & SO phụ."""
    url = "https://ems-api.vemedim.vn/api/ns/sale-order/compare"
    try:
        data = urllib.parse.urlencode({"mainVbeln": main_vbeln, "subVbeln": sub_vbeln}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {API_TOKEN}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if body.get("success") and body.get("data"):
            return body["data"], None
        else:
            return None, body.get("message", "Không có dữ liệu")
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return None, f"Lỗi kết nối: {e.reason}"
    except Exception as e:
        return None, str(e)


def fetch_supplementary_so(main_vbeln, items_json):
    """Gọi API tạo SO phụ bổ sung mã SP.
    items_json: chuỗi JSON, ví dụ '[{"materialCode":"500000623","quantity":40}]'
    """
    url = "https://ems-api.vemedim.vn/api/ns/sale-order/supplementary"
    try:
        data = urllib.parse.urlencode({"mainVbeln": main_vbeln, "items": items_json}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {API_TOKEN}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if body.get("success"):
            return body.get("data"), None
        else:
            return None, body.get("message", "Không có dữ liệu")
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return None, f"Lỗi kết nối: {e.reason}"
    except Exception as e:
        return None, str(e)


def fetch_customer_list():
    """Gọi API lấy danh sách khách hàng."""
    global ALL_CUSTOMERS
    try:
        body = _api_get(API_BASE_CUSTOMERS)
        if body.get("success") and body.get("message"):
            ALL_CUSTOMERS = body["message"]
            print(f"[INIT] Đã tải {len(ALL_CUSTOMERS)} khách hàng")
        else:
            print(f"[INIT] API customer trả về không thành công")
            ALL_CUSTOMERS = []
    except Exception as e:
        print(f"[INIT] Lỗi tải danh sách KH: {e}")
        ALL_CUSTOMERS = []


def get_customer_completions(sale_org=""):
    """Lấy danh sách gợi ý mã KH, lọc theo saleOrg nếu có."""
    if sale_org:
        filtered = [c for c in ALL_CUSTOMERS if c.get("saleOrg", "") == sale_org]
    else:
        filtered = ALL_CUSTOMERS
    return [f"{c['customerCode']} - {c['customerName']}" for c in filtered]


def fetch_prices_from_api(customer_code, sale_org):
    """Gọi API lấy danh sách giá theo mã KH và chi nhánh."""
    params = urllib.parse.urlencode({"customerCode": customer_code, "saleOrg": sale_org})
    url = f"{API_BASE_PRICES}?{params}"
    try:
        body = _api_get(url)
        if body.get("success") and body.get("data"):
            data = body["data"]
            products = data.get("products", [])
            result = []
            for p in products:
                result.append({
                    "makh": data.get("customerCode", customer_code),
                    "masp": p.get("productCode", ""),
                    "tensp": p.get("productName", ""),
                    "gia": p.get("price", 0),
                    "ghi_chu": p.get("note", ""),
                })
            customer_info = f"{data.get('customerName', '')} - {data.get('typeCustomer', '')}"
            return result, customer_info, None
        else:
            return [], "", body.get("message", "Không có dữ liệu")
    except urllib.error.HTTPError as e:
        return [], "", f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return [], "", f"Lỗi kết nối: {e.reason}"
    except Exception as e:
        return [], "", str(e)


def fetch_sale_order(sale_order):
    """Gọi API lấy chi tiết Sale Order."""
    url = f"https://ems-api.vemedim.vn/api/ns/sale-order/{sale_order}"
    try:
        body = _api_get(url)
        if body.get("success") and body.get("data"):
            return body["data"], None
        else:
            return None, body.get("message", "Không có dữ liệu")
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return None, f"Lỗi kết nối: {e.reason}"
    except Exception as e:
        return None, str(e)


# ==================== SAP Session ====================
def _get_or_create_sap_session():
    """Lấy session SAP đã lưu hoặc tạo mới nếu chưa có / đã hết hạn."""
    global SAP_SESSION
    # Đảm bảo COM được khởi tạo trong thread hiện tại
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
    # Nếu đã có session → kiểm tra còn sống không
    if SAP_SESSION is not None:
        try:
            _ = SAP_SESSION.Info.SystemName
            print("Tái sử dụng session SAP đã có.")
            return SAP_SESSION
        except Exception:
            print("Session SAP cũ đã mất kết nối. Tạo session mới...")
            SAP_SESSION = None

    # Tạo session mới
    from helper.connect_sap import ConnectSAP
    session = ConnectSAP()
    if session not in (None, "MAX_SESSIONS"):
        SAP_SESSION = session
    return session


def reset_sap_session():
    """Reset SAP session (khi gặp lỗi, để lần sau tạo mới)."""
    global SAP_SESSION
    SAP_SESSION = None


# ==================== UI Helpers ====================
def on_enter_btn(e, color):
    e.widget.config(bg=color)


def on_leave_btn(e, color):
    e.widget.config(bg=color)


def bind_tree_shortcuts(root, tree, masp_col_index, lbl_status=None):
    """Gán Ctrl+A, Ctrl+C, Ctrl+V cho Treeview.
    masp_col_index: vị trí cột mã SP trong values (0-based).
    """
    def _select_all(event):
        tree.selection_set(tree.get_children())
        return "break"

    def _copy_masp(event):
        selected = tree.selection()
        if not selected:
            return "break"
        codes = []
        for item_id in selected:
            vals = tree.item(item_id, "values")
            codes.append(str(vals[masp_col_index]).strip())
        root.clipboard_clear()
        root.clipboard_append("\n".join(codes))
        if lbl_status:
            lbl_status.config(text=f"  Đã copy {len(codes)} mã SP")
        return "break"

    def _paste_and_select(event):
        try:
            clipboard = root.clipboard_get().strip()
        except Exception:
            return "break"
        masp_list = [x.strip().upper() for x in re.split(r'[\n\r\t,;\s]+', clipboard) if x.strip()]
        if not masp_list:
            return "break"
        masp_set = set(masp_list)
        masp_set_stripped = set(m.lstrip("0") for m in masp_list)
        tree.selection_remove(*tree.selection())
        matched = []
        for item_id in tree.get_children():
            values = tree.item(item_id, "values")
            masp_val = str(values[masp_col_index]).strip().upper()
            if masp_val in masp_set or masp_val.lstrip("0") in masp_set_stripped:
                matched.append(item_id)
        if matched:
            tree.selection_set(matched)
            unmatched = [iid for iid in tree.get_children() if iid not in matched]
            for idx, iid in enumerate(matched + unmatched):
                tree.move(iid, "", idx)
                vals = list(tree.item(iid, "values"))
                vals[0] = idx + 1
                tag = "even" if (idx + 1) % 2 == 0 else "odd"
                tree.item(iid, values=vals, tags=(tag,))
            tree.see(matched[0])
            if lbl_status:
                lbl_status.config(text=f"  Đã chọn {len(matched)}/{len(masp_list)} mã SP từ clipboard")
        else:
            if lbl_status:
                lbl_status.config(text=f"  Không tìm thấy mã SP nào từ clipboard trong bảng")
        return "break"

    tree.bind("<Control-a>", _select_all)
    tree.bind("<Control-c>", _copy_masp)
    tree.bind("<Control-v>", _paste_and_select)
    return _paste_and_select
