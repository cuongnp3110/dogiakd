"""Tab D: SO Phụ – So sánh SO chính & SO phụ"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from types import SimpleNamespace

from helper.functions import (
    BG_COLOR, ACCENT, TEXT_COLOR, CARD_BG, STATUS_BG,
    ROW_EVEN, ROW_ODD,
    BTN_SUCCESS, BTN_SUCCESS_HOVER,
    fetch_compare_so,
    _get_or_create_sap_session, reset_sap_session,
    on_enter_btn, on_leave_btn,
    bind_tree_shortcuts,
)


def build(root, frame_d):
    """Tạo toàn bộ UI và logic cho Tab D (SO Phụ)."""

    CURRENT_HEADER_D = {}

    # ---- Loading overlay ----
    _state = {"frame": None, "label": None, "anim_id": None, "dots": 0}

    def show_loading(msg="Đang tải dữ liệu"):
        hide_loading()
        _state["dots"] = 0
        _state["frame"] = tk.Frame(frame_d, bg=BG_COLOR)
        _state["frame"].place(relx=0.5, rely=0.55, anchor=tk.CENTER, width=300, height=80)
        _state["label"] = tk.Label(
            _state["frame"], text=msg, font=("Segoe UI", 12), bg=BG_COLOR, fg=TEXT_COLOR)
        _state["label"].pack(expand=True)
        _animate(msg)

    def _animate(base_msg):
        if _state["label"] and _state["label"].winfo_exists():
            _state["dots"] = (_state["dots"] % 3) + 1
            _state["label"].config(text=base_msg + "." * _state["dots"])
            _state["anim_id"] = root.after(400, lambda: _animate(base_msg))

    def hide_loading():
        if _state["anim_id"]:
            root.after_cancel(_state["anim_id"])
            _state["anim_id"] = None
        if _state["frame"]:
            _state["frame"].destroy()
            _state["frame"] = None
            _state["label"] = None

    # ---- Helpers ----
    def _build_items(items, items_price):
        """Tạo danh sách dòng cho bảng từ items + items_price."""
        price_map = {}
        for ip in items_price:
            matnr = ip.get("MATNR", "").lstrip("0")
            price_map[matnr] = {
                "net": ip.get("NET", 0),
                "note": ip.get("note", ""),
                "nhom_nganh": ip.get("nhomNganh", ""),
            }
        rows = []
        for it in items:
            matnr = it.get("MATNR", "").lstrip("0")
            dongia = float(it.get("NETPR", 0))
            gia_cu = float(it.get("NETWR", 0))
            pm = price_map.get(matnr, {})
            gia_moi = pm.get("net", "") if pm else ""
            dieu_kien = pm.get("note", "") if pm else ""
            nhom_nganh = pm.get("nhom_nganh", "") if pm else ""
            rows.append({
                "masp": matnr, "tensp": it.get("ARKTX", ""),
                "soluong": it.get("KWMENG", "0").replace(".000", ""),
                "thue": it.get("TAXKM_TEXT", ""),
                "dongia": dongia, "gia_cu": gia_cu,
                "gia_moi": gia_moi, "dieu_kien": dieu_kien,
                "nhom_nganh": nhom_nganh,
            })
        return rows

    def _fill_tree(tree, rows):
        for row in tree.get_children():
            tree.delete(row)
        for i, item in enumerate(rows, start=1):
            dongia_fmt = f"{item['dongia']:,.0f}" if item['dongia'] else ""
            gia_cu_fmt = f"{item['gia_cu']:,.0f}" if item['gia_cu'] else ""
            gia_moi_fmt = f"{item['gia_moi']:,.0f}" if item['gia_moi'] not in ("", None) else ""
            tag = "even" if i % 2 == 0 else "odd"
            tree.insert("", tk.END, values=(
                i, item["masp"], item["tensp"], item["soluong"], item["thue"],
                dongia_fmt, gia_cu_fmt, gia_moi_fmt,
                item.get("dieu_kien", ""), item.get("nhom_nganh", "")
            ), tags=(tag,))

    # ---- SAP update ----
    def do_update_price_d():
        selected = tree_sub.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn dòng", "Vui lòng chọn ít nhất một dòng trong bảng SO Phụ để đổ giá.")
            return
        items = []
        for sel in selected:
            values = tree_sub.item(sel, "values")
            gia_moi = values[7].replace(",", "").strip()  # cột index 7 = gia_moi
            if not gia_moi:
                continue
            items.append({
                "masp": values[1], "tensp": values[2],
                "gia": gia_moi, "gia_moi_fmt": values[7],
            })
        if not items:
            messagebox.showwarning("Không có giá mới", "Các dòng đã chọn không có giá mới.")
            return

        customer_code = CURRENT_HEADER_D.get("KUNNR", "").lstrip("0")
        sales_org = CURRENT_HEADER_D.get("VKORG", "2001")
        customer_name = CURRENT_HEADER_D.get("NAME1", "")

        count = len(items)
        MAX_SHOW = 10
        detail_lines = [f"  {i+1}. SP: {it['masp']}  |  Giá mới: {it['gia_moi_fmt']}" for i, it in enumerate(items[:MAX_SHOW])]
        if count > MAX_SHOW:
            detail_lines.append(f"  ... và {count - MAX_SHOW} dòng nữa")
        detail = "\n".join(detail_lines)
        confirm = messagebox.askyesno("Xác nhận đổ giá",
            f"KH: {customer_code} - {customer_name}\nChi nhánh: {sales_org}\n\n"
            f"Đổ giá {count} sản phẩm?\n\n{detail}")
        if not confirm:
            return

        btn_update_d.config(state=tk.DISABLED, text="Đang xử lý...")
        lbl_status_d.config(text=f"  Đang xử lý {count} dòng...")
        root.update_idletasks()

        def _run():
            try:
                from helper.vk11 import updateMaterialV3
                session = _get_or_create_sap_session()
                if session == "MAX_SESSIONS":
                    root.after(0, lambda: messagebox.showwarning("Quá giới hạn session",
                        "Số session SAP đã đạt giới hạn tối đa.\n\nVui lòng đóng bớt các cửa sổ SAP đang mở rồi thử lại."))
                    return
                if session is None:
                    root.after(0, lambda: messagebox.showerror("Lỗi", "Không thể kết nối SAP. Kiểm tra lại cấu hình."))
                    return

                mat_list = [{"masp": it["masp"], "gia": it["gia"]} for it in items]
                results = updateMaterialV3(session, customer_code, mat_list, sales_org)

                success = 0
                errors = []
                for i, r in enumerate(results):
                    if r["status"] == "ok":
                        success += 1
                    else:
                        errors.append(f"{r['masp']}: {r['msg']}")
                    root.after(0, lambda p=i+1: lbl_status_d.config(text=f"  Đã xử lý {p}/{count}..."))

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
                root.after(0, lambda: lbl_status_d.config(text=f"  Hoàn tất: {success}/{count} thành công"))
            except Exception as ex:
                reset_sap_session()
                root.after(0, lambda e=ex: messagebox.showerror("Lỗi", f"Đổ giá thất bại:\n{e}"))
                root.after(0, lambda e=ex: lbl_status_d.config(text=f"  Lỗi: {e}"))
            finally:
                root.after(0, lambda: btn_update_d.config(state=tk.NORMAL, text="Đổ giá SAP"))
        threading.Thread(target=_run, daemon=True).start()

    # ---- Search ----
    def on_compare(event=None):
        main_so = entry_main.get().strip()
        sub_so = entry_sub.get().strip()
        if not main_so or not sub_so:
            return
        lbl_status_d.config(text="  Đang so sánh SO...")
        show_loading("Đang so sánh SO chính & SO phụ")
        root.update_idletasks()

        def _fetch():
            data, error = fetch_compare_so(main_so, sub_so)
            if error:
                root.after(0, hide_loading)
                root.after(0, lambda: lbl_status_d.config(text=f"  Lỗi: {error}"))
                return
            main_data = data.get("mainSO", {})
            sub_data = data.get("subSO", {})
            summary = data.get("summary", {})
            warnings = data.get("warnings", None)

            main_header = main_data.get("header", {})
            sub_header = sub_data.get("header", {})
            CURRENT_HEADER_D.clear()
            CURRENT_HEADER_D.update(sub_header)
            main_rows = _build_items(main_data.get("items", []), main_data.get("items_price", []))
            sub_rows = _build_items(sub_data.get("items", []), sub_data.get("items_price", []))

            def _update_ui():
                hide_loading()
                # Fill info
                lbl_info_d.config(text=(
                    f"KH: {main_header.get('KUNNR', '').lstrip('0')} - {main_header.get('NAME1', '')}"
                    f"  |  Nhóm: {main_header.get('KDGRP_TEXT', '')}"
                    f"  |  NV: {main_header.get('TEN_NV', '')}"
                ))
                # Summary message → tách theo |
                msg_text = summary.get("message", "")
                parts = [p.strip() for p in msg_text.split("|") if p.strip()] if msg_text else []
                # Nếu số phần khác → tạo lại labels
                if len(parts) != len(summary_labels_d):
                    for lbl in summary_labels_d:
                        lbl.destroy()
                    summary_labels_d.clear()
                    import math
                    n_rows = math.ceil(len(parts) / 2) if parts else 3
                    for idx in range(len(parts)):
                        lbl = tk.Label(summary_frame, text="-", font=("Segoe UI", 9),
                                       bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.W)
                        lbl.grid(row=idx % n_rows, column=idx // n_rows, sticky=tk.W, padx=(0, 24))
                        summary_labels_d.append(lbl)
                # Cập nhật text
                for idx, part in enumerate(parts):
                    summary_labels_d[idx].config(text=part)

                # Main SO table
                lbl_main_title.config(text=f"SO Chính: {main_so}  ({len(main_rows)} SP)")
                _fill_tree(tree_main, main_rows)

                # Sub SO table
                lbl_sub_title.config(text=f"SO Phụ: {sub_so}  ({len(sub_rows)} SP)")
                _fill_tree(tree_sub, sub_rows)

                lbl_status_d.config(text=f"  SO Chính: {main_so} ({len(main_rows)} SP)  |  SO Phụ: {sub_so} ({len(sub_rows)} SP)")

                # Warnings
                if warnings:
                    warn_text = warnings[0] if isinstance(warnings, list) and len(warnings) > 0 else str(warnings)
                    lbl_warning_d.config(text=f"⚠ {warn_text}")
                    lbl_warning_d.pack(fill=tk.X, padx=20, pady=(2, 0))
                else:
                    lbl_warning_d.config(text="")
                    lbl_warning_d.pack_forget()

            root.after(0, _update_ui)
        threading.Thread(target=_fetch, daemon=True).start()

    # ==================================================================
    #  UI
    # ==================================================================

    # ---- Card tìm kiếm ----
    card_search = tk.Frame(frame_d, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
    card_search.pack(fill=tk.X, padx=16, pady=(16, 8))

    inner_search = tk.Frame(card_search, bg=CARD_BG)
    inner_search.pack(fill=tk.X, padx=20, pady=16)

    tk.Label(inner_search, text="SO Chính", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
        row=0, column=0, padx=(0, 8), sticky=tk.W)
    entry_main = tk.Entry(
        inner_search, width=20, font=("Segoe UI", 11), relief=tk.FLAT,
        bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT)
    entry_main.grid(row=1, column=0, padx=(0, 16), pady=(4, 0), ipady=5, sticky=tk.W)
    entry_main.bind("<Return>", on_compare)

    tk.Label(inner_search, text="SO Phụ", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
        row=0, column=1, padx=(0, 8), sticky=tk.W)
    entry_sub = tk.Entry(
        inner_search, width=20, font=("Segoe UI", 11), relief=tk.FLAT,
        bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT)
    entry_sub.grid(row=1, column=1, padx=(0, 16), pady=(4, 0), ipady=5, sticky=tk.W)
    entry_sub.bind("<Return>", on_compare)

    btn_update_d = tk.Button(
        inner_search, text="Đổ giá SAP", font=("Segoe UI", 10, "bold"),
        bg=BTN_SUCCESS, fg="white", activebackground=BTN_SUCCESS_HOVER, activeforeground="white",
        relief=tk.FLAT, cursor="hand2", padx=16, pady=4, command=do_update_price_d)
    btn_update_d.grid(row=1, column=2, padx=(0, 8), pady=(4, 0), ipady=3)
    btn_update_d.bind("<Enter>", lambda e: on_enter_btn(e, BTN_SUCCESS_HOVER))
    btn_update_d.bind("<Leave>", lambda e: on_leave_btn(e, BTN_SUCCESS))

    lbl_info_d = tk.Label(inner_search, text="", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=TEXT_COLOR, anchor=tk.W)
    lbl_info_d.grid(row=1, column=3, padx=(16, 0), pady=(4, 0), sticky=tk.W)

    # ---- Summary (giữa search và bảng) ----
    summary_frame = tk.Frame(frame_d, bg=BG_COLOR)
    summary_frame.pack(fill=tk.X, padx=20, pady=(4, 0))

    summary_labels_d = []
    for _i in range(6):
        lbl = tk.Label(summary_frame, text="-", font=("Segoe UI", 9),
                       bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.W)
        lbl.grid(row=_i % 3, column=_i // 3, sticky=tk.W, padx=(0, 24))
        summary_labels_d.append(lbl)

    lbl_warning_d = tk.Label(frame_d, text="", font=("Segoe UI", 9), bg=BG_COLOR, fg="#c62828", anchor=tk.W)

    # ---- Khu vực 2 bảng (dùng PanedWindow cho chia đôi) ----
    pane = tk.PanedWindow(frame_d, orient=tk.VERTICAL, bg=BG_COLOR, sashwidth=6, sashrelief=tk.FLAT)
    pane.pack(fill=tk.BOTH, expand=True, padx=16, pady=(1, 8))

    # ---- Bảng SO Chính ----
    frame_main = tk.Frame(pane, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
    pane.add(frame_main, stretch="always")

    lbl_main_title = tk.Label(frame_main, text="SO Chính", font=("Segoe UI", 10, "bold"),
                              bg=CARD_BG, fg=TEXT_COLOR, anchor=tk.W)
    lbl_main_title.pack(fill=tk.X, padx=12, pady=(8, 0))

    tbl_main = tk.Frame(frame_main, bg=CARD_BG)
    tbl_main.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    cols = ("stt", "masp", "tensp", "soluong", "thue", "dongia", "gia_cu", "gia_moi", "dieu_kien", "nhom_nganh")
    tree_main = ttk.Treeview(tbl_main, columns=cols, show="headings", height=7, style="Custom.Treeview", selectmode="extended")
    _setup_tree(tree_main)
    tree_main.tag_configure("even", background=ROW_EVEN)
    tree_main.tag_configure("odd", background=ROW_ODD)

    sb_main = ttk.Scrollbar(tbl_main, orient=tk.VERTICAL, command=tree_main.yview, style="Custom.Vertical.TScrollbar")
    tree_main.configure(yscrollcommand=sb_main.set)
    tree_main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sb_main.pack(side=tk.RIGHT, fill=tk.Y)

    # ---- Bảng SO Phụ ----
    frame_sub = tk.Frame(pane, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
    pane.add(frame_sub, stretch="always")

    lbl_sub_title = tk.Label(frame_sub, text="SO Phụ", font=("Segoe UI", 10, "bold"),
                             bg=CARD_BG, fg=TEXT_COLOR, anchor=tk.W)
    lbl_sub_title.pack(fill=tk.X, padx=12, pady=(8, 0))

    tbl_sub = tk.Frame(frame_sub, bg=CARD_BG)
    tbl_sub.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    tree_sub = ttk.Treeview(tbl_sub, columns=cols, show="headings", height=7, style="Custom.Treeview", selectmode="extended")
    _setup_tree(tree_sub)
    tree_sub.tag_configure("even", background=ROW_EVEN)
    tree_sub.tag_configure("odd", background=ROW_ODD)

    sb_sub = ttk.Scrollbar(tbl_sub, orient=tk.VERTICAL, command=tree_sub.yview, style="Custom.Vertical.TScrollbar")
    tree_sub.configure(yscrollcommand=sb_sub.set)
    tree_sub.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sb_sub.pack(side=tk.RIGHT, fill=tk.Y)

    # ---- Status bar ----
    status_bar_d = tk.Frame(frame_d, bg=STATUS_BG, height=32)
    status_bar_d.pack(fill=tk.X, padx=16, pady=(0, 12))
    status_bar_d.pack_propagate(False)

    lbl_status_d = tk.Label(status_bar_d, text="  Nhập SO Chính và SO Phụ rồi nhấn Enter",
                            font=("Segoe UI", 9), bg=STATUS_BG, fg="#5d6d7e", anchor=tk.W)
    lbl_status_d.pack(fill=tk.X, padx=8, pady=5)

    # ---- Bindings ----
    bind_tree_shortcuts(root, tree_main, masp_col_index=1, lbl_status=lbl_status_d)
    paste_and_select_sub = bind_tree_shortcuts(root, tree_sub, masp_col_index=1, lbl_status=lbl_status_d)

    return SimpleNamespace(entry_main=entry_main, entry_sub=entry_sub, lbl_status_d=lbl_status_d, paste_and_select_sub=paste_and_select_sub)


def _setup_tree(tree):
    """Cấu hình heading + column chung cho cả 2 bảng."""
    tree.heading("stt", text="STT")
    tree.heading("masp", text="Mã SP")
    tree.heading("tensp", text="Tên SP")
    tree.heading("soluong", text="Số lượng")
    tree.heading("thue", text="Thuế")
    tree.heading("dongia", text="Giá cũ")
    tree.heading("gia_cu", text="Tổng")
    tree.heading("gia_moi", text="Giá mới")
    tree.heading("dieu_kien", text="Điều kiện")
    tree.heading("nhom_nganh", text="Nhóm ngành")

    tree.column("stt", width=40, anchor=tk.CENTER, minwidth=35)
    tree.column("masp", width=100, anchor=tk.CENTER, minwidth=70)
    tree.column("tensp", width=200, anchor=tk.W, minwidth=120)
    tree.column("soluong", width=70, anchor=tk.CENTER, minwidth=50)
    tree.column("thue", width=90, anchor=tk.CENTER, minwidth=60)
    tree.column("dongia", width=80, anchor=tk.E, minwidth=60)
    tree.column("gia_cu", width=90, anchor=tk.E, minwidth=60)
    tree.column("gia_moi", width=80, anchor=tk.E, minwidth=60)
    tree.column("dieu_kien", width=120, anchor=tk.W, minwidth=80)
    tree.column("nhom_nganh", width=120, anchor=tk.W, minwidth=80)
