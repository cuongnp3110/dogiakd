import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys

# Thêm thư mục exe vào sys.path để tìm pywinauto/comtypes khi chạy từ exe
if getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(sys.executable))

import subprocess
import shutil
import zipfile
import tempfile
import configparser

import helper.functions as fn
from helper.functions import (
    get_app_dir, VERSION, _parse_ver,
    fetch_customer_list, get_customer_completions,
    _get_or_create_sap_session, reset_sap_session,
    on_enter_btn, on_leave_btn,
    CHI_NHANH_MAP,
    BG_COLOR, HEADER_BG, HEADER_FG, ACCENT, ACCENT_HOVER,
    BTN_DANGER, BTN_DANGER_HOVER, TEXT_COLOR, CARD_BG, STATUS_BG,
    ROW_EVEN, ROW_ODD, ROW_SELECT,
)

from tabs import farm, agency, customer_gr, so_phu, supplement


# ==================== Cập nhật phần mềm ====================
def update_app():
    """Kiểm tra và tải bản cập nhật từ shared folder"""

    progress_win = tk.Toplevel(root)
    progress_win.title("Cập nhật phần mềm")
    progress_win.geometry("420x130")
    progress_win.resizable(False, False)
    progress_win.configure(bg=CARD_BG)
    progress_win.transient(root)
    progress_win.grab_set()
    progress_win.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() - 420) // 2
    y = root.winfo_y() + (root.winfo_height() - 130) // 2
    progress_win.geometry(f"+{x}+{y}")

    lbl_progress = tk.Label(
        progress_win, text="Đang kiểm tra phiên bản...", font=("Segoe UI", 10),
        bg=CARD_BG, fg=TEXT_COLOR, anchor=tk.W)
    lbl_progress.pack(fill=tk.X, padx=20, pady=(16, 4))

    progress_bar = ttk.Progressbar(progress_win, length=380, mode="determinate")
    progress_bar.pack(padx=20, pady=(0, 4))

    lbl_percent = tk.Label(
        progress_win, text="0%", font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_COLOR)
    lbl_percent.pack(padx=20)
    progress_win.update()

    def _set_progress(text, value):
        lbl_progress.config(text=text)
        progress_bar["value"] = value
        lbl_percent.config(text=f"{int(value)}%")
        progress_win.update()

    try:
        config = configparser.ConfigParser()
        config.read(os.path.join(get_app_dir(), "config.ini"))
        share_path = config.get("UPDATE", "share", fallback=r"\\172.0.1.103\kinhdoanh\DoGiaKD_Source")
        share_pass = config.get("UPDATE", "password", fallback="")

        print(f"[UPDATE] VERSION hiện tại: {VERSION}")
        print(f"[UPDATE] Share path: {share_path}")

        version_file = os.path.join(share_path, "version.txt")
        print(f"[UPDATE] Version file: {version_file}")
        _set_progress("Đang kết nối server...", 5)

        if not os.path.exists(version_file):
            print(f"[UPDATE] Không thấy version.txt, thử net use...")
            try:
                parts = share_path.strip("\\").split("\\")
                net_share = "\\\\" + parts[0] + "\\" + parts[1] if len(parts) >= 2 else share_path
                print(f"[UPDATE] net use \"{net_share}\"")
                result = subprocess.run(
                    f'net use "{net_share}" "{share_pass}" /persistent:no',
                    shell=True, capture_output=True, timeout=10, text=True)
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

        with open(version_file, "r", encoding="utf-8-sig") as f:
            latest_version = f.read().strip()
        print(f"[UPDATE] Phiên bản mới nhất trên server: {repr(latest_version)}")
        print(f"[UPDATE] Phiên bản hiện tại: {repr(VERSION)}")

        if _parse_ver(latest_version) <= _parse_ver(VERSION):
            print(f"[UPDATE] Đang dùng bản mới nhất, không cần cập nhật")
            progress_win.destroy()
            messagebox.showinfo("Cập nhật", f"Bạn đang dùng phiên bản mới nhất ({VERSION})")
            return

        _set_progress(f"Tìm thấy phiên bản mới: {latest_version}", 20)

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

        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else get_app_dir()
        temp_dir = os.path.join(tempfile.gettempdir(), "DoGiaKD_update")
        print(f"[UPDATE] App dir: {app_dir}")
        print(f"[UPDATE] Temp dir: {temp_dir}")

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)

        print(f"[UPDATE] Đang copy zip...")
        temp_zip = os.path.join(temp_dir, "DoGiaKD.zip")
        copied = 0
        chunk_size = 1024 * 256
        with open(zip_file, "rb") as src, open(temp_zip, "wb") as dst:
            while True:
                chunk = src.read(chunk_size)
                if not chunk:
                    break
                dst.write(chunk)
                copied += len(chunk)
                pct = 25 + int((copied / zip_size) * 55)
                _set_progress(
                    f"Đang tải: {copied / 1024 / 1024:.1f} / {zip_size / 1024 / 1024:.1f} MB",
                    min(pct, 80))
        print(f"[UPDATE] Copy xong: {temp_zip} ({os.path.getsize(temp_zip) / 1024 / 1024:.1f} MB)")

        _set_progress("Đang giải nén...", 85)

        extract_dir = os.path.join(temp_dir, "extracted")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        with zipfile.ZipFile(temp_zip, "r") as zf:
            zf.extractall(extract_dir)
        print(f"[UPDATE] Giải nén xong: {extract_dir}")

        src_dir = extract_dir
        sub = os.path.join(extract_dir, "DoGiaKD")
        if os.path.isdir(sub):
            src_dir = sub

        _set_progress("Đang chuẩn bị cập nhật...", 90)

        # Tạo batch script để thay thế file sau khi app tắt
        pid = os.getpid()
        exe_path = sys.executable if getattr(sys, 'frozen', False) else ""
        bat_path = os.path.join(temp_dir, "do_update.bat")

        bat_content = f'''@echo off
chcp 65001 >nul
echo Đang chờ ứng dụng đóng...

:wait_loop
tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo Đang cập nhật file...
xcopy /E /Y /Q "{src_dir}\\*" "{app_dir}\\"
if errorlevel 1 (
    echo Cập nhật thất bại!
    pause
    exit /b 1
)

echo Cập nhật thành công!
'''
        if exe_path:
            bat_content += f'start "" "{exe_path}"\n'
        bat_content += f'''
rd /S /Q "{extract_dir}" 2>nul
del /Q "{temp_zip}" 2>nul
(goto) 2>nul & del "%~f0"
'''

        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        print(f"[UPDATE] Batch script: {bat_path}")

        _set_progress(f"Cập nhật phiên bản {latest_version} – đang khởi động lại...", 100)
        progress_win.update()
        import time
        time.sleep(0.5)
        progress_win.destroy()

        confirm = messagebox.askyesno(
            "Cập nhật",
            f"Đã tải xong phiên bản {latest_version}.\n\n"
            "Ứng dụng sẽ đóng và tự khởi động lại.\nBạn có muốn tiếp tục?")
        if not confirm:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        # Chạy batch script rồi tắt app
        subprocess.Popen(
            f'cmd /c "{bat_path}"',
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        root.destroy()
        sys.exit(0)

    except Exception as ex:
        print(f"[UPDATE] EXCEPTION: {ex}")
        import traceback
        traceback.print_exc()
        try:
            progress_win.destroy()
        except Exception:
            pass
        messagebox.showerror("Lỗi", f"Cập nhật thất bại:\n{ex}")


# ==================== Giao diện ====================
root = tk.Tk()
root.title("Đơn Giá Khách Hàng - Version " + VERSION)
root.geometry("1280x920+200+50")
root.minsize(600, 400)
root.configure(bg=BG_COLOR)

_icon_path = os.path.join(get_app_dir(), "logo.ico")
if os.path.exists(_icon_path):
    root.iconbitmap(_icon_path)

# ---- Header ----
header = tk.Frame(root, bg=HEADER_BG, height=56)
header.pack(fill=tk.X)
header.pack_propagate(False)

lbl_title = tk.Label(
    header, text="QUẢN LÝ ĐỔ GIÁ TRỰC TIẾP",
    font=("Segoe UI", 16, "bold"), bg=HEADER_BG, fg=HEADER_FG)
lbl_title.pack(side=tk.LEFT, padx=20, pady=10)

BTN_UPDATE_APP = "#e67e22"
BTN_UPDATE_APP_HOVER = "#f39c12"
btn_update_app = tk.Button(
    header, text="Cập nhật phiên bản mới ⬇", font=("Segoe UI", 10, "bold"),
    bg=BTN_UPDATE_APP, fg="white", activebackground=BTN_UPDATE_APP_HOVER, activeforeground="white",
    relief=tk.FLAT, cursor="hand2", padx=8, pady=2, command=update_app)
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
    for f in (frame_a, frame_b, frame_c, frame_d, frame_e):
        f.pack_forget()
    for btn in (tab_btn_a, tab_btn_b, tab_btn_c, tab_btn_d, tab_btn_e):
        btn.config(bg=TAB_INACTIVE_BG, fg=TAB_INACTIVE_FG, font=("Segoe UI", 10))
    if tab_name == "A":
        frame_a.pack(fill=tk.BOTH, expand=True)
        tab_btn_a.config(bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG, font=("Segoe UI", 10, "bold"))
    elif tab_name == "B":
        frame_b.pack(fill=tk.BOTH, expand=True)
        tab_btn_b.config(bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG, font=("Segoe UI", 10, "bold"))
    elif tab_name == "C":
        frame_c.pack(fill=tk.BOTH, expand=True)
        tab_btn_c.config(bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG, font=("Segoe UI", 10, "bold"))
    elif tab_name == "D":
        frame_d.pack(fill=tk.BOTH, expand=True)
        tab_btn_d.config(bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG, font=("Segoe UI", 10, "bold"))
    elif tab_name == "E":
        frame_e.pack(fill=tk.BOTH, expand=True)
        tab_btn_e.config(bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG, font=("Segoe UI", 10, "bold"))

tab_btn_a = tk.Button(
    tab_bar, text="  Đổ giá trang trại", font=("Segoe UI", 10, "bold"),
    bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG,
    relief=tk.FLAT, cursor="hand2", bd=0, command=lambda: switch_tab("A"))
tab_btn_a.pack(side=tk.LEFT, padx=(16, 2), pady=(6, 0), ipady=4, ipadx=10)

tab_btn_b = tk.Button(
    tab_bar, text="  Đổ giá đại lý", font=("Segoe UI", 10),
    bg=TAB_INACTIVE_BG, fg=TAB_INACTIVE_FG,
    relief=tk.FLAT, cursor="hand2", bd=0, command=lambda: switch_tab("B"))
tab_btn_b.pack(side=tk.LEFT, padx=(2, 0), pady=(6, 0), ipady=4, ipadx=10)

tab_btn_c = tk.Button(
    tab_bar, text="  Đổ giá nhóm KH", font=("Segoe UI", 10),
    bg=TAB_INACTIVE_BG, fg=TAB_INACTIVE_FG,
    relief=tk.FLAT, cursor="hand2", bd=0, command=lambda: switch_tab("C"))
tab_btn_c.pack(side=tk.LEFT, padx=(2, 0), pady=(6, 0), ipady=4, ipadx=10)

tab_btn_d = tk.Button(
    tab_bar, text="  SO Phụ", font=("Segoe UI", 10),
    bg=TAB_INACTIVE_BG, fg=TAB_INACTIVE_FG,
    relief=tk.FLAT, cursor="hand2", bd=0, command=lambda: switch_tab("D"))
tab_btn_d.pack(side=tk.LEFT, padx=(2, 0), pady=(6, 0), ipady=4, ipadx=10)

tab_btn_e = tk.Button(
    tab_bar, text="  Bổ sung mã SP", font=("Segoe UI", 10),
    bg=TAB_INACTIVE_BG, fg=TAB_INACTIVE_FG,
    relief=tk.FLAT, cursor="hand2", bd=0, command=lambda: switch_tab("E"))
tab_btn_e.pack(side=tk.LEFT, padx=(2, 0), pady=(6, 0), ipady=4, ipadx=10)

# ---- Content frames ----
frame_a = tk.Frame(root, bg=BG_COLOR)
frame_a.pack(fill=tk.BOTH, expand=True)

frame_b = tk.Frame(root, bg=BG_COLOR)
frame_c = tk.Frame(root, bg=BG_COLOR)
frame_d = tk.Frame(root, bg=BG_COLOR)
frame_e = tk.Frame(root, bg=BG_COLOR)

# ---- Style cho Treeview (dùng chung cho tất cả Tab) ----
style = ttk.Style()
style.theme_use("clam")

style.configure(
    "Custom.Treeview",
    background=ROW_EVEN, foreground=TEXT_COLOR, fieldbackground=ROW_EVEN,
    font=("Segoe UI", 10), rowheight=32, borderwidth=0)
style.configure(
    "Custom.Treeview.Heading",
    background=HEADER_BG, foreground=HEADER_FG,
    font=("Segoe UI", 10, "bold"), relief=tk.FLAT, borderwidth=0, padding=(0, 6))
style.map("Custom.Treeview.Heading", background=[("active", "#264e78")])
style.map("Custom.Treeview",
    background=[("selected", ROW_SELECT)], foreground=[("selected", TEXT_COLOR)])
style.configure(
    "Custom.Vertical.TScrollbar",
    troughcolor="#f0f4f8", background="#b0c4de", arrowcolor=HEADER_BG,
    borderwidth=0, relief=tk.FLAT)

# ---- Build các Tab ----
tab_a = farm.build(root, frame_a)
tab_b = agency.build(root, frame_b)
tab_c = customer_gr.build(root, frame_c)
tab_d = so_phu.build(root, frame_d)
tab_e = supplement.build(root, frame_e)

# ---- Global paste (Ctrl+V) ----
def global_paste(event):
    focused = root.focus_get()
    if focused in (tab_a.entry_makh, tab_a.entry_masp, tab_b.entry_so, tab_d.entry_main, tab_d.entry_sub, tab_e.entry_main_e):
        return  # Để Entry xử lý paste bình thường
    if current_tab == "B":
        return tab_b.paste_and_select_b(event)
    if current_tab == "C":
        return tab_c.paste_and_select_c(event)
    if current_tab == "D":
        return tab_d.paste_and_select_sub(event)
    return tab_a.paste_and_select(event)
root.bind("<Control-v>", global_paste)

# Focus vào ô mã KH khi mở app
tab_a.entry_makh.focus_set()

# Tải danh sách KH trong thread sau khi UI sẵn sàng
def _init_load():
    tab_a.show_loading("Đang tải danh sách khách hàng")
    def _do():
        fetch_customer_list()
        def _done():
            tab_a.hide_loading()
            _default = CHI_NHANH_MAP.get(tab_a.cmb_chinhanh.get(), "")
            tab_a.entry_makh.completions = get_customer_completions(_default)
            tab_a.lbl_status.config(text=f"  Đã tải {len(fn.ALL_CUSTOMERS)} khách hàng")
        root.after(0, _done)
    threading.Thread(target=_do, daemon=True).start()

root.after(100, _init_load)

root.mainloop()
