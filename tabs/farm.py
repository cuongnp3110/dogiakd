"""Tab A: Đổ giá trang trại"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from types import SimpleNamespace

from helper.functions import (
    BG_COLOR, HEADER_BG, HEADER_FG, ACCENT, TEXT_COLOR, CARD_BG, STATUS_BG,
    ROW_EVEN, ROW_ODD, ROW_SELECT, BTN_SUCCESS, BTN_SUCCESS_HOVER,
    CHI_NHANH_MAP,
    get_customer_completions, fetch_prices_from_api,
    _get_or_create_sap_session, reset_sap_session,
    on_enter_btn, on_leave_btn,
    bind_tree_shortcuts,
)


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
            self._update_list()
        else:
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


# ==================== Build Tab A ====================
def build(root, frame_a):
    """Tạo toàn bộ UI và logic cho Tab A. Trả về namespace chứa widgets cần thiết."""

    CURRENT_DATA = []

    # ---- Loading overlay ----
    _state = {"frame": None, "label": None, "anim_id": None, "dots": 0}

    def show_loading(msg="Đang tải dữ liệu"):
        hide_loading()
        _state["dots"] = 0
        _state["frame"] = tk.Frame(root, bg=BG_COLOR)
        _state["frame"].place(relx=0.5, rely=0.55, anchor=tk.CENTER, width=300, height=80)
        _state["label"] = tk.Label(
            _state["frame"], text=msg, font=("Segoe UI", 12), bg=BG_COLOR, fg=TEXT_COLOR
        )
        _state["label"].pack(expand=True)
        _animate_loading(msg)

    def _animate_loading(base_msg):
        if _state["label"] and _state["label"].winfo_exists():
            _state["dots"] = (_state["dots"] % 3) + 1
            _state["label"].config(text=base_msg + "." * _state["dots"])
            _state["anim_id"] = root.after(400, lambda: _animate_loading(base_msg))

    def hide_loading():
        if _state["anim_id"]:
            root.after_cancel(_state["anim_id"])
            _state["anim_id"] = None
        if _state["frame"]:
            _state["frame"].destroy()
            _state["frame"] = None
            _state["label"] = None

    # ---- Logic functions ----
    def on_customer_selected(customer_code):
        nonlocal CURRENT_DATA
        masp_filter = entry_masp.get().strip().upper()
        for row in tree.get_children():
            tree.delete(row)
        if not customer_code:
            CURRENT_DATA = []
            lbl_status.config(text="")
            return
        api_code = customer_code.lstrip("0") or customer_code
        chinhanh_code = CHI_NHANH_MAP.get(cmb_chinhanh.get(), "2001")
        lbl_status.config(text="  Đang tải dữ liệu...")
        show_loading("Đang tải giá sản phẩm")
        root.update_idletasks()

        def _fetch():
            nonlocal CURRENT_DATA
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
            tree.insert("", tk.END, values=(i, item["makh"], item["masp"], item.get("tensp", ""), gia_fmt, item.get("ghi_chu", "")), tags=(tag,))
        name_txt = f" - {cust_name}" if cust_name else ""
        lbl_status.config(text=f"  Tìm thấy {len(results)} sản phẩm{name_txt}")

    def filter_local(event=None):
        masp_filter = entry_masp.get().strip().upper()
        results = CURRENT_DATA
        if masp_filter:
            results = [r for r in results if masp_filter in r["masp"].upper()]
        _show_results(results)

    def do_update_price():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn dòng", "Vui lòng chọn ít nhất một dòng trong bảng để đổ giá.")
            return
        items = []
        for sel in selected:
            values = tree.item(sel, "values")
            items.append({
                "makh": values[1], "masp": values[2], "tensp": values[3],
                "gia": values[4].replace(",", ""), "gia_fmt": values[4], "ngaykt": "", "ghi_chu": values[5],
            })
        count = len(items)
        MAX_SHOW = 10
        detail_lines = [f"  {i+1}. KH: {it['makh']}  |  SP: {it['masp']}  |  Giá: {it['gia_fmt']}" for i, it in enumerate(items[:MAX_SHOW])]
        if count > MAX_SHOW:
            detail_lines.append(f"  ... và {count - MAX_SHOW} dòng nữa")
        detail = "\n".join(detail_lines)
        confirm = messagebox.askyesno("Xác nhận đổ giá", f"Bạn có chắc muốn đổ giá {count} dòng vào SAP?\n\n{detail}")
        if not confirm:
            return
        btn_update.config(state=tk.DISABLED, text="Đang xử lý...")
        lbl_status.config(text=f"Đang xử lý {count} dòng...")
        root.update_idletasks()

        def _run():
            try:
                from helper.vk11 import updateMaterial
                session = _get_or_create_sap_session()
                print(session)
                if session == "MAX_SESSIONS":
                    root.after(0, lambda: messagebox.showwarning("Quá giới hạn session",
                        "Số session SAP đã đạt giới hạn tối đa.\n\nVui lòng đóng bớt các cửa sổ SAP đang mở rồi thử lại."))
                    return
                if session is None:
                    root.after(0, lambda: messagebox.showerror("Lỗi", "Không thể kết nối SAP. Kiểm tra lại cấu hình."))
                    return
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
                root.after(0, lambda: lbl_status.config(text=f"  Hoàn tất: {success}/{count} thành công"))
            except Exception as ex:
                reset_sap_session()
                root.after(0, lambda e=ex: messagebox.showerror("Lỗi", f"Đổ giá thất bại:\n{e}"))
                root.after(0, lambda e=ex: lbl_status.config(text=f"  Lỗi: {e}"))
            finally:
                root.after(0, lambda: btn_update.config(state=tk.NORMAL, text="Đổ giá SAP"))
        threading.Thread(target=_run, daemon=True).start()

    # ---- UI: Card tìm kiếm ----
    card_search = tk.Frame(frame_a, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
    card_search.pack(fill=tk.X, padx=16, pady=(16, 8))

    inner_search = tk.Frame(card_search, bg=CARD_BG)
    inner_search.pack(fill=tk.X, padx=20, pady=16)

    # Row 0: Labels
    tk.Label(inner_search, text="Chi nhánh", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
        row=0, column=0, padx=(0, 24), sticky=tk.W)
    tk.Label(inner_search, text="Mã KH", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
        row=0, column=1, padx=(0, 24), sticky=tk.W)
    tk.Label(inner_search, text="Mã SP", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
        row=0, column=2, padx=(0, 24), sticky=tk.W)

    # Row 1: Inputs & Buttons
    cmb_chinhanh = ttk.Combobox(
        inner_search, values=list(CHI_NHANH_MAP.keys()), width=20, font=("Segoe UI", 11), state="readonly")
    cmb_chinhanh.current(0)
    cmb_chinhanh.grid(row=1, column=0, padx=(0, 24), pady=(4, 0), ipady=3, sticky=tk.W)

    def _on_chinhanh_change(event=None):
        chinhanh_code = CHI_NHANH_MAP.get(cmb_chinhanh.get(), "")
        entry_makh.completions = get_customer_completions(chinhanh_code)
        makh = entry_makh.get().strip()
        if makh:
            on_customer_selected(makh)
    cmb_chinhanh.bind("<<ComboboxSelected>>", _on_chinhanh_change)

    _default_sale_org = CHI_NHANH_MAP.get(list(CHI_NHANH_MAP.keys())[0], "")

    entry_makh = AutocompleteEntry(
        inner_search, completions=get_customer_completions(_default_sale_org),
        on_select_callback=on_customer_selected,
        width=18, font=("Segoe UI", 11), relief=tk.FLAT,
        bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT)
    entry_makh.grid(row=1, column=1, padx=(0, 24), pady=(4, 0), ipady=5, sticky=tk.W)

    entry_masp = tk.Entry(
        inner_search, width=18, font=("Segoe UI", 11), relief=tk.FLAT,
        bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT)
    entry_masp.grid(row=1, column=2, padx=(0, 24), pady=(4, 0), ipady=5, sticky=tk.W)
    entry_masp.bind("<KeyRelease>", filter_local)

    btn_update = tk.Button(
        inner_search, text="Đổ giá SAP", font=("Segoe UI", 10, "bold"),
        bg=BTN_SUCCESS, fg="white", activebackground=BTN_SUCCESS_HOVER, activeforeground="white",
        relief=tk.FLAT, cursor="hand2", padx=16, pady=4, command=do_update_price)
    btn_update.grid(row=1, column=3, padx=(0, 8), pady=(4, 0), ipady=3)
    btn_update.bind("<Enter>", lambda e: on_enter_btn(e, BTN_SUCCESS_HOVER))
    btn_update.bind("<Leave>", lambda e: on_leave_btn(e, BTN_SUCCESS))

    # ---- UI: Card bảng dữ liệu ----
    card_table = tk.Frame(frame_a, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
    card_table.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 8))

    tbl_frame = tk.Frame(card_table, bg=CARD_BG)
    tbl_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    columns = ("stt", "makh", "masp", "tensp", "gia", "ghi_chu")
    tree = ttk.Treeview(tbl_frame, columns=columns, show="headings", height=14, style="Custom.Treeview", selectmode="extended")

    tree.heading("stt", text="STT")
    tree.heading("makh", text="Mã KH")
    tree.heading("masp", text="Mã SP")
    tree.heading("tensp", text="Tên SP")
    tree.heading("gia", text="Giá (VNĐ)")
    tree.heading("ghi_chu", text="Ghi chú")
    tree.column("stt", width=50, anchor=tk.CENTER, minwidth=40)
    tree.column("makh", width=120, anchor=tk.CENTER, minwidth=80)
    tree.column("masp", width=120, anchor=tk.CENTER, minwidth=80)
    tree.column("tensp", width=250, anchor=tk.CENTER, minwidth=150)
    tree.column("gia", width=130, anchor=tk.CENTER, minwidth=80)
    tree.column("ghi_chu", width=100, anchor=tk.CENTER, minwidth=50)

    tree.tag_configure("odd", background=ROW_ODD)
    tree.tag_configure("even", background=ROW_EVEN)

    tbl_frame.columnconfigure(0, weight=1)
    tbl_frame.rowconfigure(0, weight=1)
    scrollbar = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL, command=tree.yview, style="Custom.Vertical.TScrollbar")
    tree.configure(yscrollcommand=scrollbar.set)
    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # ---- Status bar ----
    status_bar = tk.Frame(frame_a, bg=STATUS_BG, height=32)
    status_bar.pack(fill=tk.X, padx=16, pady=(0, 12))
    status_bar.pack_propagate(False)

    lbl_status = tk.Label(status_bar, text="", font=("Segoe UI", 9), bg=STATUS_BG, fg="#5d6d7e", anchor=tk.W)
    lbl_status.pack(fill=tk.X, padx=8, pady=5)

    # ---- Bindings ----
    paste_and_select = bind_tree_shortcuts(root, tree, masp_col_index=2, lbl_status=lbl_status)

    def tree_enter(event):
        if tree.selection():
            do_update_price()
        return "break"
    tree.bind("<Return>", tree_enter)

    # ---- Return namespace ----
    return SimpleNamespace(
        entry_makh=entry_makh,
        entry_masp=entry_masp,
        cmb_chinhanh=cmb_chinhanh,
        tree=tree,
        lbl_status=lbl_status,
        paste_and_select=paste_and_select,
        show_loading=show_loading,
        hide_loading=hide_loading,
    )
