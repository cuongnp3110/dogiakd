"""Tab E: Bổ sung mã SP – Tạo SO phụ bổ sung từ SO chính"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
from types import SimpleNamespace

from helper.functions import (
    BG_COLOR, ACCENT, ACCENT_HOVER, TEXT_COLOR, CARD_BG, STATUS_BG,
    ROW_EVEN, ROW_ODD,
    BTN_SUCCESS, BTN_SUCCESS_HOVER,
    fetch_supplementary_so,
    _get_or_create_sap_session, reset_sap_session,
    on_enter_btn, on_leave_btn,
    bind_tree_shortcuts,
)

HEADER_BG = "#1b3a5c"
HEADER_FG = "#ffffff"


def build(root, frame_e):
    """Tạo toàn bộ UI và logic cho Tab E (Bổ sung mã SP)."""

    CURRENT_DATA_E = {}  # Lưu thông tin mainSO từ API response

    # ---- Card SO Chính ----
    card_search = tk.Frame(frame_e, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
    card_search.pack(fill=tk.X, padx=16, pady=(16, 8))

    inner_search = tk.Frame(card_search, bg=CARD_BG)
    inner_search.pack(fill=tk.X, padx=20, pady=16)

    tk.Label(inner_search, text="SO Chính", font=("Segoe UI", 10, "bold"),
             bg=CARD_BG, fg=TEXT_COLOR).grid(row=0, column=0, padx=(0, 8), sticky=tk.W)
    entry_main_e = tk.Entry(
        inner_search, width=20, font=("Segoe UI", 11), relief=tk.FLAT,
        bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT)
    entry_main_e.grid(row=1, column=0, padx=(0, 16), pady=(4, 0), ipady=5, sticky=tk.W)

    btn_open_modal = tk.Button(
        inner_search, text="Nhập mã SP", font=("Segoe UI", 10, "bold"),
        bg=ACCENT, fg="white", activebackground=ACCENT_HOVER, activeforeground="white",
        relief=tk.FLAT, cursor="hand2", padx=16, pady=4,
        command=lambda: open_input_modal())
    btn_open_modal.grid(row=1, column=1, padx=(0, 8), pady=(4, 0), ipady=3)
    btn_open_modal.bind("<Enter>", lambda e: on_enter_btn(e, ACCENT_HOVER))
    btn_open_modal.bind("<Leave>", lambda e: on_leave_btn(e, ACCENT))

    btn_update_e = tk.Button(
        inner_search, text="Đổ giá SAP", font=("Segoe UI", 10, "bold"),
        bg=BTN_SUCCESS, fg="white", activebackground=BTN_SUCCESS_HOVER, activeforeground="white",
        relief=tk.FLAT, cursor="hand2", padx=16, pady=4, command=lambda: do_update_price_e())
    btn_update_e.grid(row=1, column=2, padx=(0, 8), pady=(4, 0), ipady=3)
    btn_update_e.bind("<Enter>", lambda e: on_enter_btn(e, BTN_SUCCESS_HOVER))
    btn_update_e.bind("<Leave>", lambda e: on_leave_btn(e, BTN_SUCCESS))

    lbl_info_e = tk.Label(inner_search, text="", font=("Segoe UI", 9, "bold"),
                          bg=CARD_BG, fg=TEXT_COLOR, anchor=tk.W)
    lbl_info_e.grid(row=1, column=3, padx=(8, 0), pady=(4, 0), sticky=tk.W)

    # ---- Summary ----
    summary_frame = tk.Frame(frame_e, bg=BG_COLOR)
    summary_frame.pack(fill=tk.X, padx=20, pady=(4, 0))

    summary_labels_e = []
    for _i in range(6):
        lbl = tk.Label(summary_frame, text="", font=("Segoe UI", 9),
                       bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.W)
        lbl.grid(row=_i % 3, column=_i // 3, sticky=tk.W, padx=(0, 24))
        summary_labels_e.append(lbl)

    # ---- Bảng kết quả items_price ----
    card_table = tk.Frame(frame_e, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
    card_table.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 8))

    header_table = tk.Frame(card_table, bg=CARD_BG)
    header_table.pack(fill=tk.X, padx=12, pady=(8, 0))

    lbl_table_title = tk.Label(header_table, text="Danh sách mã SP bổ sung",
                               font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR, anchor=tk.W)
    lbl_table_title.pack(side=tk.LEFT)

    def _clear_table():
        for row in tree_result.get_children():
            tree_result.delete(row)
        lbl_table_title.config(text="Danh sách mã SP bổ sung")
        lbl_info_e.config(text="")
        for lbl in summary_labels_e:
            lbl.config(text="")
        CURRENT_DATA_E.clear()
        lbl_status_e.config(text="  Đã xóa danh sách")

    BTN_CLR_BG = "#e74c3c"
    BTN_CLR_HOVER = "#c0392b"
    btn_clear = tk.Button(
        header_table, text="Xóa danh sách", font=("Segoe UI", 9),
        bg=BTN_CLR_BG, fg="white", activebackground=BTN_CLR_HOVER, activeforeground="white",
        relief=tk.FLAT, cursor="hand2", padx=10, pady=1, command=_clear_table)
    btn_clear.pack(side=tk.RIGHT)
    btn_clear.bind("<Enter>", lambda e: on_enter_btn(e, BTN_CLR_HOVER))
    btn_clear.bind("<Leave>", lambda e: on_leave_btn(e, BTN_CLR_BG))

    tbl_frame = tk.Frame(card_table, bg=CARD_BG)
    tbl_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    cols_e = ("stt", "masp", "soluong", "nhom_nganh", "gia", "dieu_kien", "price_source")
    tree_result = ttk.Treeview(tbl_frame, columns=cols_e, show="headings",
                               height=12, style="Custom.Treeview", selectmode="extended")
    tree_result.heading("stt", text="STT")
    tree_result.heading("masp", text="Mã SP")
    tree_result.heading("soluong", text="Số lượng")
    tree_result.heading("nhom_nganh", text="Nhóm ngành")
    tree_result.heading("gia", text="Đơn giá")
    tree_result.heading("dieu_kien", text="Điều kiện")
    tree_result.heading("price_source", text="Nguồn giá")

    tree_result.column("stt", width=45, anchor=tk.CENTER, minwidth=35)
    tree_result.column("masp", width=110, anchor=tk.CENTER, minwidth=80)
    tree_result.column("soluong", width=80, anchor=tk.CENTER, minwidth=60)
    tree_result.column("nhom_nganh", width=160, anchor=tk.W, minwidth=100)
    tree_result.column("gia", width=100, anchor=tk.E, minwidth=70)
    tree_result.column("dieu_kien", width=180, anchor=tk.W, minwidth=100)
    tree_result.column("price_source", width=100, anchor=tk.CENTER, minwidth=70)

    tree_result.tag_configure("even", background=ROW_EVEN)
    tree_result.tag_configure("odd", background=ROW_ODD)

    sb_result = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL, command=tree_result.yview,
                              style="Custom.Vertical.TScrollbar")
    tree_result.configure(yscrollcommand=sb_result.set)
    tree_result.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sb_result.pack(side=tk.RIGHT, fill=tk.Y)

    # ---- Status bar ----
    status_bar_e = tk.Frame(frame_e, bg=STATUS_BG, height=32)
    status_bar_e.pack(fill=tk.X, padx=16, pady=(0, 12))
    status_bar_e.pack_propagate(False)

    lbl_status_e = tk.Label(status_bar_e, text="  Nhập SO Chính rồi nhấn Nhập mã SP",
                            font=("Segoe UI", 9), bg=STATUS_BG, fg="#5d6d7e", anchor=tk.W)
    lbl_status_e.pack(fill=tk.X, padx=8, pady=5)

    # ---- Bindings ----
    bind_tree_shortcuts(root, tree_result, masp_col_index=1, lbl_status=lbl_status_e)

    # ---- Helpers ----
    def _fill_result(items_price):
        # Xóa bảng cũ rồi fill lại (API trả về toàn bộ mã cũ + mới)
        for row in tree_result.get_children():
            tree_result.delete(row)
        for i, ip in enumerate(items_price, start=1):
            matnr = ip.get("MATNR", "").lstrip("0")
            qty = ip.get("KWMENG", "")
            nhom = ip.get("nhomNganh", "")
            net = ip.get("NET", "")
            net_fmt = f"{float(net):,.0f}" if net not in ("", None) else ""
            note = ip.get("note", "")
            src = ip.get("priceSource", "")
            tag = "even" if i % 2 == 0 else "odd"
            tree_result.insert("", tk.END, values=(i, matnr, qty, nhom, net_fmt, note, src), tags=(tag,))

    def _fill_summary(summary):
        msg_text = summary.get("message", "")
        parts = [p.strip() for p in msg_text.split("|") if p.strip()] if msg_text else []
        import math
        n_rows = max(math.ceil(len(parts) / 2), 3)
        # Rebuild labels if count differs
        if len(parts) != len(summary_labels_e):
            for lbl in summary_labels_e:
                lbl.destroy()
            summary_labels_e.clear()
            for idx in range(len(parts)):
                lbl = tk.Label(summary_frame, text="", font=("Segoe UI", 9),
                               bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.W)
                lbl.grid(row=idx % n_rows, column=idx // n_rows, sticky=tk.W, padx=(0, 24))
                summary_labels_e.append(lbl)
        for idx, part in enumerate(parts):
            summary_labels_e[idx].config(text=part)

    # ---- Modal nhập mã SP ----
    def open_input_modal():
        main_so = entry_main_e.get().strip()
        if not main_so:
            messagebox.showwarning("Thiếu SO", "Vui lòng nhập SO Chính trước.")
            entry_main_e.focus_set()
            return

        modal = tk.Toplevel(root)
        modal.title("Nhập mã SP bổ sung")
        modal.configure(bg=CARD_BG)
        modal.resizable(False, False)
        modal.transient(root)
        modal.grab_set()

        mw, mh = 460, 480
        modal.geometry(f"{mw}x{mh}+{root.winfo_x() + (root.winfo_width() - mw) // 2}+"
                       f"{root.winfo_y() + (root.winfo_height() - mh) // 2}")

        tk.Label(modal, text=f"SO Chính: {main_so}", font=("Segoe UI", 10, "bold"),
                 bg=CARD_BG, fg=TEXT_COLOR).pack(padx=16, pady=(12, 4), anchor=tk.W)

        # Scrollable frame for entry rows
        canvas_frame = tk.Frame(modal, bg=CARD_BG)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 4))

        canvas = tk.Canvas(canvas_frame, bg=CARD_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        rows_frame = tk.Frame(canvas, bg=CARD_BG)

        rows_frame.bind("<Configure>", lambda ev: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=rows_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _mw(ev):
            canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _mw)
        rows_frame.bind("<MouseWheel>", _mw)

        # Header
        tk.Label(rows_frame, text="Mã SP", font=("Segoe UI", 9, "bold"),
                 bg=CARD_BG, fg=TEXT_COLOR, width=20, anchor=tk.W).grid(row=0, column=0, padx=(0, 8), pady=(0, 4))
        tk.Label(rows_frame, text="Số lượng", font=("Segoe UI", 9, "bold"),
                 bg=CARD_BG, fg=TEXT_COLOR, width=12, anchor=tk.W).grid(row=0, column=1, padx=(0, 4), pady=(0, 4))

        modal_rows = []  # list of (entry_masp, entry_qty)

        def _add_modal_row():
            r = len(modal_rows) + 1
            e_m = tk.Entry(rows_frame, width=20, font=("Segoe UI", 10), relief=tk.FLAT,
                           bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT)
            e_m.grid(row=r, column=0, padx=(0, 8), pady=2, ipady=3)
            e_q = tk.Entry(rows_frame, width=12, font=("Segoe UI", 10), relief=tk.FLAT,
                           bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT)
            e_q.grid(row=r, column=1, padx=(0, 4), pady=2, ipady=3)
            e_m.bind("<Return>", lambda ev: e_q.focus_set())
            e_q.bind("<Return>", lambda ev: _add_modal_row())
            e_m.bind("<MouseWheel>", _mw)
            e_q.bind("<MouseWheel>", _mw)
            modal_rows.append((e_m, e_q))
            e_m.focus_set()
            canvas.update_idletasks()
            canvas.yview_moveto(1.0)

        # Tạo 5 dòng mặc định
        for _ in range(5):
            _add_modal_row()

        # Bottom buttons
        btn_frame = tk.Frame(modal, bg=CARD_BG)
        btn_frame.pack(fill=tk.X, padx=16, pady=(4, 12))

        btn_add_more = tk.Button(
            btn_frame, text="+ Thêm dòng", font=("Segoe UI", 9),
            bg="#ecf0f1", fg=TEXT_COLOR, relief=tk.FLAT, cursor="hand2", padx=10, pady=2,
            command=_add_modal_row)
        btn_add_more.pack(side=tk.LEFT)

        lbl_modal_status = tk.Label(btn_frame, text="", font=("Segoe UI", 9), bg=CARD_BG, fg="#c0392b")
        lbl_modal_status.pack(side=tk.LEFT, padx=(12, 0))

        def _do_submit():
            items_list = []
            for e_m, e_q in modal_rows:
                masp = e_m.get().strip()
                qty = e_q.get().strip()
                if not masp and not qty:
                    continue
                if not masp:
                    lbl_modal_status.config(text="Mã SP không được để trống")
                    e_m.focus_set()
                    return
                if not qty:
                    lbl_modal_status.config(text="Số lượng không được để trống")
                    e_q.focus_set()
                    return
                try:
                    qty_num = int(qty)
                except ValueError:
                    lbl_modal_status.config(text=f"Số lượng '{qty}' không hợp lệ")
                    e_q.focus_set()
                    return
                items_list.append({"materialCode": masp, "quantity": qty_num})
            if not items_list:
                lbl_modal_status.config(text="Vui lòng nhập ít nhất 1 mã SP")
                return

            # Gộp mã cũ (đang có trong bảng) + mã mới
            existing_items = []
            for row_id in tree_result.get_children():
                vals = tree_result.item(row_id, "values")
                masp_old = str(vals[1]).strip()
                qty_old = str(vals[2]).strip()
                if masp_old:
                    try:
                        qty_old_num = int(float(qty_old)) if qty_old else 1
                    except ValueError:
                        qty_old_num = 1
                    existing_items.append({"materialCode": masp_old, "quantity": qty_old_num})
            all_items = existing_items + items_list
            # Gộp mã SP trùng: cộng dồn số lượng
            merged = {}
            for it in all_items:
                code = it["materialCode"]
                if code in merged:
                    merged[code]["quantity"] += it["quantity"]
                else:
                    merged[code] = {"materialCode": code, "quantity": it["quantity"]}
            all_items = list(merged.values())
            items_json = json.dumps(all_items)
            btn_modal_submit.config(state=tk.DISABLED, text="Đang xử lý...")
            lbl_modal_status.config(text="", fg="#c0392b")

            def _call():
                data, error = fetch_supplementary_so(main_so, items_json)

                def _done():
                    btn_modal_submit.config(state=tk.NORMAL, text="Nhập mã")
                    if error:
                        lbl_modal_status.config(text=f"Lỗi: {error}", fg="#c0392b")
                    else:
                        modal.destroy()
                        # Hiển thị kết quả
                        _show_results(data, main_so)
                root.after(0, _done)
            threading.Thread(target=_call, daemon=True).start()

        btn_modal_submit = tk.Button(
            btn_frame, text="Nhập mã", font=("Segoe UI", 10, "bold"),
            bg=BTN_SUCCESS, fg="white", activebackground=BTN_SUCCESS_HOVER, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=16, pady=4, command=_do_submit)
        btn_modal_submit.pack(side=tk.RIGHT)
        btn_modal_submit.bind("<Enter>", lambda e: on_enter_btn(e, BTN_SUCCESS_HOVER))
        btn_modal_submit.bind("<Leave>", lambda e: on_leave_btn(e, BTN_SUCCESS))

    def _show_results(data, main_so):
        if not isinstance(data, dict):
            return
        main_info = data.get("mainSO", {})
        summary = data.get("summary", {})
        items_price = data.get("items_price", [])

        # Info label
        kh_code = main_info.get("customerCode", "").lstrip("0")
        kh_name = main_info.get("customerName", "")
        kdgrp = main_info.get("kdgrp", "")
        dealer_label = summary.get("dealerTypeLabel", data.get("dealerType", ""))
        lbl_info_e.config(text=f"KH: {kh_code} - {kh_name}  |  Loại: {dealer_label} - {kdgrp}")

        # Lưu thông tin KH cho SAP update
        CURRENT_DATA_E.clear()
        CURRENT_DATA_E["KUNNR"] = main_info.get("customerCode", "")
        CURRENT_DATA_E["NAME1"] = kh_name
        CURRENT_DATA_E["VKORG"] = main_info.get("salesOrg", "2001")

        # Summary
        _fill_summary(summary)

        # Table
        _fill_result(items_price)
        total = len(tree_result.get_children())
        lbl_table_title.config(text=f"Danh sách mã SP bổ sung  ({total} SP)")

        supp = summary.get("supplementary", {})
        lbl_status_e.config(
            text=f"  SO: {main_so}  |  {supp.get('totalItems', len(items_price))} SP bổ sung"
                 f"  |  Đạt giá: {supp.get('dealerPriceCount', '')}  |  Không đủ ĐK: {supp.get('noConditionCount', '')}")

    # ---- Đổ giá SAP ----
    def do_update_price_e():
        selected = tree_result.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn dòng", "Vui lòng chọn ít nhất một dòng để đổ giá.")
            return
        items = []
        for sel in selected:
            values = tree_result.item(sel, "values")
            gia = values[4].replace(",", "").strip()  # cột index 4 = Đơn giá
            if not gia:
                continue
            items.append({
                "masp": values[1], "tensp": "",
                "gia": gia, "gia_moi_fmt": values[4],
            })
        if not items:
            messagebox.showwarning("Không có giá", "Các dòng đã chọn không có đơn giá.")
            return

        # Gộp mã SP trùng: giữ giá của dòng đầu tiên
        seen = {}
        unique_items = []
        for it in items:
            if it["masp"] not in seen:
                seen[it["masp"]] = True
                unique_items.append(it)
        items = unique_items

        customer_code = CURRENT_DATA_E.get("KUNNR", "").lstrip("0")
        sales_org = CURRENT_DATA_E.get("VKORG", "2001")
        customer_name = CURRENT_DATA_E.get("NAME1", "")

        count = len(items)
        MAX_SHOW = 10
        detail_lines = [f"  {i+1}. SP: {it['masp']}  |  Giá: {it['gia_moi_fmt']}" for i, it in enumerate(items[:MAX_SHOW])]
        if count > MAX_SHOW:
            detail_lines.append(f"  ... và {count - MAX_SHOW} dòng nữa")
        detail = "\n".join(detail_lines)
        confirm = messagebox.askyesno("Xác nhận đổ giá",
            f"KH: {customer_code} - {customer_name}\nChi nhánh: {sales_org}\n\n"
            f"Đổ giá {count} sản phẩm?\n\n{detail}")
        if not confirm:
            return

        btn_update_e.config(state=tk.DISABLED, text="Đang xử lý...")
        lbl_status_e.config(text=f"  Đang xử lý {count} dòng...")
        root.update_idletasks()

        def _run():
            try:
                from helper.vk11 import updateMaterialV2
                session = _get_or_create_sap_session()
                if session == "MAX_SESSIONS":
                    root.after(0, lambda: messagebox.showwarning("Quá giới hạn session",
                        "Số session SAP đã đạt giới hạn tối đa.\n\nVui lòng đóng bớt các cửa sổ SAP đang mở rồi thử lại."))
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
                    root.after(0, lambda p=i+1: lbl_status_e.config(text=f"  Đã xử lý {p}/{count}..."))

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
                root.after(0, lambda: lbl_status_e.config(text=f"  Hoàn tất: {success}/{count} thành công"))
            except Exception as ex:
                reset_sap_session()
                root.after(0, lambda e=ex: messagebox.showerror("Lỗi", f"Đổ giá thất bại:\n{e}"))
                root.after(0, lambda e=ex: lbl_status_e.config(text=f"  Lỗi: {e}"))
            finally:
                root.after(0, lambda: btn_update_e.config(state=tk.NORMAL, text="Đổ giá SAP"))
        threading.Thread(target=_run, daemon=True).start()

    return SimpleNamespace(entry_main_e=entry_main_e)
