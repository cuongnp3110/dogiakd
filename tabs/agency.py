"""Tab B: Đổ giá đại lý"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from types import SimpleNamespace

from helper.functions import (
    BG_COLOR, ACCENT, TEXT_COLOR, CARD_BG, STATUS_BG,
    ROW_EVEN, ROW_ODD, BTN_SUCCESS, BTN_SUCCESS_HOVER,
    fetch_sale_order,
    _get_or_create_sap_session, reset_sap_session,
    on_enter_btn, on_leave_btn,
    bind_tree_shortcuts,
)


def build(root, frame_b):
    """Tạo toàn bộ UI và logic cho Tab B. Trả về namespace chứa widgets cần thiết."""

    CURRENT_DATA_B = []
    CURRENT_HEADER_B = {}

    # ---- Loading overlay ----
    _state = {"frame": None, "label": None, "anim_id": None, "dots": 0}

    def show_loading_b(msg="Đang tải dữ liệu"):
        hide_loading_b()
        _state["dots"] = 0
        _state["frame"] = tk.Frame(frame_b, bg=BG_COLOR)
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

    def hide_loading_b():
        if _state["anim_id"]:
            root.after_cancel(_state["anim_id"])
            _state["anim_id"] = None
        if _state["frame"]:
            _state["frame"].destroy()
            _state["frame"] = None
            _state["label"] = None

    # ---- Logic functions ----
    def on_search_sale_order(event=None):
        nonlocal CURRENT_DATA_B, CURRENT_HEADER_B
        so = entry_so.get().strip()
        if not so:
            return
        for row in tree_b.get_children():
            tree_b.delete(row)
        lbl_status_b.config(text="  Đang tải dữ liệu...")
        show_loading_b("Đang tải Sale Order")
        root.update_idletasks()

        def _fetch():
            nonlocal CURRENT_DATA_B, CURRENT_HEADER_B
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

            price_map = {}
            for ip in items_price:
                matnr = ip.get("MATNR", "").lstrip("0")
                price_map[matnr] = {"net": ip.get("NET", 0), "note": ip.get("note", ""), "nhom_nganh": ip.get("nhomNganh", "")}

            result = []
            for it in items:
                matnr_raw = it.get("MATNR", "")
                matnr = matnr_raw.lstrip("0")
                dongia = float(it.get("NETPR", 0))
                gia_cu = float(it.get("NETWR", 0))
                pm = price_map.get(matnr, {})
                gia_moi = pm.get("net", "") if pm else ""
                dieu_kien = pm.get("note", "") if pm else ""
                nhom_nganh = pm.get("nhom_nganh", "") if pm else ""
                result.append({
                    "masp": matnr, "tensp": it.get("ARKTX", ""),
                    "soluong": it.get("KWMENG", "0").replace(".000", ""),
                    "thue": it.get("TAXKM_TEXT", ""),
                    "dongia": dongia, "gia_cu": gia_cu,
                    "gia_moi": gia_moi, "dieu_kien": dieu_kien,
                    "nhom_nganh": nhom_nganh,
                })
            CURRENT_DATA_B = result

            cust_info = f"{header.get('KUNNR', '').lstrip('0')} - {header.get('NAME1', '')}"
            branch = header.get("VKORG_TEXT", "")
            root.after(0, lambda: hide_loading_b())
            root.after(0, lambda: _show_results_b(result, cust_info, branch, warnings, order_summary, header))
        threading.Thread(target=_fetch, daemon=True).start()

    def _show_results_b(results, cust_info="", branch="", warnings=None, order_summary=None, header=None):
        for row in tree_b.get_children():
            tree_b.delete(row)
        filtered = [item for item in results if item['gia_moi'] not in ("", None)]
        for i, item in enumerate(filtered, start=1):
            dongia_fmt = f"{item['dongia']:,.0f}" if item['dongia'] else ""
            gia_cu_fmt = f"{item['gia_cu']:,.0f}" if item['gia_cu'] else ""
            gia_moi_fmt = f"{item['gia_moi']:,.0f}"
            try:
                soluong_num = float(item['soluong']) if item['soluong'] else 0
                gia_moi_num = float(item['gia_moi']) if item['gia_moi'] else 0
                tong_moi = soluong_num * gia_moi_num
                tong_moi_fmt = f"{tong_moi:,.0f}" if tong_moi else ""
            except (ValueError, TypeError):
                tong_moi_fmt = ""
            dieu_kien = item.get("dieu_kien", "")
            nhom_nganh = item.get("nhom_nganh", "")
            thue = item.get("thue", "")
            is_diff = item['dongia'] and item['gia_moi'] and float(item['dongia']) != float(item['gia_moi'])
            if is_diff:
                tag = "diff_even" if i % 2 == 0 else "diff_odd"
            else:
                tag = "even" if i % 2 == 0 else "odd"
            tree_b.insert("", tk.END, values=(
                i, item["masp"], item["tensp"], item["soluong"], thue,
                dongia_fmt, gia_cu_fmt, gia_moi_fmt, tong_moi_fmt, dieu_kien, nhom_nganh
            ), tags=(tag,))
        # Tính tổng cũ (giá gốc từ API) và tổng mới (giá chiết khấu trên SO)
        sum_cu = 0
        sum_moi = 0
        for item in filtered:
            try:
                sl = float(item['soluong']) if item['soluong'] else 0
                dg = float(item['dongia']) if item['dongia'] else 0
                gm = float(item['gia_moi']) if item['gia_moi'] else 0
                sum_cu += sl * gm
                sum_moi += sl * dg
            except (ValueError, TypeError):
                pass
        diff = sum_moi - sum_cu
        tree_b.insert("", tk.END, values=(
            "", "", "TỔNG CỘNG", "", "",
            "", f"{sum_cu:,.0f}", "",
            f"{sum_moi:,.0f}",
            f"CK: {abs(diff):,.0f}", ""
        ), tags=("summary",))

        info_txt = f"  SO: {entry_so.get().strip()}"
        if cust_info:
            info_txt += f"  |  KH: {cust_info}"
        if branch:
            info_txt += f"  |  {branch}"
        info_txt += f"  |  {len(filtered)} sản phẩm"
        lbl_status_b.config(text=info_txt)
        # Dòng 1: Thông tin đại lý
        if header:
            name1 = header.get("NAME1", "")
            kdgrp_text = header.get("KDGRP_TEXT", "")
            ten_nv = header.get("TEN_NV", "")
            parts = []
            if name1:
                parts.append(f"Tên đại lý: {name1}")
            if kdgrp_text:
                parts.append(f"Nhóm: {kdgrp_text}")
            if ten_nv:
                parts.append(f"Tên nhân viên: {ten_nv}")
            lbl_info_b.config(text="  |  ".join(parts) if parts else "")
        else:
            lbl_info_b.config(text="")
        # Dòng 2: Order summary
        if header:
            dealer_type_label = ""
            condition_level = ""
            if order_summary and isinstance(order_summary, dict):
                dealer_type_label = order_summary.get("dealerTypeLabel", "")
                gs = order_summary.get("groupStats", {})
                if isinstance(gs, dict):
                    condition_level = gs.get("conditionLevel", "")
                elif isinstance(gs, list) and gs:
                    condition_level = gs[0].get("conditionLevel", "")
            tong_sp = len(results)
            sp_dat_muc = len(filtered)
            kdgrp = header.get("KDGRP", "")
            loai_kh_txt = dealer_type_label
            if dealer_type_label and kdgrp:
                loai_kh_txt = f"{dealer_type_label} - {kdgrp}"
            elif kdgrp:
                loai_kh_txt = kdgrp
            lbl_loai_kh_b.config(text=f"Loại khách hàng: {loai_kh_txt}")
            lbl_tong_sl_b.config(text=f"Tổng số lượng sản phẩm: {tong_sp}")
            lbl_dieu_kien_b.config(text=f"Điều kiện: {condition_level}")
            lbl_sp_dat_muc_b.config(text=f"SP đạt mức số lượng: {sp_dat_muc}")
        else:
            lbl_loai_kh_b.config(text="Loại khách hàng:")
            lbl_tong_sl_b.config(text="Tổng số lượng sản phẩm:")
            lbl_dieu_kien_b.config(text="Điều kiện:")
            lbl_sp_dat_muc_b.config(text="SP đạt mức số lượng:")
        # Hiện warning
        if warnings:
            warn_text = warnings[0] if isinstance(warnings, list) and len(warnings) > 0 else str(warnings)
            lbl_warning_b.config(text=f"⚠ {warn_text}")
            lbl_warning_b.pack(fill=tk.X, padx=20, pady=(2, 0))
        else:
            lbl_warning_b.config(text="")
            lbl_warning_b.pack_forget()

    def do_update_price_b():
        selected = tree_b.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn dòng", "Vui lòng chọn ít nhất một dòng trong bảng để đổ giá.")
            return
        items = []
        for sel in selected:
            values = tree_b.item(sel, "values")
            gia_moi = values[7].replace(",", "").strip()  # cột index 7 = Giá mới
            if not gia_moi:
                continue
            items.append({
                "masp": values[1], "tensp": values[2],
                "gia": gia_moi, "gia_moi_fmt": values[7],  # index 7 = Giá mới
            })
        if not items:
            messagebox.showwarning("Không có giá mới", "Các dòng đã chọn không có giá mới.")
            return

        customer_code = CURRENT_HEADER_B.get("KUNNR", "").lstrip("0")
        sales_org = CURRENT_HEADER_B.get("VKORG", "2001")
        customer_name = CURRENT_HEADER_B.get("NAME1", "")

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

        btn_update_b.config(state=tk.DISABLED, text="Đang xử lý...")
        lbl_status_b.config(text=f"  Đang xử lý {count} dòng...")
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
                reset_sap_session()
                root.after(0, lambda e=ex: messagebox.showerror("Lỗi", f"Đổ giá thất bại:\n{e}"))
                root.after(0, lambda e=ex: lbl_status_b.config(text=f"  Lỗi: {e}"))
            finally:
                root.after(0, lambda: btn_update_b.config(state=tk.NORMAL, text="Đổ giá SAP"))
        threading.Thread(target=_run, daemon=True).start()

    # ---- UI: Card tìm kiếm ----
    card_search_b = tk.Frame(frame_b, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
    card_search_b.pack(fill=tk.X, padx=16, pady=(16, 8))

    inner_search_b = tk.Frame(card_search_b, bg=CARD_BG)
    inner_search_b.pack(fill=tk.X, padx=20, pady=16)

    tk.Label(inner_search_b, text="Sale Order", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT_COLOR).grid(
        row=0, column=0, padx=(0, 24), sticky=tk.W)

    entry_so = tk.Entry(
        inner_search_b, width=24, font=("Segoe UI", 11), relief=tk.FLAT,
        bg="#f5f7fa", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor=ACCENT)
    entry_so.grid(row=1, column=0, padx=(0, 24), pady=(4, 0), ipady=5, sticky=tk.W)
    entry_so.bind("<Return>", on_search_sale_order)

    btn_update_b = tk.Button(
        inner_search_b, text="Đổ giá SAP", font=("Segoe UI", 10, "bold"),
        bg=BTN_SUCCESS, fg="white", activebackground=BTN_SUCCESS_HOVER, activeforeground="white",
        relief=tk.FLAT, cursor="hand2", padx=16, pady=4, command=do_update_price_b)
    btn_update_b.grid(row=1, column=1, padx=(0, 8), pady=(4, 0), ipady=3)
    btn_update_b.bind("<Enter>", lambda e: on_enter_btn(e, BTN_SUCCESS_HOVER))
    btn_update_b.bind("<Leave>", lambda e: on_leave_btn(e, BTN_SUCCESS))

    lbl_info_b = tk.Label(inner_search_b, text="", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=TEXT_COLOR, anchor=tk.W)
    lbl_info_b.grid(row=1, column=2, columnspan=2, padx=(16, 0), pady=(4, 0), sticky=tk.W)

    # ---- UI: Thông tin order (giữa search card và bảng) ----
    summary_frame_b = tk.Frame(frame_b, bg=BG_COLOR)
    summary_frame_b.pack(fill=tk.X, padx=20, pady=(4, 0))

    lbl_loai_kh_b = tk.Label(summary_frame_b, text="Loại khách hàng:", font=("Segoe UI", 9), bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.W)
    lbl_loai_kh_b.pack(fill=tk.X)
    lbl_tong_sl_b = tk.Label(summary_frame_b, text="Tổng số lượng sản phẩm:", font=("Segoe UI", 9), bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.W) 
    lbl_tong_sl_b.pack(fill=tk.X)
    lbl_dieu_kien_b = tk.Label(summary_frame_b, text="Điều kiện:", font=("Segoe UI", 9), bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.W)
    lbl_dieu_kien_b.pack(fill=tk.X)
    lbl_sp_dat_muc_b = tk.Label(summary_frame_b, text="SP đạt mức số lượng:", font=("Segoe UI", 9), bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.W)
    lbl_sp_dat_muc_b.pack(fill=tk.X)

    lbl_warning_b = tk.Label(frame_b, text="", font=("Segoe UI", 9), bg=BG_COLOR, fg="#c62828", anchor=tk.W)

    # ---- UI: Card bảng dữ liệu ----
    card_table_b = tk.Frame(frame_b, bg=CARD_BG, bd=0, highlightthickness=1, highlightbackground="#dce6f0")
    card_table_b.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 8))

    tbl_frame_b = tk.Frame(card_table_b, bg=CARD_BG)
    tbl_frame_b.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    columns_b = ("stt", "masp", "tensp", "soluong", "thue", "dongia", "gia_cu", "gia_moi", "tong_moi", "dieu_kien", "nhom_nganh")
    tree_b = ttk.Treeview(tbl_frame_b, columns=columns_b, show="headings", height=14, style="Custom.Treeview", selectmode="extended")

    tree_b.heading("stt", text="STT")
    tree_b.heading("masp", text="Mã SP")
    tree_b.heading("tensp", text="Tên SP")
    tree_b.heading("soluong", text="Số lượng")
    tree_b.heading("thue", text="Thuế")
    tree_b.heading("dongia", text="Giá cũ")
    tree_b.heading("gia_cu", text="Tổng cũ")
    tree_b.heading("gia_moi", text="Giá mới")
    tree_b.heading("tong_moi", text="Tổng mới")
    tree_b.heading("dieu_kien", text="Điều kiện")
    tree_b.heading("nhom_nganh", text="Nhóm ngành")

    tree_b.column("stt", width=50, anchor=tk.CENTER, minwidth=40)
    tree_b.column("masp", width=120, anchor=tk.CENTER, minwidth=80)
    tree_b.column("tensp", width=200, anchor=tk.W, minwidth=130)
    tree_b.column("soluong", width=65, anchor=tk.CENTER, minwidth=50)
    tree_b.column("thue", width=80, anchor=tk.W, minwidth=60)
    tree_b.column("dongia", width=85, anchor=tk.E, minwidth=65)
    tree_b.column("gia_cu", width=85, anchor=tk.E, minwidth=65)
    tree_b.column("gia_moi", width=85, anchor=tk.E, minwidth=65)
    tree_b.column("tong_moi", width=95, anchor=tk.E, minwidth=70)
    tree_b.column("dieu_kien", width=120, anchor=tk.W, minwidth=80)
    tree_b.column("nhom_nganh", width=120, anchor=tk.W, minwidth=80)

    tree_b.tag_configure("odd", background=ROW_ODD)
    tree_b.tag_configure("even", background=ROW_EVEN)
    tree_b.tag_configure("diff_odd", background="#fff3cd")
    tree_b.tag_configure("diff_even", background="#ffeeba")
    tree_b.tag_configure("summary", background="#d5e8d4", font=("Segoe UI", 10, "bold"))

    tbl_frame_b.columnconfigure(0, weight=1)
    tbl_frame_b.rowconfigure(0, weight=1)
    scrollbar_b = ttk.Scrollbar(tbl_frame_b, orient=tk.VERTICAL, command=tree_b.yview, style="Custom.Vertical.TScrollbar")
    tree_b.configure(yscrollcommand=scrollbar_b.set)
    tree_b.grid(row=0, column=0, sticky="nsew")
    scrollbar_b.grid(row=0, column=1, sticky="ns")



    # ---- Status bar ----
    status_bar_b = tk.Frame(frame_b, bg=STATUS_BG, height=32)
    status_bar_b.pack(fill=tk.X, padx=16, pady=(0, 12))
    status_bar_b.pack_propagate(False)

    lbl_status_b = tk.Label(status_bar_b, text="", font=("Segoe UI", 9), bg=STATUS_BG, fg="#5d6d7e", anchor=tk.W)
    lbl_status_b.pack(fill=tk.X, padx=8, pady=5)

    # ---- Bindings ----
    paste_and_select_b = bind_tree_shortcuts(root, tree_b, masp_col_index=1, lbl_status=lbl_status_b)

    def on_enter_tree_b(event):
        if tree_b.selection():
            do_update_price_b()
        return "break"
    tree_b.bind("<Return>", on_enter_tree_b)

    # ---- Return namespace ----
    return SimpleNamespace(
        entry_so=entry_so,
        tree_b=tree_b,
        lbl_status_b=lbl_status_b,
        paste_and_select_b=paste_and_select_b,
    )
