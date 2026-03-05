import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import subprocess
import shutil
import zipfile
import tempfile
import configparser
import json
import urllib.request
import urllib.parse

def _read_version():
    """Đọc version từ version.txt trong thư mục app"""
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    vf = os.path.join(app_dir, "version.txt")
    if os.path.exists(vf):
        try:
            with open(vf, "r", encoding="utf-8-sig") as f:
                return f.read().strip()
        except Exception:
            pass
    return "--"

VERSION = _read_version()

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

# ==================== API config ====================
API_BASE_PRICES = "https://nextsale-api.vemedim.vn/api/farm-price/customer-prices"
API_BASE_CUSTOMERS = "https://nextsale-api.vemedim.vn/api/customer/simple-list"
API_TOKEN = "7a98712bb4c31e2feb4f927a4206faa006bac054e506fe37c945a1cff05f5a1abcb4d0c9200ebaa400ad201ddce8d15b"

def get_app_dir():
    """Lấy thư mục chứa file .exe hoặc file .py"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# Khi khởi động: nếu có file .exe.new thì rename thay thế exe cũ
def _apply_pending_exe_update():
    if not getattr(sys, 'frozen', False):
        return
    exe_path = sys.executable
    new_path = exe_path + ".new"
    if os.path.exists(new_path):
        try:
            old_path = exe_path + ".old"
            if os.path.exists(old_path):
                os.remove(old_path)
            os.rename(exe_path, old_path)
            os.rename(new_path, exe_path)
            # Xóa file .old
            try:
                os.remove(old_path)
            except Exception:
                pass
            print("[UPDATE] Đã thay thế exe bằng bản mới")
        except Exception as e:
            print(f"[UPDATE] Không rename được exe: {e}")

_apply_pending_exe_update()
# Dữ liệu khách hàng từ API
ALL_CUSTOMERS = []  # [{"customerCode": ..., "customerName": ..., "saleOrg": ...}]
CURRENT_DATA = []   # Sản phẩm hiện tại từ API giá

# ==================== Loading overlay ====================
_loading_frame = None
_loading_label = None
_loading_anim_id = None
_loading_dots = 0

def show_loading(msg="Đang tải dữ liệu"):
    """Hiển thị overlay loading trên bảng."""
    global _loading_frame, _loading_label, _loading_dots
    hide_loading()  # Xóa cái cũ nếu có
    _loading_dots = 0
    _loading_frame = tk.Frame(root, bg="#f0f4f8")
    _loading_frame.place(relx=0.5, rely=0.55, anchor=tk.CENTER, width=300, height=80)
    _loading_label = tk.Label(
        _loading_frame, text=msg, font=("Segoe UI", 12),
        bg="#f0f4f8", fg="#2c3e50"
    )
    _loading_label.pack(expand=True)
    _animate_loading(msg)

def _animate_loading(base_msg):
    """Animation dấu chấm chạy."""
    global _loading_dots, _loading_anim_id
    if _loading_label and _loading_label.winfo_exists():
        _loading_dots = (_loading_dots % 3) + 1
        _loading_label.config(text=base_msg + "." * _loading_dots)
        _loading_anim_id = root.after(400, lambda: _animate_loading(base_msg))

def hide_loading():
    """Ẩn overlay loading."""
    global _loading_frame, _loading_label, _loading_anim_id
    if _loading_anim_id:
        root.after_cancel(_loading_anim_id)
        _loading_anim_id = None
    if _loading_frame:
        _loading_frame.destroy()
        _loading_frame = None
        _loading_label = None

def _api_get(url):
    """Gọi GET API với bearer token."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {API_TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

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
    # Trả về dạng "mãKH - tênKH" để dễ chọn
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
                })
            return result, data.get("customerName", ""), None
        else:
            return [], "", body.get("message", "Không có dữ liệu")
    except urllib.error.HTTPError as e:
        return [], "", f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return [], "", f"Lỗi kết nối: {e.reason}"
    except Exception as e:
        return [], "", str(e)

# Tải danh sách khách hàng khi khởi động (sẽ gọi trong thread sau khi UI sẵn sàng)
# fetch_customer_list() → chuyển sang _init_load()


# ==================== Autocomplete Entry ====================
class AutocompleteEntry(tk.Entry):
    def __init__(self, master, completions, on_select_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.completions = completions
        self.on_select_callback = on_select_callback
        self.lb = None
        self._hide_id = None
        self.bind("<KeyRelease>", self._on_key)
        self.bind("<FocusOut>", self._schedule_hide)
        self.bind("<Escape>", self._hide)

    def _on_key(self, event):
        if event.keysym == "Return":
            self._on_enter()
            return "break"
        if event.keysym in ("Down", "Up", "Escape"):
            if event.keysym == "Down" and self.lb:
                self.lb.focus_set()
                if self.lb.size() > 0:
                    self.lb.selection_set(0)
            return
        self._update_list()

    def _on_enter(self):
        """Enter: nếu chỉ 1 kết quả suggest → chọn luôn, nhiều hơn 1 → báo user."""
        text = self.get().strip().upper()
        if not text:
            return
        self._hide()
        matches = [c for c in self.completions if text in c.upper()]
        if len(matches) == 1:
            code = matches[0].split(" - ")[0].strip()
            self.delete(0, tk.END)
            self.insert(0, code)
            self.icursor(tk.END)
            if self.on_select_callback:
                self.on_select_callback(code)
        elif len(matches) > 1:
            # Nhiều kết quả → hiện dropdown để user chọn
            self._update_list()
        else:
            # Không tìm thấy → thử tìm chính xác với mã đã nhập
            if self.on_select_callback:
                self.on_select_callback(text)

    def _update_list(self):
        text = self.get().strip().upper()
        if not text:
            self._hide()
            return
        matches = [c for c in self.completions if text in c.upper()][:15]
        if not matches:
            self._hide()
            return
        if self.lb:
            self.lb.destroy()
        self.lb = tk.Listbox(
            self.winfo_toplevel(), font=("Segoe UI", 10),
            bg="white", fg="#2c3e50", selectbackground="#2980b9",
            selectforeground="white", bd=1, relief=tk.SOLID,
            highlightthickness=0, exportselection=False
        )
        for m in matches:
            self.lb.insert(tk.END, m)
        x = self.winfo_rootx() - self.winfo_toplevel().winfo_rootx()
        y = self.winfo_rooty() - self.winfo_toplevel().winfo_rooty() + self.winfo_height()
        w = max(self.winfo_width(), 350)
        h = min(len(matches), 8) * 22
        self.lb.place(x=x, y=y, width=w, height=h)
        self.lb.lift()
        self.lb.bind("<ButtonRelease-1>", self._on_select)
        self.lb.bind("<Return>", self._on_select)
        self.lb.bind("<Escape>", self._hide)
        self.lb.bind("<FocusOut>", self._hide)

    def _on_select(self, event=None):
        if self._hide_id:
            self.after_cancel(self._hide_id)
            self._hide_id = None
        if self.lb and self.lb.curselection():
            val = self.lb.get(self.lb.curselection())
            # Lấy mã KH (phần trước " - ")
            code = val.split(" - ")[0].strip()
            self.delete(0, tk.END)
            self.insert(0, code)
            self._hide()
            self.focus_set()
            self.icursor(tk.END)
            if self.on_select_callback:
                self.on_select_callback(code)

    def _schedule_hide(self, event=None):
        if self._hide_id:
            self.after_cancel(self._hide_id)
        self._hide_id = self.after(150, self._hide)

    def _hide(self, event=None):
        if self._hide_id:
            self.after_cancel(self._hide_id)
            self._hide_id = None
        if self.lb:
            self.lb.destroy()
            self.lb = None


# ==================== Hàm tìm kiếm (gọi API giá) ====================
def on_customer_selected(customer_code):
    """Khi user chọn một khách hàng từ autocomplete, gọi API lấy giá."""
    global CURRENT_DATA
    masp_filter = entry_masp.get().strip().upper()

    for row in tree.get_children():
        tree.delete(row)

    if not customer_code:
        CURRENT_DATA = []
        lbl_status.config(text="")
        return

    # Bỏ số 0 ở đầu mã KH khi gọi API
    api_code = customer_code.lstrip("0") or customer_code
    chinhanh_code = CHI_NHANH_MAP.get(cmb_chinhanh.get(), "2001")
    lbl_status.config(text="  Đang tải dữ liệu...")
    show_loading("Đang tải giá sản phẩm")
    root.update_idletasks()

    def _fetch():
        global CURRENT_DATA
        products, cust_name, error = fetch_prices_from_api(api_code, chinhanh_code)
        if error:
            root.after(0, lambda: hide_loading())
            root.after(0, lambda: lbl_status.config(text=f"  Lỗi: {error}"))
            CURRENT_DATA = []
            return
        CURRENT_DATA = products
        results = products
        if masp_filter:
            results = [r for r in results if masp_filter in r["masp"].upper()]
        root.after(0, lambda: hide_loading())
        root.after(0, lambda: _show_results(results, cust_name))

    threading.Thread(target=_fetch, daemon=True).start()

def _show_results(results, cust_name=""):
    for row in tree.get_children():
        tree.delete(row)
    for i, item in enumerate(results, start=1):
        gia_fmt = f"{item['gia']:,.0f}"
        tag = "even" if i % 2 == 0 else "odd"
        tree.insert("", tk.END, values=(i, item["makh"], item["masp"], item.get("tensp", ""), gia_fmt), tags=(tag,))
    name_txt = f" - {cust_name}" if cust_name else ""
    lbl_status.config(text=f"  Tìm thấy {len(results)} sản phẩm{name_txt}")

def filter_local(event=None):
    """Lọc local theo mã SP từ CURRENT_DATA (không gọi lại API)."""
    masp_filter = entry_masp.get().strip().upper()
    results = CURRENT_DATA
    if masp_filter:
        results = [r for r in results if masp_filter in r["masp"].upper()]
    _show_results(results)

# ==================== SAP Session quản lý ====================
SAP_SESSION = None  # Lưu session SAP để tái sử dụng

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


def do_update_price():
    """Đổ giá vào SAP cho các dòng đang chọn trong bảng."""
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Chưa chọn dòng", "Vui lòng chọn ít nhất một dòng trong bảng để đổ giá.")
        return

    # Thu thập thông tin các dòng đã chọn
    items = []
    for sel in selected:
        values = tree.item(sel, "values")
        # columns: stt(0), makh(1), masp(2), tensp(3), gia(4)
        items.append({
            "makh": values[1],
            "masp": values[2],
            "tensp": values[3],
            "gia": values[4].replace(",", ""),
            "gia_fmt": values[4],
            "ngaykt": "",
        })

    # Tạo nội dung xác nhận
    count = len(items)
    MAX_SHOW = 10
    detail_lines = [f"  {i+1}. KH: {it['makh']}  |  SP: {it['masp']}  |  Giá: {it['gia_fmt']}" for i, it in enumerate(items[:MAX_SHOW])]
    if count > MAX_SHOW:
        detail_lines.append(f"  ... và {count - MAX_SHOW} dòng nữa")
    detail = "\n".join(detail_lines)
    confirm = messagebox.askyesno(
        "Xác nhận đổ giá",
        f"Bạn có chắc muốn đổ giá {count} dòng vào SAP?\n\n{detail}",
    )
    if not confirm:
        return

    # Disable nút trong lúc xử lý
    btn_update.config(state=tk.DISABLED, text="Đang xử lý...")
    lbl_status.config(text=f"Đang xử lý {count} dòng...")
    root.update_idletasks()

    def _run():
        global SAP_SESSION
        try:
            from vk11 import updateMaterial

            session = _get_or_create_sap_session()
            print(session)
            if session == "MAX_SESSIONS":
                root.after(0, lambda: messagebox.showwarning(
                    "Quá giới hạn session",
                    "Số session SAP đã đạt giới hạn tối đa.\n\n"
                    "Vui lòng đóng bớt các cửa sổ SAP đang mở rồi thử lại."
                ))
                return
            if session is None:
                root.after(0, lambda: messagebox.showerror("Lỗi", "Không thể kết nối SAP. Kiểm tra lại cấu hình."))
                return

            # Gom theo mã KH và gọi updateMaterial với list
            from collections import defaultdict
            grouped = defaultdict(list)
            for it in items:
                grouped[it["makh"]].append({"masp": it["masp"], "gia": it["gia"], "ngaykt": it.get("ngaykt", "")})

            success = 0
            errors = []
            total = len(items)
            processed = 0
            for makh, mat_list in grouped.items():
                root.after(0, lambda mk=makh: lbl_status.config(text=f" Đang xử lý KH {mk} ({len(mat_list)} SP)..."))
                vkorg = CHI_NHANH_MAP.get(cmb_chinhanh.get(), "2001")
                results = updateMaterial(session, makh, mat_list, vkorg)
                for r in results:
                    processed += 1
                    if r["status"] == "ok":
                        success += 1
                    else:
                        errors.append(f"{makh}/{r['masp']}: {r['msg']}")
                    root.after(0, lambda p=processed: lbl_status.config(text=f"  Đã xử lý {p}/{total}..."))

            # Báo kết quả
            msg = f"Thành công: {success}/{count}"
            if errors:
                # Nếu tất cả lỗi có cùng message SAP → gộp thành 1 dòng
                unique_msgs = set()
                for e in errors:
                    # Lấy phần sau "SAP: " nếu có
                    if "| SAP: " in e:
                        unique_msgs.add(e.split("| SAP: ")[-1])
                    else:
                        unique_msgs.add(e.split(": ", 1)[-1] if ": " in e else e)
                if len(unique_msgs) == 1:
                    msg += f"\n\nLỗi ({len(errors)} SP): {unique_msgs.pop()}"
                else:
                    msg += f"\n\nLỗi ({len(errors)}):\n" + "\n".join(errors)
                root.after(0, lambda m=msg: messagebox.showwarning("Kết quả", m))
            root.after(0, lambda: lbl_status.config(text=f"  Hoàn tất: {success}/{count} thành công"))
        except Exception as ex:
            # Session lỗi → reset để lần sau tạo mới
            SAP_SESSION = None
            root.after(0, lambda e=ex: messagebox.showerror("Lỗi", f"Đổ giá thất bại:\n{e}"))
            root.after(0, lambda e=ex: lbl_status.config(text=f"  Lỗi: {e}"))
        finally:
            root.after(0, lambda: btn_update.config(state=tk.NORMAL, text="Đổ giá SAP"))

    threading.Thread(target=_run, daemon=True).start()


def on_enter_btn(e, color):
    e.widget.config(bg=color)


def on_leave_btn(e, color):
    e.widget.config(bg=color)


# ==================== Cập nhật phần mềm ====================
def update_app():
    """Kiểm tra và tải bản cập nhật từ shared folder"""

    # --- Tạo cửa sổ progress ---
    progress_win = tk.Toplevel(root)
    progress_win.title("Cập nhật phần mềm")
    progress_win.geometry("420x130")
    progress_win.resizable(False, False)
    progress_win.configure(bg=CARD_BG)
    progress_win.transient(root)
    progress_win.grab_set()
    # Căn giữa
    progress_win.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() - 420) // 2
    y = root.winfo_y() + (root.winfo_height() - 130) // 2
    progress_win.geometry(f"+{x}+{y}")

    lbl_progress = tk.Label(
        progress_win, text="Đang kiểm tra phiên bản...", font=("Segoe UI", 10),
        bg=CARD_BG, fg=TEXT_COLOR, anchor=tk.W,
    )
    lbl_progress.pack(fill=tk.X, padx=20, pady=(16, 4))

    progress_bar = ttk.Progressbar(progress_win, length=380, mode="determinate")
    progress_bar.pack(padx=20, pady=(0, 4))

    lbl_percent = tk.Label(
        progress_win, text="0%", font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_COLOR,
    )
    lbl_percent.pack(padx=20)

    progress_win.update()

    def _set_progress(text, value):
        lbl_progress.config(text=text)
        progress_bar["value"] = value
        lbl_percent.config(text=f"{int(value)}%")
        progress_win.update()

    try:
        # Đọc cấu hình update
        config = configparser.ConfigParser()
        config.read(os.path.join(get_app_dir(), "config.ini"))
        share_path = config.get("UPDATE", "share", fallback=r"\\172.0.1.103\kinhdoanh\DoGiaKD_Source")
        share_pass = config.get("UPDATE", "password", fallback="")

        print(f"[UPDATE] VERSION hiện tại: {VERSION}")
        print(f"[UPDATE] Share path: {share_path}")

        version_file = os.path.join(share_path, "version.txt")
        print(f"[UPDATE] Version file: {version_file}")
        _set_progress("Đang kết nối server...", 5)

        # Nếu chưa kết nối share, thử net use (chỉ dùng phần \\server\share)
        if not os.path.exists(version_file):
            print(f"[UPDATE] Không thấy version.txt, thử net use...")
            try:
                parts = share_path.strip("\\").split("\\")
                net_share = "\\\\" + parts[0] + "\\" + parts[1] if len(parts) >= 2 else share_path
                print(f"[UPDATE] net use \"{net_share}\"")
                result = subprocess.run(
                    f'net use "{net_share}" "{share_pass}" /persistent:no',
                    shell=True, capture_output=True, timeout=10, text=True,
                )
                print(f"[UPDATE] net use stdout: {result.stdout.strip()}")
                print(f"[UPDATE] net use stderr: {result.stderr.strip()}")
                print(f"[UPDATE] net use returncode: {result.returncode}")
            except Exception as e:
                print(f"[UPDATE] net use exception: {e}")
        else:
            print(f"[UPDATE] version.txt tìm thấy OK")

        _set_progress("Đang kiểm tra phiên bản...", 15)

        if not os.path.exists(version_file):
            print(f"[UPDATE] LỖI: Vẫn không thấy version.txt")
            progress_win.destroy()
            messagebox.showerror("Lỗi", f"Không thể kết nối server cập nhật:\n{share_path}")
            return

        # Đọc phiên bản mới nhất (utf-8-sig để bỏ BOM nếu có)
        with open(version_file, "r", encoding="utf-8-sig") as f:
            latest_version = f.read().strip()
        print(f"[UPDATE] Phiên bản mới nhất trên server: {repr(latest_version)}")
        print(f"[UPDATE] Phiên bản hiện tại: {repr(VERSION)}")

        def _parse_ver(v):
            """Parse version string thành tuple số để so sánh chính xác."""
            try:
                return tuple(int(x) for x in v.split("."))
            except Exception:
                return (0,)

        if _parse_ver(latest_version) <= _parse_ver(VERSION):
            print(f"[UPDATE] Đang dùng bản mới nhất, không cần cập nhật")
            progress_win.destroy()
            messagebox.showinfo("Cập nhật", f"Bạn đang dùng phiên bản mới nhất ({VERSION})")
            return

        _set_progress(f"Tìm thấy phiên bản mới: {latest_version}", 20)

        # Tìm file zip: thử nhiều tên khác nhau
        ver_parts = latest_version.split(".")
        zip_candidates = [
            "DoGiaKD.zip",
            f"DoGiaKD_v{latest_version}.zip",
            f"DoGiaKD_v{'.'.join(ver_parts[:2])}.zip" if len(ver_parts) >= 2 else None,
            f"DoGiaKD_v{ver_parts[0]}.zip" if ver_parts else None,
        ]
        zip_file = None
        for name in zip_candidates:
            if name is None:
                continue
            candidate = os.path.join(share_path, name)
            exists = os.path.exists(candidate)
            print(f"[UPDATE] Thử tìm: {candidate} -> {exists}")
            if exists:
                zip_file = candidate
                break
        if not zip_file:
            print(f"[UPDATE] LỖI: Không tìm thấy file zip")
            progress_win.destroy()
            messagebox.showerror("Lỗi", "Không tìm thấy file cập nhật trên server")
            return

        zip_size = os.path.getsize(zip_file)
        print(f"[UPDATE] Tìm thấy zip: {zip_file} ({zip_size / 1024 / 1024:.1f} MB)")
        _set_progress(f"Đang tải ({zip_size / 1024 / 1024:.1f} MB)...", 25)

        app_dir = get_app_dir()
        temp_dir = os.path.join(tempfile.gettempdir(), "DoGiaKD_update")
        print(f"[UPDATE] App dir: {app_dir}")
        print(f"[UPDATE] Temp dir: {temp_dir}")

        # Dọn thư mục tạm
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)

        # Copy zip về thư mục tạm (theo chunk để hiện progress)
        print(f"[UPDATE] Đang copy zip...")
        temp_zip = os.path.join(temp_dir, "DoGiaKD.zip")
        copied = 0
        chunk_size = 1024 * 256  # 256KB
        with open(zip_file, "rb") as src, open(temp_zip, "wb") as dst:
            while True:
                chunk = src.read(chunk_size)
                if not chunk:
                    break
                dst.write(chunk)
                copied += len(chunk)
                pct = 25 + int((copied / zip_size) * 65)  # 25% -> 90%
                _set_progress(
                    f"Đang tải: {copied / 1024 / 1024:.1f} / {zip_size / 1024 / 1024:.1f} MB",
                    min(pct, 90),
                )
        print(f"[UPDATE] Copy xong: {temp_zip} ({os.path.getsize(temp_zip) / 1024 / 1024:.1f} MB)")

        _set_progress("Đang giải nén...", 92)

        # Giải nén ngay trong temp_dir
        import zipfile
        extract_dir = os.path.join(temp_dir, "extracted")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        with zipfile.ZipFile(temp_zip, "r") as zf:
            zf.extractall(extract_dir)
        print(f"[UPDATE] Giải nén xong: {extract_dir}")

        # Xác định thư mục nguồn
        src_dir = extract_dir
        sub = os.path.join(extract_dir, "DoGiaKD")
        if os.path.isdir(sub):
            src_dir = sub

        _set_progress("Đang cập nhật file...", 95)

        # Copy file từ extracted sang app_dir
        app_dir = get_app_dir()
        exe_name = os.path.basename(sys.executable) if getattr(sys, "frozen", False) else ""
        for root_dir, dirs, files in os.walk(src_dir):
            rel = os.path.relpath(root_dir, src_dir)
            dest_dir = os.path.join(app_dir, rel)
            os.makedirs(dest_dir, exist_ok=True)
            for fname in files:
                src_file = os.path.join(root_dir, fname)
                dst_file = os.path.join(dest_dir, fname)
                # Bỏ qua exe đang chạy (không thể overwrite chính nó)
                if fname.lower() == exe_name.lower():
                    # Copy thành .new, sẽ rename khi khởi động lại
                    try:
                        shutil.copy2(src_file, dst_file + ".new")
                    except Exception:
                        pass
                    continue
                try:
                    shutil.copy2(src_file, dst_file)
                except Exception as copy_err:
                    print(f"[UPDATE] Không copy được: {fname} -> {copy_err}")

        print(f"[UPDATE] Copy file xong!")

        # Dọn dẹp
        _set_progress("Đang dọn dẹp...", 98)
        shutil.rmtree(extract_dir, ignore_errors=True)
        try:
            os.remove(temp_zip)
        except Exception:
            pass

        _set_progress(f"Cập nhật thành công! Phiên bản {latest_version}", 100)
        progress_win.update()
        import time
        time.sleep(0.5)

        progress_win.destroy()
        messagebox.showinfo(
            "Cập nhật thành công",
            f"Đã cập nhật lên phiên bản {latest_version}.\n\n"
            "Vui lòng tắt và mở lại ứng dụng để sử dụng phiên bản mới."
        )

    except Exception as ex:
        print(f"[UPDATE] EXCEPTION: {ex}")
        import traceback
        traceback.print_exc()
        try:
            progress_win.destroy()
        except Exception:
            pass
        messagebox.showerror("Lỗi", f"Cập nhật thất bại:\n{ex}")
        lbl_status.config(text="  Cập nhật thất bại")


# ==================== Giao diện ====================
root = tk.Tk()
root.title("Đơn Giá Khách Hàng - Version " + VERSION)
root.geometry("980x760")
root.minsize(600, 400)
root.configure(bg=BG_COLOR)

# Icon cửa sổ
_icon_path = os.path.join(get_app_dir(), "logo.ico")
if os.path.exists(_icon_path):
    root.iconbitmap(_icon_path)

# ---- Header ----
header = tk.Frame(root, bg=HEADER_BG, height=56)
header.pack(fill=tk.X)
header.pack_propagate(False)

lbl_title = tk.Label(
    header,
    text="QUẢN LÝ ĐỔ GIÁ TRỰC TIẾP",
    font=("Segoe UI", 16, "bold"),
    bg=HEADER_BG,
    fg=HEADER_FG,
)
lbl_title.pack(side=tk.LEFT, padx=20, pady=10)

BTN_UPDATE_APP = "#e67e22"
BTN_UPDATE_APP_HOVER = "#f39c12"
btn_update_app = tk.Button(
    header, text="Cập nhật phiên bản mới ⬇", font=("Segoe UI", 10, "bold"),
    bg=BTN_UPDATE_APP, fg="white", activebackground=BTN_UPDATE_APP_HOVER, activeforeground="white",
    relief=tk.FLAT, cursor="hand2", padx=8, pady=2,
    command=update_app,
)
btn_update_app.pack(side=tk.RIGHT, padx=(4, 16), pady=10)
btn_update_app.bind("<Enter>", lambda e: on_enter_btn(e, BTN_UPDATE_APP_HOVER))
btn_update_app.bind("<Leave>", lambda e: on_leave_btn(e, BTN_UPDATE_APP))

# ---- Tab bar ----
TAB_ACTIVE_BG = "#ffffff"
TAB_INACTIVE_BG = "#c8d6e5"
TAB_ACTIVE_FG = HEADER_BG
TAB_INACTIVE_FG = "#5d6d7e"

tab_bar = tk.Frame(root, bg="#dce6f0", height=40)
tab_bar.pack(fill=tk.X)
tab_bar.pack_propagate(False)

current_tab = "A"

def switch_tab(tab_name):
    global current_tab
    if current_tab == tab_name:
        return
    current_tab = tab_name
    # Ẩn tất cả frame
    for f in (frame_a, frame_b, frame_c):
        f.pack_forget()
    # Reset tất cả tab button về inactive
    for btn in (tab_btn_a, tab_btn_b, tab_btn_c):
        btn.config(bg=TAB_INACTIVE_BG, fg=TAB_INACTIVE_FG, font=("Segoe UI", 10))
    # Hiện frame và active button tương ứng
    if tab_name == "A":
        frame_a.pack(fill=tk.BOTH, expand=True)
        tab_btn_a.config(bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG, font=("Segoe UI", 10, "bold"))
    elif tab_name == "B":
        frame_b.pack(fill=tk.BOTH, expand=True)
        tab_btn_b.config(bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG, font=("Segoe UI", 10, "bold"))
    elif tab_name == "C":
        frame_c.pack(fill=tk.BOTH, expand=True)
        tab_btn_c.config(bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG, font=("Segoe UI", 10, "bold"))

tab_btn_a = tk.Button(
    tab_bar, text="  Đổ giá trang trại", font=("Segoe UI", 10, "bold"),
    bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG,
    relief=tk.FLAT, cursor="hand2", bd=0,
    command=lambda: switch_tab("A"),
)
tab_btn_a.pack(side=tk.LEFT, padx=(16, 2), pady=(6, 0), ipady=4, ipadx=10)

tab_btn_b = tk.Button(
    tab_bar, text="  Đổ giá đại lý", font=("Segoe UI", 10),
    bg=TAB_INACTIVE_BG, fg=TAB_INACTIVE_FG,
    relief=tk.FLAT, cursor="hand2", bd=0,
    command=lambda: switch_tab("B"),
)
tab_btn_b.pack(side=tk.LEFT, padx=(2, 0), pady=(6, 0), ipady=4, ipadx=10)

tab_btn_c = tk.Button(
    tab_bar, text="  Đổ giá nhóm KH", font=("Segoe UI", 10),
    bg=TAB_INACTIVE_BG, fg=TAB_INACTIVE_FG,
    relief=tk.FLAT, cursor="hand2", bd=0,
    command=lambda: switch_tab("C"),
)
tab_btn_c.pack(side=tk.LEFT, padx=(2, 0), pady=(6, 0), ipady=4, ipadx=10)

# ---- Content frames ----
frame_a = tk.Frame(root, bg=BG_COLOR)
frame_a.pack(fill=tk.BOTH, expand=True)

frame_b = tk.Frame(root, bg=BG_COLOR)
# frame_b starts hidden (not packed)

frame_c = tk.Frame(root, bg=BG_COLOR)
# frame_c starts hidden (not packed)

# ---- Tab A: Card tìm kiếm ----
card_search = tk.Frame(frame_a, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
card_search.pack(fill=tk.X, padx=16, pady=(16, 8))

inner_search = tk.Frame(card_search, bg=CARD_BG)
inner_search.pack(fill=tk.X, padx=20, pady=16)

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

# Row 0: Labels
tk.Label(inner_search, text="Chi nhánh", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
    row=0, column=0, padx=(0, 24), sticky=tk.W
)
tk.Label(inner_search, text="Mã KH", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
    row=0, column=1, padx=(0, 24), sticky=tk.W
)
tk.Label(inner_search, text="Mã SP", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
    row=0, column=2, padx=(0, 24), sticky=tk.W
)

# Row 1: Inputs & Buttons
cmb_chinhanh = ttk.Combobox(
    inner_search, values=list(CHI_NHANH_MAP.keys()), width=20, font=("Segoe UI", 11),
    state="readonly"
)
cmb_chinhanh.current(0)
cmb_chinhanh.grid(row=1, column=0, padx=(0, 24), pady=(4, 0), ipady=3, sticky=tk.W)
def _on_chinhanh_change(event=None):
    # Cập nhật gợi ý mã KH theo chi nhánh
    chinhanh_code = CHI_NHANH_MAP.get(cmb_chinhanh.get(), "")
    entry_makh.completions = get_customer_completions(chinhanh_code)
    # Nếu đã có mã KH, gọi lại API giá với chi nhánh mới
    makh = entry_makh.get().strip()
    if makh:
        on_customer_selected(makh)
cmb_chinhanh.bind("<<ComboboxSelected>>", _on_chinhanh_change)

# Lấy saleOrg mặc định của chi nhánh đầu tiên
_default_sale_org = CHI_NHANH_MAP.get(list(CHI_NHANH_MAP.keys())[0], "")

entry_makh = AutocompleteEntry(
    inner_search, completions=get_customer_completions(_default_sale_org),
    on_select_callback=on_customer_selected,
    width=18, font=("Segoe UI", 11), relief=tk.FLAT,
    bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT
)
entry_makh.grid(row=1, column=1, padx=(0, 24), pady=(4, 0), ipady=5, sticky=tk.W)

entry_masp = tk.Entry(
    inner_search, width=18, font=("Segoe UI", 11), relief=tk.FLAT,
    bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT
)
entry_masp.grid(row=1, column=2, padx=(0, 24), pady=(4, 0), ipady=5, sticky=tk.W)
entry_masp.bind("<KeyRelease>", filter_local)

BTN_SUCCESS = "#27ae60"
BTN_SUCCESS_HOVER = "#2ecc71"
btn_update = tk.Button(
    inner_search, text="Đổ giá SAP", font=("Segoe UI", 10, "bold"),
    bg=BTN_SUCCESS, fg="white", activebackground=BTN_SUCCESS_HOVER, activeforeground="white",
    relief=tk.FLAT, cursor="hand2", padx=16, pady=4, command=do_update_price,
)
btn_update.grid(row=1, column=3, padx=(0, 8), pady=(4, 0), ipady=3)
btn_update.bind("<Enter>", lambda e: on_enter_btn(e, BTN_SUCCESS_HOVER))
btn_update.bind("<Leave>", lambda e: on_leave_btn(e, BTN_SUCCESS))

# ---- Tab A: Card bảng dữ liệu ----
card_table = tk.Frame(frame_a, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
card_table.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 8))

# Style cho Treeview
style = ttk.Style()
style.theme_use("clam")

style.configure(
    "Custom.Treeview",
    background=ROW_EVEN,
    foreground=TEXT_COLOR,
    fieldbackground=ROW_EVEN,
    font=("Segoe UI", 10),
    rowheight=32,
    borderwidth=0,
)
style.configure(
    "Custom.Treeview.Heading",
    background=HEADER_BG,
    foreground=HEADER_FG,
    font=("Segoe UI", 10, "bold"),
    relief=tk.FLAT,
    borderwidth=0,
    padding=(0, 6),
)
style.map(
    "Custom.Treeview.Heading",
    background=[("active", "#264e78")],
)
style.map(
    "Custom.Treeview",
    background=[("selected", ROW_SELECT)],
    foreground=[("selected", TEXT_COLOR)],
)
style.configure(
    "Custom.Vertical.TScrollbar",
    troughcolor="#f0f4f8",
    background="#b0c4de",
    arrowcolor=HEADER_BG,
    borderwidth=0,
    relief=tk.FLAT,
)

# Treeview
tbl_frame = tk.Frame(card_table, bg=CARD_BG)
tbl_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

columns = ("stt", "makh", "masp", "tensp", "gia")
tree = ttk.Treeview(tbl_frame, columns=columns, show="headings", height=14, style="Custom.Treeview", selectmode="extended")

tree.heading("stt", text="STT")
tree.heading("makh", text="Mã KH")
tree.heading("masp", text="Mã SP")
tree.heading("tensp", text="Tên SP")
tree.heading("gia", text="Giá (VNĐ)")

tree.column("stt", width=50, anchor=tk.CENTER, minwidth=40)
tree.column("makh", width=120, anchor=tk.CENTER, minwidth=80)
tree.column("masp", width=120, anchor=tk.CENTER, minwidth=80)
tree.column("tensp", width=250, anchor=tk.W, minwidth=150)
tree.column("gia", width=130, anchor=tk.E, minwidth=80)

# Tags cho row xen kẽ
tree.tag_configure("odd", background=ROW_ODD)
tree.tag_configure("even", background=ROW_EVEN)

# Scrollbar (dùng grid để scrollbar không chồng lên cột cuối)
tbl_frame.columnconfigure(0, weight=1)
tbl_frame.rowconfigure(0, weight=1)
scrollbar = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL, command=tree.yview, style="Custom.Vertical.TScrollbar")
tree.configure(yscrollcommand=scrollbar.set)
tree.grid(row=0, column=0, sticky="nsew")
scrollbar.grid(row=0, column=1, sticky="ns")

# ---- Tab A: Status bar ----
status_bar = tk.Frame(frame_a, bg=STATUS_BG, height=32)
status_bar.pack(fill=tk.X, padx=16, pady=(0, 12))
status_bar.pack_propagate(False)

lbl_status = tk.Label(status_bar, text="", font=("Segoe UI", 9), bg=STATUS_BG, fg="#5d6d7e", anchor=tk.W)
lbl_status.pack(fill=tk.X, padx=8, pady=5)

# ---- Tab B: Đổ giá khách hàng Nor/Vip ----
CURRENT_DATA_B = []  # Dữ liệu items cho tab B
CURRENT_HEADER_B = {}  # Header info cho tab B

def fetch_sale_order(sale_order):
    """Gọi API lấy chi tiết Sale Order."""
    url = f"https://nextsale-api.vemedim.vn/api/sale-order/{sale_order}"
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

def on_search_sale_order(event=None):
    """Khi user nhấn Enter trên ô Sale Order."""
    global CURRENT_DATA_B, CURRENT_HEADER_B
    so = entry_so.get().strip()
    if not so:
        return

    for row in tree_b.get_children():
        tree_b.delete(row)
    lbl_status_b.config(text="  Đang tải dữ liệu...")
    show_loading_b("Đang tải Sale Order")
    root.update_idletasks()

    def _fetch():
        global CURRENT_DATA_B, CURRENT_HEADER_B
        data, error = fetch_sale_order(so)
        if error:
            root.after(0, lambda: hide_loading_b())
            root.after(0, lambda: lbl_status_b.config(text=f"  Lỗi: {error}"))
            CURRENT_DATA_B = []
            CURRENT_HEADER_B = {}
            return
        header = data.get("header", {})
        items = data.get("items", [])
        items_price = data.get("items_price", [])
        CURRENT_HEADER_B = header

        warnings = data.get("warnings", None)
        order_summary = data.get("orderSummary", None)

        # Tạo map giá mới + note từ items_price theo MATNR
        price_map = {}
        for ip in items_price:
            matnr = ip.get("MATNR", "").lstrip("0")
            price_map[matnr] = {"net": ip.get("NET", 0), "note": ip.get("note", "")}

        # Gộp items + giá mới
        result = []
        for it in items:
            matnr_raw = it.get("MATNR", "")
            matnr = matnr_raw.lstrip("0")
            dongia = float(it.get("NETPR", 0))
            gia_cu = float(it.get("NETWR", 0))
            pm = price_map.get(matnr, {})
            gia_moi = pm.get("net", "") if pm else ""
            dieu_kien = pm.get("note", "") if pm else ""
            result.append({
                "masp": matnr,
                "tensp": it.get("ARKTX", ""),
                "soluong": it.get("KWMENG", "0").replace(".000", ""),
                "dongia": dongia,
                "gia_cu": gia_cu,
                "gia_moi": gia_moi,
                "dieu_kien": dieu_kien,
            })
        CURRENT_DATA_B = result

        cust_info = f"{header.get('KUNNR', '').lstrip('0')} - {header.get('NAME1', '')}"
        branch = header.get("VKORG_TEXT", "")
        root.after(0, lambda: hide_loading_b())
        root.after(0, lambda: _show_results_b(result, cust_info, branch, warnings, order_summary))

    threading.Thread(target=_fetch, daemon=True).start()

def _show_results_b(results, cust_info="", branch="", warnings=None, order_summary=None):
    for row in tree_b.get_children():
        tree_b.delete(row)
    # Lọc bỏ dòng thiếu giá mới
    filtered = [item for item in results if item['gia_moi'] not in ("", None)]
    for i, item in enumerate(filtered, start=1):
        dongia_fmt = f"{item['dongia']:,.0f}" if item['dongia'] else ""
        gia_cu_fmt = f"{item['gia_cu']:,.0f}" if item['gia_cu'] else ""
        gia_moi_fmt = f"{item['gia_moi']:,.0f}"
        dieu_kien = item.get("dieu_kien", "")
        tag = "even" if i % 2 == 0 else "odd"
        tree_b.insert("", tk.END, values=(
            i, item["masp"], item["tensp"], item["soluong"], dongia_fmt, gia_cu_fmt, gia_moi_fmt, dieu_kien
        ), tags=(tag,))
    info_txt = f"  SO: {entry_so.get().strip()}"
    if cust_info:
        info_txt += f"  |  KH: {cust_info}"
    if branch:
        info_txt += f"  |  {branch}"
    info_txt += f"  |  {len(filtered)} sản phẩm"
    lbl_status_b.config(text=info_txt)
    # Hiện order summary
    if order_summary and isinstance(order_summary, dict):
        summary_msg = order_summary.get("message", "")
        lbl_summary_b.config(text=summary_msg if summary_msg else "")
    else:
        lbl_summary_b.config(text="")
    # Hiện warning (lấy phần tử đầu tiên của mảng)
    if warnings:
        warn_text = warnings[0] if isinstance(warnings, list) and len(warnings) > 0 else str(warnings)
        lbl_warning_b.config(text=f"⚠ {warn_text}")
        lbl_warning_b.grid(row=2, column=0, columnspan=3, padx=(0, 0), pady=(4, 0), sticky=tk.W)
    else:
        lbl_warning_b.config(text="")
        lbl_warning_b.grid_remove()

# Loading overlay cho Tab B
_loading_frame_b = None
_loading_label_b = None
_loading_anim_id_b = None
_loading_dots_b = 0

def show_loading_b(msg="Đang tải dữ liệu"):
    global _loading_frame_b, _loading_label_b, _loading_dots_b
    hide_loading_b()
    _loading_dots_b = 0
    _loading_frame_b = tk.Frame(frame_b, bg=BG_COLOR)
    _loading_frame_b.place(relx=0.5, rely=0.55, anchor=tk.CENTER, width=300, height=80)
    _loading_label_b = tk.Label(
        _loading_frame_b, text=msg, font=("Segoe UI", 12),
        bg=BG_COLOR, fg=TEXT_COLOR
    )
    _loading_label_b.pack(expand=True)
    _animate_loading_b(msg)

def _animate_loading_b(base_msg):
    global _loading_dots_b, _loading_anim_id_b
    if _loading_label_b and _loading_label_b.winfo_exists():
        _loading_dots_b = (_loading_dots_b % 3) + 1
        _loading_label_b.config(text=base_msg + "." * _loading_dots_b)
        _loading_anim_id_b = root.after(400, lambda: _animate_loading_b(base_msg))

def hide_loading_b():
    global _loading_frame_b, _loading_label_b, _loading_anim_id_b
    if _loading_anim_id_b:
        root.after_cancel(_loading_anim_id_b)
        _loading_anim_id_b = None
    if _loading_frame_b:
        _loading_frame_b.destroy()
        _loading_frame_b = None
        _loading_label_b = None

def do_update_price_b():
    """Đổ giá SAP cho Tab B dùng updateMaterialV2."""
    selected = tree_b.selection()
    if not selected:
        messagebox.showwarning("Chưa chọn dòng", "Vui lòng chọn ít nhất một dòng trong bảng để đổ giá.")
        return

    items = []
    for sel in selected:
        values = tree_b.item(sel, "values")
        # columns: stt(0), masp(1), tensp(2), soluong(3), dongia(4), gia_cu(5), gia_moi(6), dieu_kien(7)
        gia_moi = values[6].replace(",", "").strip()
        if not gia_moi:
            continue
        items.append({
            "masp": values[1],
            "tensp": values[2],
            "gia": gia_moi,
            "gia_moi_fmt": values[5],
        })

    if not items:
        messagebox.showwarning("Không có giá mới", "Các dòng đã chọn không có giá mới.")
        return

    # Lấy thông tin từ header
    customer_code = CURRENT_HEADER_B.get("KUNNR", "").lstrip("0")
    sales_org = CURRENT_HEADER_B.get("VKORG", "2001")
    customer_name = CURRENT_HEADER_B.get("NAME1", "")

    count = len(items)
    MAX_SHOW = 10
    detail_lines = [f"  {i+1}. SP: {it['masp']}  |  Giá mới: {it['gia_moi_fmt']}" for i, it in enumerate(items[:MAX_SHOW])]
    if count > MAX_SHOW:
        detail_lines.append(f"  ... và {count - MAX_SHOW} dòng nữa")
    detail = "\n".join(detail_lines)
    confirm = messagebox.askyesno(
        "Xác nhận đổ giá",
        f"KH: {customer_code} - {customer_name}\nChi nhánh: {sales_org}\n\n"
        f"Đổ giá {count} sản phẩm?\n\n{detail}",
    )
    if not confirm:
        return

    btn_update_b.config(state=tk.DISABLED, text="Đang xử lý...")
    lbl_status_b.config(text=f"  Đang xử lý {count} dòng...")
    root.update_idletasks()

    def _run():
        global SAP_SESSION
        try:
            from vk11 import updateMaterialV2

            session = _get_or_create_sap_session()
            if session == "MAX_SESSIONS":
                root.after(0, lambda: messagebox.showwarning(
                    "Quá giới hạn session",
                    "Số session SAP đã đạt giới hạn tối đa.\n\n"
                    "Vui lòng đóng bớt các cửa sổ SAP đang mở rồi thử lại."
                ))
                return
            if session is None:
                root.after(0, lambda: messagebox.showerror("Lỗi", "Không thể kết nối SAP. Kiểm tra lại cấu hình."))
                return

            mat_list = [{"masp": it["masp"], "gia": it["gia"]} for it in items]
            results = updateMaterialV2(session, customer_code, mat_list, sales_org)

            success = 0
            errors = []
            for i, r in enumerate(results):
                if r["status"] == "ok":
                    success += 1
                else:
                    errors.append(f"{r['masp']}: {r['msg']}")
                root.after(0, lambda p=i+1: lbl_status_b.config(text=f"  Đã xử lý {p}/{count}..."))

            msg = f"Thành công: {success}/{count}"
            if errors:
                unique_msgs = set()
                for e in errors:
                    if "| SAP: " in e:
                        unique_msgs.add(e.split("| SAP: ")[-1])
                    else:
                        unique_msgs.add(e.split(": ", 1)[-1] if ": " in e else e)
                if len(unique_msgs) == 1:
                    msg += f"\n\nLỗi ({len(errors)} SP): {unique_msgs.pop()}"
                else:
                    msg += f"\n\nLỗi ({len(errors)}):\n" + "\n".join(errors)
                root.after(0, lambda m=msg: messagebox.showwarning("Kết quả", m))
            root.after(0, lambda: lbl_status_b.config(text=f"  Hoàn tất: {success}/{count} thành công"))
        except Exception as ex:
            SAP_SESSION = None
            root.after(0, lambda e=ex: messagebox.showerror("Lỗi", f"Đổ giá thất bại:\n{e}"))
            root.after(0, lambda e=ex: lbl_status_b.config(text=f"  Lỗi: {e}"))
        finally:
            root.after(0, lambda: btn_update_b.config(state=tk.NORMAL, text="Đổ giá SAP"))

    threading.Thread(target=_run, daemon=True).start()

# Tab B: Card tìm kiếm
card_search_b = tk.Frame(frame_b, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
card_search_b.pack(fill=tk.X, padx=16, pady=(16, 8))

inner_search_b = tk.Frame(card_search_b, bg=CARD_BG)
inner_search_b.pack(fill=tk.X, padx=20, pady=16)

tk.Label(inner_search_b, text="Sale Order", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
    row=0, column=0, padx=(0, 24), sticky=tk.W
)

entry_so = tk.Entry(
    inner_search_b, width=24, font=("Segoe UI", 11), relief=tk.FLAT,
    bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT
)
entry_so.grid(row=1, column=0, padx=(0, 24), pady=(4, 0), ipady=5, sticky=tk.W)
entry_so.bind("<Return>", on_search_sale_order)

btn_update_b = tk.Button(
    inner_search_b, text="Đổ giá SAP", font=("Segoe UI", 10, "bold"),
    bg=BTN_SUCCESS, fg="white", activebackground=BTN_SUCCESS_HOVER, activeforeground="white",
    relief=tk.FLAT, cursor="hand2", padx=16, pady=4, command=do_update_price_b,
)
btn_update_b.grid(row=1, column=1, padx=(0, 8), pady=(4, 0), ipady=3)
btn_update_b.bind("<Enter>", lambda e: on_enter_btn(e, BTN_SUCCESS_HOVER))
btn_update_b.bind("<Leave>", lambda e: on_leave_btn(e, BTN_SUCCESS))

# Tab B: Summary + Warning hiện cùng dòng với nút Đổ giá SAP
lbl_summary_b = tk.Label(inner_search_b, text="", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg="#2e7d32", anchor=tk.W)
lbl_summary_b.grid(row=1, column=2, padx=(16, 0), pady=(4, 0), sticky=tk.W)

lbl_warning_b = tk.Label(inner_search_b, text="", font=("Segoe UI", 9), bg=CARD_BG, fg="#c62828", anchor=tk.W)
# Không grid ngay - chỉ grid khi có warning

# Tab B: Card bảng dữ liệu
card_table_b = tk.Frame(frame_b, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
card_table_b.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 8))

tbl_frame_b = tk.Frame(card_table_b, bg=CARD_BG)
tbl_frame_b.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

columns_b = ("stt", "masp", "tensp", "soluong", "dongia", "gia_cu", "gia_moi", "dieu_kien")
tree_b = ttk.Treeview(tbl_frame_b, columns=columns_b, show="headings", height=14, style="Custom.Treeview", selectmode="extended")

tree_b.heading("stt", text="STT")
tree_b.heading("masp", text="Mã SP")
tree_b.heading("tensp", text="Tên SP")
tree_b.heading("soluong", text="Số lượng")
tree_b.heading("dongia", text="Giá cũ")
tree_b.heading("gia_cu", text="Tổng")
tree_b.heading("gia_moi", text="Giá mới")
tree_b.heading("dieu_kien", text="Điều kiện")

tree_b.column("stt", width=50, anchor=tk.CENTER, minwidth=40)
tree_b.column("masp", width=120, anchor=tk.CENTER, minwidth=80)
tree_b.column("tensp", width=200, anchor=tk.W, minwidth=130)
tree_b.column("soluong", width=65, anchor=tk.CENTER, minwidth=50)
tree_b.column("dongia", width=85, anchor=tk.E, minwidth=65)
tree_b.column("gia_cu", width=85, anchor=tk.E, minwidth=65)
tree_b.column("gia_moi", width=85, anchor=tk.E, minwidth=65)
tree_b.column("dieu_kien", width=120, anchor=tk.W, minwidth=80)

tree_b.tag_configure("odd", background=ROW_ODD)
tree_b.tag_configure("even", background=ROW_EVEN)

# Scrollbar (dùng grid để scrollbar không chồng lên cột cuối)
tbl_frame_b.columnconfigure(0, weight=1)
tbl_frame_b.rowconfigure(0, weight=1)
scrollbar_b = ttk.Scrollbar(tbl_frame_b, orient=tk.VERTICAL, command=tree_b.yview, style="Custom.Vertical.TScrollbar")
tree_b.configure(yscrollcommand=scrollbar_b.set)
tree_b.grid(row=0, column=0, sticky="nsew")
scrollbar_b.grid(row=0, column=1, sticky="ns")

# Tab B: Status bar
status_bar_b = tk.Frame(frame_b, bg=STATUS_BG, height=32)
status_bar_b.pack(fill=tk.X, padx=16, pady=(0, 12))
status_bar_b.pack_propagate(False)

lbl_status_b = tk.Label(status_bar_b, text="", font=("Segoe UI", 9), bg=STATUS_BG, fg="#5d6d7e", anchor=tk.W)
lbl_status_b.pack(fill=tk.X, padx=8, pady=5)

# Ctrl+A select all cho Tab B
def select_all_b(event):
    tree_b.selection_set(tree_b.get_children())
    return "break"
tree_b.bind("<Control-a>", select_all_b)

# Enter trên tree_b: nếu có selection thì gọi đổ giá SAP luôn
def on_enter_tree_b(event):
    if tree_b.selection():
        do_update_price_b()
    return "break"
tree_b.bind("<Return>", on_enter_tree_b)

# Ctrl+V paste list mã SP để tự select trong Tab B
def paste_and_select_b(event):
    try:
        clipboard = root.clipboard_get().strip()
    except:
        return "break"
    import re
    masp_list = [x.strip().upper() for x in re.split(r'[\n\r\t,;\s]+', clipboard) if x.strip()]
    if not masp_list:
        return "break"
    masp_set = set(masp_list)
    masp_set_stripped = set(m.lstrip("0") for m in masp_list)
    tree_b.selection_remove(*tree_b.selection())
    matched = []
    for item_id in tree_b.get_children():
        values = tree_b.item(item_id, "values")
        masp_val = values[1].strip().upper()  # cột masp ở index 1
        if masp_val in masp_set or masp_val.lstrip("0") in masp_set_stripped:
            matched.append(item_id)
    if matched:
        tree_b.selection_set(matched)
        unmatched = [iid for iid in tree_b.get_children() if iid not in matched]
        for idx, iid in enumerate(matched + unmatched):
            tree_b.move(iid, "", idx)
            vals = list(tree_b.item(iid, "values"))
            vals[0] = idx + 1
            tag = "even" if (idx + 1) % 2 == 0 else "odd"
            tree_b.item(iid, values=vals, tags=(tag,))
        tree_b.see(matched[0])
        lbl_status_b.config(text=f"  Đã chọn {len(matched)}/{len(masp_list)} mã SP từ clipboard")
    else:
        lbl_status_b.config(text=f"  Không tìm thấy mã SP nào từ clipboard trong bảng")
    return "break"
tree_b.bind("<Control-v>", paste_and_select_b)

# Bind Enter key: chỉ xử lý khi focus ở entry_makh (AutocompleteEntry tự handle Enter)
# Không bind global Enter nữa để tránh chồng chéo với AutocompleteEntry._on_enter

# Ctrl+A để select all trong bảng
def select_all(event):
    tree.selection_set(tree.get_children())
    return "break"
tree.bind("<Control-a>", select_all)

# Ctrl+V để paste list mã SP và tự select các dòng khớp
def paste_and_select(event):
    try:
        clipboard = root.clipboard_get().strip()
    except:
        return "break"
    # Tách list mã SP từ clipboard (theo dòng, tab, dấu phẩy, khoảng trắng)
    import re
    masp_list = [x.strip().upper() for x in re.split(r'[\n\r\t,;\s]+', clipboard) if x.strip()]
    if not masp_list:
        return "break"
    # Tạo set để so sánh nhanh (bao gồm cả dạng bỏ leading zeros)
    masp_set = set(masp_list)
    masp_set_stripped = set(m.lstrip("0") for m in masp_list)
    # Tìm và select các dòng có mã SP nằm trong list
    tree.selection_remove(*tree.selection())
    matched = []
    for item_id in tree.get_children():
        values = tree.item(item_id, "values")
        masp_val = values[2].strip().upper()
        if masp_val in masp_set or masp_val.lstrip("0") in masp_set_stripped:
            matched.append(item_id)
    if matched:
        tree.selection_set(matched)
        # Đẩy các dòng được select lên đầu bảng
        unmatched = [iid for iid in tree.get_children() if iid not in matched]
        for idx, iid in enumerate(matched + unmatched):
            tree.move(iid, "", idx)
            # Cập nhật STT và tag màu xen kẽ
            vals = list(tree.item(iid, "values"))
            vals[0] = idx + 1
            tag = "even" if (idx + 1) % 2 == 0 else "odd"
            tree.item(iid, values=vals, tags=(tag,))
        tree.see(matched[0])
        lbl_status.config(text=f"  Đã chọn {len(matched)}/{len(masp_list)} mã SP từ clipboard")
    else:
        lbl_status.config(text=f"  Không tìm thấy mã SP nào từ clipboard trong bảng")
    return "break"
tree.bind("<Control-v>", paste_and_select)

# Ctrl+V toàn app: nếu không focus vào entry thì auto select trong bảng
def global_paste(event):
    focused = root.focus_get()
    if focused in (entry_makh, entry_masp, entry_so):
        return  # để Entry xử lý paste bình thường
    if current_tab == "B":
        return paste_and_select_b(event)
    if current_tab == "C":
        return paste_and_select_c(event)
    return paste_and_select(event)
root.bind("<Control-v>", global_paste)

# Enter trong bảng → đổ giá SAP
def tree_enter(event):
    if tree.selection():
        do_update_price()
    return "break"
tree.bind("<Return>", tree_enter)

# ==================== Tab C: Đổ giá theo nhóm KH ====================
CUSTOMER_GROUP_MAP = {
    "T1 - Trang trại loại B5": "T1",
    "T2 - Trang trại loại B4": "T2",
    "T3 - Trang trại loại B3": "T3",
    "T5 - Trang trại loại B2": "T5",
    "T6 - Trang trại loại B1": "T6",
    "T7 - Trang trại loại TT": "T7",
    "T8 - Trang trại loại C": "T8",
    "Z1 - Đại lý loại I": "Z1",
    "Z2 - Đại lý loại II": "Z2",
    "Z3 - Kinh Doanh Online": "Z3",
    "Z5 - Trang trại loại A": "Z5",
    "Z6 - Trang trại loại B": "Z6",
    "Z7 - KH đại lý hưởng CKTT": "Z7",
    "Z9 - Nhóm Khách hàng khác": "Z9",
}

CURRENT_DATA_C = []  # Dữ liệu từ Excel cho Tab C

# Loading overlay cho Tab C
_loading_frame_c = None
_loading_label_c = None
_loading_anim_id_c = None
_loading_dots_c = 0

def show_loading_c(msg="Đang tải dữ liệu"):
    global _loading_frame_c, _loading_label_c, _loading_dots_c
    hide_loading_c()
    _loading_dots_c = 0
    _loading_frame_c = tk.Frame(frame_c, bg=BG_COLOR)
    _loading_frame_c.place(relx=0.5, rely=0.55, anchor=tk.CENTER, width=300, height=80)
    _loading_label_c = tk.Label(
        _loading_frame_c, text=msg, font=("Segoe UI", 12),
        bg=BG_COLOR, fg=TEXT_COLOR
    )
    _loading_label_c.pack(expand=True)
    _animate_loading_c(msg)

def _animate_loading_c(base_msg):
    global _loading_dots_c, _loading_anim_id_c
    if _loading_label_c and _loading_label_c.winfo_exists():
        _loading_dots_c = (_loading_dots_c % 3) + 1
        _loading_label_c.config(text=base_msg + "." * _loading_dots_c)
        _loading_anim_id_c = root.after(400, lambda: _animate_loading_c(base_msg))

def hide_loading_c():
    global _loading_frame_c, _loading_label_c, _loading_anim_id_c
    if _loading_anim_id_c:
        root.after_cancel(_loading_anim_id_c)
        _loading_anim_id_c = None
    if _loading_frame_c:
        _loading_frame_c.destroy()
        _loading_frame_c = None
        _loading_label_c = None

def download_template_c():
    """Tạo và lưu file Excel template mẫu để user nạp dữ liệu."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        messagebox.showerror(
            "Thiếu thư viện",
            "Cần cài đặt thư viện openpyxl.\n\nChạy lệnh: pip install openpyxl"
        )
        return
    try:
        save_path = filedialog.asksaveasfilename(
            parent=root,
            title="Lưu file template",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="template_do_gia_nhom_kh.xlsx",
            initialdir=os.path.join(os.path.expanduser("~"), "Desktop"),
        )
        if not save_path:
            return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "DuLieu"
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin"),
        )
        headers = ["Mã SP", "Giá"]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border
        sample_data = [("100001", 50000), ("100002", 75000), ("100003", 120000)]
        data_font = Font(name="Segoe UI", size=11)
        for row_idx, (masp, gia) in enumerate(sample_data, start=2):
            c1 = ws.cell(row=row_idx, column=1, value=masp)
            c1.font = data_font
            c1.border = thin_border
            c1.alignment = Alignment(horizontal="center")
            c2 = ws.cell(row=row_idx, column=2, value=gia)
            c2.font = data_font
            c2.border = thin_border
            c2.number_format = "#,##0"
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 20
        wb.save(save_path)
        lbl_status_c.config(text=f"  Đã lưu template: {os.path.basename(save_path)}")
        messagebox.showinfo("Thành công", f"Đã lưu file template tại:\n{save_path}")
    except Exception as ex:
        messagebox.showerror("Lỗi", f"Không thể tạo file template:\n{ex}")

def load_excel_file_c():
    """Mở file Excel và đọc dữ liệu mã SP + giá vào bảng."""
    global CURRENT_DATA_C
    try:
        import openpyxl
    except ImportError:
        messagebox.showerror(
            "Thiếu thư viện",
            "Cần cài đặt thư viện openpyxl.\n\nChạy lệnh: pip install openpyxl"
        )
        return
    file_path = filedialog.askopenfilename(
        parent=root,
        title="Chọn file Excel",
        filetypes=[("Excel files", "*.xlsx *.xls")],
    )
    if not file_path:
        return
    show_loading_c("Đang đọc file Excel")
    root.update_idletasks()

    def _read():
        global CURRENT_DATA_C
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            ws = wb.active
            data = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row is None or len(row) < 2:
                    continue
                masp_raw, gia_raw = row[0], row[1]
                if masp_raw is None or gia_raw is None:
                    continue
                masp = str(masp_raw).strip()
                if not masp:
                    continue
                try:
                    gia = float(str(gia_raw).replace(",", "").strip())
                except (ValueError, TypeError):
                    continue
                data.append({"masp": masp, "gia": gia})
            wb.close()
            CURRENT_DATA_C = data
            root.after(0, lambda: hide_loading_c())
            root.after(0, lambda: _show_results_c(data, file_path))
        except Exception as ex:
            CURRENT_DATA_C = []
            root.after(0, lambda: hide_loading_c())
            root.after(0, lambda: lbl_status_c.config(text=f"  Lỗi đọc file: {ex}"))
            root.after(0, lambda: messagebox.showerror("Lỗi", f"Không thể đọc file Excel:\n{ex}"))
    threading.Thread(target=_read, daemon=True).start()

def _show_results_c(data, file_path=""):
    """Hiển thị dữ liệu lên bảng Tab C."""
    for row in tree_c.get_children():
        tree_c.delete(row)
    for i, item in enumerate(data, start=1):
        gia_fmt = f"{item['gia']:,.0f}"
        tag = "even" if i % 2 == 0 else "odd"
        tree_c.insert("", tk.END, values=(i, item["masp"], gia_fmt), tags=(tag,))
    fname = os.path.basename(file_path) if file_path else ""
    lbl_status_c.config(text=f"  Đã tải {len(data)} sản phẩm từ {fname}")

def do_update_price_c():
    """Đổ giá SAP theo nhóm khách hàng cho các dòng đang chọn."""
    global SAP_SESSION
    selected = tree_c.selection()
    if not selected:
        messagebox.showwarning("Chưa chọn dòng", "Vui lòng chọn ít nhất một dòng trong bảng để đổ giá.")
        return
    group_label = cmb_group.get()
    group_code = CUSTOMER_GROUP_MAP.get(group_label, "")
    if not group_code:
        messagebox.showwarning("Chưa chọn nhóm KH", "Vui lòng chọn nhóm khách hàng.")
        return
    items = []
    for sel in selected:
        values = tree_c.item(sel, "values")
        items.append({
            "masp": values[1],
            "gia": values[2].replace(",", "").strip(),
            "gia_fmt": values[2],
        })
    count = len(items)
    MAX_SHOW = 10
    detail_lines = [f"  {i+1}. SP: {it['masp']}  |  Giá: {it['gia_fmt']}" for i, it in enumerate(items[:MAX_SHOW])]
    if count > MAX_SHOW:
        detail_lines.append(f"  ... và {count - MAX_SHOW} dòng nữa")
    detail = "\n".join(detail_lines)
    confirm = messagebox.askyesno(
        "Xác nhận đổ giá",
        f"Nhóm KH: {group_label}\n\nĐổ giá {count} sản phẩm?\n\n{detail}",
    )
    if not confirm:
        return
    btn_update_c.config(state=tk.DISABLED, text="Đang xử lý...")
    lbl_status_c.config(text=f"  Đang xử lý {count} dòng...")
    root.update_idletasks()

    def _run():
        global SAP_SESSION
        try:
            from vk11 import updatematerialgr
            session = _get_or_create_sap_session()
            if session == "MAX_SESSIONS":
                root.after(0, lambda: messagebox.showwarning(
                    "Quá giới hạn session",
                    "Số session SAP đã đạt giới hạn tối đa.\n\n"
                    "Vui lòng đóng bớt các cửa sổ SAP đang mở rồi thử lại."
                ))
                return
            if session is None:
                root.after(0, lambda: messagebox.showerror("Lỗi", "Không thể kết nối SAP. Kiểm tra lại cấu hình."))
                return
            mat_list = [{"masp": it["masp"], "gia": it["gia"]} for it in items]
            results = updatematerialgr(session, group_code, mat_list)
            success = 0
            errors = []
            for i, r in enumerate(results):
                if r["status"] == "ok":
                    success += 1
                else:
                    errors.append(f"{r['masp']}: {r['msg']}")
                root.after(0, lambda p=i+1: lbl_status_c.config(text=f"  Đã xử lý {p}/{count}..."))
            msg = f"Thành công: {success}/{count}"
            if errors:
                unique_msgs = set()
                for e in errors:
                    if "| SAP: " in e:
                        unique_msgs.add(e.split("| SAP: ")[-1])
                    else:
                        unique_msgs.add(e.split(": ", 1)[-1] if ": " in e else e)
                if len(unique_msgs) == 1:
                    msg += f"\n\nLỗi ({len(errors)} SP): {unique_msgs.pop()}"
                else:
                    msg += f"\n\nLỗi ({len(errors)}):\n" + "\n".join(errors)
                root.after(0, lambda m=msg: messagebox.showwarning("Kết quả", m))
            root.after(0, lambda: lbl_status_c.config(text=f"  Hoàn tất: {success}/{count} thành công"))
        except Exception as ex:
            SAP_SESSION = None
            root.after(0, lambda e=ex: messagebox.showerror("Lỗi", f"Đổ giá thất bại:\n{e}"))
            root.after(0, lambda e=ex: lbl_status_c.config(text=f"  Lỗi: {e}"))
        finally:
            root.after(0, lambda: btn_update_c.config(state=tk.NORMAL, text="Đổ giá SAP"))
    threading.Thread(target=_run, daemon=True).start()

# Tab C: Card tìm kiếm
card_search_c = tk.Frame(frame_c, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
card_search_c.pack(fill=tk.X, padx=16, pady=(16, 8))

inner_search_c = tk.Frame(card_search_c, bg=CARD_BG)
inner_search_c.pack(fill=tk.X, padx=20, pady=16)

tk.Label(inner_search_c, text="Nhóm khách hàng", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
    row=0, column=0, padx=(0, 24), sticky=tk.W
)

cmb_group = ttk.Combobox(
    inner_search_c, values=list(CUSTOMER_GROUP_MAP.keys()), width=30, font=("Segoe UI", 11),
    state="readonly"
)
cmb_group.current(0)
cmb_group.grid(row=1, column=0, padx=(0, 16), pady=(4, 0), ipady=3, sticky=tk.W)

BTN_IMPORT = "#2980b9"
BTN_IMPORT_HOVER = "#3498db"
BTN_TEMPLATE = "#8e44ad"
BTN_TEMPLATE_HOVER = "#9b59b6"

btn_load_excel = tk.Button(
    inner_search_c, text="📂 Nạp file Excel", font=("Segoe UI", 10, "bold"),
    bg=BTN_IMPORT, fg="white", activebackground=BTN_IMPORT_HOVER, activeforeground="white",
    relief=tk.FLAT, cursor="hand2", padx=12, pady=4,
    command=load_excel_file_c,
)
btn_load_excel.grid(row=1, column=1, padx=(0, 8), pady=(4, 0), ipady=3)
btn_load_excel.bind("<Enter>", lambda e: on_enter_btn(e, BTN_IMPORT_HOVER))
btn_load_excel.bind("<Leave>", lambda e: on_leave_btn(e, BTN_IMPORT))

btn_template = tk.Button(
    inner_search_c, text="📥 Tải template mẫu", font=("Segoe UI", 10, "bold"),
    bg=BTN_TEMPLATE, fg="white", activebackground=BTN_TEMPLATE_HOVER, activeforeground="white",
    relief=tk.FLAT, cursor="hand2", padx=12, pady=4,
    command=download_template_c,
)
btn_template.grid(row=1, column=2, padx=(0, 8), pady=(4, 0), ipady=3)
btn_template.bind("<Enter>", lambda e: on_enter_btn(e, BTN_TEMPLATE_HOVER))
btn_template.bind("<Leave>", lambda e: on_leave_btn(e, BTN_TEMPLATE))

btn_update_c = tk.Button(
    inner_search_c, text="Đổ giá SAP", font=("Segoe UI", 10, "bold"),
    bg=BTN_SUCCESS, fg="white", activebackground=BTN_SUCCESS_HOVER, activeforeground="white",
    relief=tk.FLAT, cursor="hand2", padx=16, pady=4, command=do_update_price_c,
)
btn_update_c.grid(row=1, column=3, padx=(0, 8), pady=(4, 0), ipady=3)
btn_update_c.bind("<Enter>", lambda e: on_enter_btn(e, BTN_SUCCESS_HOVER))
btn_update_c.bind("<Leave>", lambda e: on_leave_btn(e, BTN_SUCCESS))

# Tab C: Card bảng dữ liệu
card_table_c = tk.Frame(frame_c, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
card_table_c.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 8))

tbl_frame_c = tk.Frame(card_table_c, bg=CARD_BG)
tbl_frame_c.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

columns_c = ("stt", "masp", "gia")
tree_c = ttk.Treeview(tbl_frame_c, columns=columns_c, show="headings", height=14, style="Custom.Treeview", selectmode="extended")

tree_c.heading("stt", text="STT")
tree_c.heading("masp", text="Mã SP")
tree_c.heading("gia", text="Giá (VNĐ)")

tree_c.column("stt", width=80, anchor=tk.CENTER, minwidth=50)
tree_c.column("masp", width=250, anchor=tk.CENTER, minwidth=120)
tree_c.column("gia", width=250, anchor=tk.E, minwidth=120)

tree_c.tag_configure("odd", background=ROW_ODD)
tree_c.tag_configure("even", background=ROW_EVEN)

tbl_frame_c.columnconfigure(0, weight=1)
tbl_frame_c.rowconfigure(0, weight=1)
scrollbar_c = ttk.Scrollbar(tbl_frame_c, orient=tk.VERTICAL, command=tree_c.yview, style="Custom.Vertical.TScrollbar")
tree_c.configure(yscrollcommand=scrollbar_c.set)
tree_c.grid(row=0, column=0, sticky="nsew")
scrollbar_c.grid(row=0, column=1, sticky="ns")

# Tab C: Status bar
status_bar_c = tk.Frame(frame_c, bg=STATUS_BG, height=32)
status_bar_c.pack(fill=tk.X, padx=16, pady=(0, 12))
status_bar_c.pack_propagate(False)

lbl_status_c = tk.Label(status_bar_c, text="", font=("Segoe UI", 9), bg=STATUS_BG, fg="#5d6d7e", anchor=tk.W)
lbl_status_c.pack(fill=tk.X, padx=8, pady=5)

# Tab C: Bindings
def select_all_c(event):
    tree_c.selection_set(tree_c.get_children())
    return "break"
tree_c.bind("<Control-a>", select_all_c)

def tree_enter_c(event):
    if tree_c.selection():
        do_update_price_c()
    return "break"
tree_c.bind("<Return>", tree_enter_c)

def paste_and_select_c(event):
    try:
        clipboard = root.clipboard_get().strip()
    except:
        return "break"
    import re
    masp_list = [x.strip().upper() for x in re.split(r'[\n\r\t,;\s]+', clipboard) if x.strip()]
    if not masp_list:
        return "break"
    masp_set = set(masp_list)
    masp_set_stripped = set(m.lstrip("0") for m in masp_list)
    tree_c.selection_remove(*tree_c.selection())
    matched = []
    for item_id in tree_c.get_children():
        values = tree_c.item(item_id, "values")
        masp_val = values[1].strip().upper()
        if masp_val in masp_set or masp_val.lstrip("0") in masp_set_stripped:
            matched.append(item_id)
    if matched:
        tree_c.selection_set(matched)
        unmatched = [iid for iid in tree_c.get_children() if iid not in matched]
        for idx, iid in enumerate(matched + unmatched):
            tree_c.move(iid, "", idx)
            vals = list(tree_c.item(iid, "values"))
            vals[0] = idx + 1
            tag = "even" if (idx + 1) % 2 == 0 else "odd"
            tree_c.item(iid, values=vals, tags=(tag,))
        tree_c.see(matched[0])
        lbl_status_c.config(text=f"  Đã chọn {len(matched)}/{len(masp_list)} mã SP từ clipboard")
    else:
        lbl_status_c.config(text=f"  Không tìm thấy mã SP nào từ clipboard trong bảng")
    return "break"
tree_c.bind("<Control-v>", paste_and_select_c)

# Focus vào ô mã KH khi mở app
entry_makh.focus_set()

# Tải danh sách KH trong thread sau khi UI sẵn sàng
def _init_load():
    show_loading("Đang tải danh sách khách hàng")
    def _do():
        fetch_customer_list()
        def _done():
            hide_loading()
            # Cập nhật completions sau khi tải xong
            _default = CHI_NHANH_MAP.get(cmb_chinhanh.get(), "")
            entry_makh.completions = get_customer_completions(_default)
            lbl_status.config(text=f"  Đã tải {len(ALL_CUSTOMERS)} khách hàng")
        root.after(0, _done)
    threading.Thread(target=_do, daemon=True).start()

root.after(100, _init_load)

root.mainloop()
