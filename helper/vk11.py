from datetime import datetime, date, timedelta

def updateMaterial(session, code_customer, materials, vkorg="2001"):
    """
    materials: list of dict [{"masp": ..., "gia": ...}, ...]
    vkorg: mã chi nhánh (Sales Org)
    """
    try:
        today = date.today()
        today_str = today.strftime("%d.%m.%Y")
        end_str = (today + timedelta(days=1)).strftime("%d.%m.%Y")

        session.FindById("wnd[0]/tbar[0]/okcd").Text = "/nvk11"
        session.FindById("wnd[0]").SendVKey(0)
        session.FindById("wnd[0]/usr/ctxtRV13A-KSCHL").Text = 'ZPR6'
        session.FindById("wnd[0]").SendVKey(0)
        session.FindById("wnd[0]").SendVKey(0)
        session.FindById("wnd[0]/usr/ctxtKOMG-VKORG").Text = vkorg
        session.FindById("wnd[0]/usr/ctxtKOMG-VTWEG").Text = "11"
        session.FindById("wnd[0]/usr/ctxtKOMG-KUNNR").Text = code_customer
        session.FindById("wnd[0]").SendVKey(0)
        message = get_status_message(session)
        if message["type"] in ["E", "W"]:
            return [{"masp": m["masp"], "status": "error", "msg": f"Không tìm thấy khách hàng {code_customer} trong SAP"} for m in materials]

        results = []
        for idx, mat in enumerate(materials):
            code_material = mat["masp"]
            cost = mat["gia"]
            try:
                # Nhập mã vật liệu
                session.FindById(f"wnd[0]/usr/tblSAPMV13ATCTRL_FAST_ENTRY/ctxtKOMG-MATNR[0,{idx}]").Text = code_material
                # Nhập giá
                session.FindById(f"wnd[0]/usr/tblSAPMV13ATCTRL_FAST_ENTRY/txtKONP-KBETR[2,{idx}]").Text = str(cost)

                # Nhập ngày bắt đầu
                session.FindById(f"wnd[0]/usr/tblSAPMV13ATCTRL_FAST_ENTRY/ctxtRV13A-DATAB[8,{idx}]").Text = today_str
                # Nhập ngày kết thúc
                session.FindById(f"wnd[0]/usr/tblSAPMV13ATCTRL_FAST_ENTRY/ctxtRV13A-DATBI[9,{idx}]").Text = end_str
                results.append({"masp": code_material, "status": "ok", "msg": f"{code_material} - giá {cost} ({today_str} - {end_str})"})
            except Exception as e:
                results.append({"masp": code_material, "status": "error", "msg": str(e)})

        # Nhấn Enter để validate tất cả
        session.FindById("wnd[0]").SendVKey(0)

        # Kiểm tra lỗi sau khi validate
        message = get_status_message(session)
        if message["type"] in ["E", "W"]:
            # Đánh dấu lỗi chung
            for r in results:
                if r["status"] == "ok":
                    r["status"] = "warning"
                    r["msg"] += f" | SAP: {message['text']}"

        # session.FindById("wnd[0]/tbar[0]/btn[11]").Press()

        # message = get_status_message(session)
        # if message["type"] in ["E", "W"]:
        #     # Đánh dấu lỗi chung
        #     for r in results:
        #         if r["status"] == "ok":
        #             r["status"] = "warning"
        #             r["msg"] += f" | SAP: {message['text']}"

        # Thoát VK11 về màn hình chính để lần sau ConnectSAP không bị kẹt
        # try:
        #     session.FindById("wnd[0]/tbar[0]/okcd").Text = "/n"
        #     session.FindById("wnd[0]").SendVKey(0)
        #     # Nếu có popup hỏi "Data will be lost" → nhấn Yes
        #     try:
        #         session.FindById("wnd[1]/usr/btnSPOP-OPTION1").Press()
        #     except Exception:
        #         pass
        # except Exception:
        #     pass

        return results
    except Exception as e:
        # Cố thoát transaction nếu lỗi
        try:
            session.FindById("wnd[0]/tbar[0]/okcd").Text = "/n"
            session.FindById("wnd[0]").SendVKey(0)
            try:
                session.FindById("wnd[1]/usr/btnSPOP-OPTION1").Press()
            except Exception:
                pass
        except Exception:
            pass
        return [{"masp": m["masp"], "status": "error", "msg": str(e)} for m in materials]
    
def updateMaterialV2(session, code_customer, materials, sales_org):
    try:
        today = date.today()
        today_str = today.strftime("%d.%m.%Y")
        end_str = (today + timedelta(days=1)).strftime("%d.%m.%Y")

        session.FindById("wnd[0]/tbar[0]/okcd").Text = "/nvk11"
        session.FindById("wnd[0]").SendVKey(0)
        session.FindById("wnd[0]/usr/ctxtRV13A-KSCHL").Text = 'ZPR6'
        session.FindById("wnd[0]").SendVKey(0)
        session.FindById("wnd[1]/usr/sub:SAPLV14A:0100/radRV130-SELKZ[1,0]").Select()
        session.FindById("wnd[0]").SendVKey(0)
        if sales_org == "2001":
            session.FindById('wnd[0]/usr/ctxtKOMG-AUART_SD').Text = 'YOR6'
        else:
            session.FindById('wnd[0]/usr/ctxtKOMG-AUART_SD').Text = 'YCN6'
        session.FindById("wnd[0]/usr/ctxtKOMG-KUNNR").Text = code_customer
        session.FindById("wnd[0]").SendVKey(0)
        message = get_status_message(session)
        if message["type"] in ["E", "W"]:
            return [{"masp": m["masp"], "status": "error", "msg": f"Không tìm thấy khách hàng {code_customer} trong SAP"} for m in materials]

        results = []
        table_id = "wnd[0]/usr/tblSAPMV13ATCTRL_FAST_ENTRY"
        table = session.findById(table_id)
        visible_rows = table.VisibleRowCount 
        # print(materials)
        for idx, mat in enumerate(materials):
            code_material = mat["masp"]
            cost = mat["gia"]
            try:
                # Nhập mã vật liệu
                visible_index = idx % visible_rows
                if idx > 0 and visible_index == 0:
                    session.FindById("wnd[0]").SendVKey(0)  # Enter
                    table = session.findById(table_id)  # Refresh table reference
                    visible_rows = table.VisibleRowCount
                    total_rows = table.RowCount
                    table.verticalScrollbar.position = total_rows - visible_rows
                session.FindById(f"{table_id}/ctxtKOMG-MATNR[0,{visible_index}]").Text = code_material
                print(f"Đang xử lý {code_material} (index {idx}, visible index {visible_index})")
                # Nhập giá
                session.FindById(f"{table_id}/txtKONP-KBETR[4,{visible_index}]").Text = cost

                session.FindById(f"{table_id}/ctxtKONP-KONWA[5,{visible_index}]").Text = "VND"
                # Nhập ngày bắt đầu
                session.FindById(f"{table_id}/ctxtRV13A-DATAB[10,{visible_index}]").Text = today_str
                # Nhập ngày kết thúc
                session.FindById(f"{table_id}/ctxtRV13A-DATBI[11,{visible_index}]").Text = end_str
                results.append({"masp": code_material, "status": "ok", "msg": f"{code_material} - giá {cost} ({today_str} - {end_str})"})
            except Exception as e:
                results.append({"masp": code_material, "status": "error", "msg": str(e)})

        # Nhấn Enter để validate tất cả
        session.FindById("wnd[0]").SendVKey(0)

        # Kiểm tra lỗi sau khi validate
        message = get_status_message(session)
        if message["type"] in ["E", "W"]:
            # Đánh dấu lỗi chung
            for r in results:
                if r["status"] == "ok":
                    r["status"] = "warning"
                    r["msg"] += f" | SAP: {message['text']}"

        # session.FindById("wnd[0]/tbar[0]/btn[11]").Press()
        # message = get_status_message(session)
        # if message["type"] in ["E", "W"]:
        #             # Đánh dấu lỗi chung
        #             for r in results:
        #                 if r["status"] == "ok":
        #                     r["status"] = "warning"
        #                     r["msg"] += f" | SAP: {message['text']}"

        # print(f"Kết quả cập nhật SAP: {results}")
        return results
    except Exception as e:
        return [{"masp": m["masp"], "status": "error", "msg": str(e)} for m in materials]

def updatematerialgr(session,customer_gr, materials):
    try:
        today = date.today()
        today_str = today.strftime("%d.%m.%Y")

        session.FindById("wnd[0]/tbar[0]/okcd").Text = "/nvk11"
        session.FindById("wnd[0]").SendVKey(0)
        session.FindById("wnd[0]/usr/ctxtRV13A-KSCHL").Text = 'ZPR6'
        session.FindById("wnd[0]").SendVKey(0)
        session.FindById("wnd[1]/usr/sub:SAPLV14A:0100/radRV130-SELKZ[6,0]").Select()
        session.FindById("wnd[0]").SendVKey(0)
        session.FindById('wnd[0]/usr/ctxtKOMG-KDGRP').Text = customer_gr
        session.FindById("wnd[0]").SendVKey(0)
        results = []
        table_id = "wnd[0]/usr/tblSAPMV13ATCTRL_FAST_ENTRY"
        table = session.findById(table_id)
        visible_rows = table.VisibleRowCount
        for idx, mat in enumerate(materials):
            code_material = mat["masp"]
            cost = mat["gia"]
            try:
                # Nhập mã vật liệu
                visible_index = idx % visible_rows
                if idx > 0 and visible_index == 0:
                    session.FindById("wnd[0]").SendVKey(0)  # Enter
                    table = session.findById(table_id)  # Refresh table reference
                    visible_rows = table.VisibleRowCount
                    total_rows = table.RowCount
                    table.verticalScrollbar.position = total_rows - visible_rows
                session.FindById(f"{table_id}/ctxtKOMG-MATNR[0,{visible_index}]").Text = code_material
                # Nhập giá
                session.FindById(f"{table_id}/txtKONP-KBETR[4,{visible_index}]").Text = cost

                session.FindById(f"{table_id}/ctxtKONP-KONWA[5,{visible_index}]").Text = "VND"
                # Nhập ngày bắt đầu
                session.FindById(f"{table_id}/ctxtRV13A-DATAB[10,{visible_index}]").Text = today_str
                results.append({"masp": code_material, "status": "ok", "msg": f"{code_material} - giá {cost} ({today_str})"})
            except Exception as e:
                print(f"Lỗi khi xử lý {code_material}: {e}")
                results.append({"masp": code_material, "status": "error", "msg": str(e)})

        session.FindById("wnd[0]").SendVKey(0)
        message = get_status_message(session)
        if message["type"] in ["E", "W"]:
            # Đánh dấu lỗi chung
            for r in results:
                if r["status"] == "ok":
                    r["status"] = "warning"
                    r["msg"] += f" | SAP: {message['text']}"
        return results
    except Exception as e:
        return [{"masp": m["masp"], "status": "error", "msg": str(e)} for m in materials]   

def get_status_message(session):
    try:
        status_bar = session.FindById("wnd[0]/sbar")
        return {
            "type": status_bar.MessageType,  # "E", "W", "S", "I"
            "text": status_bar.Text.strip()
        }
    except Exception:
        return {
            "type": "UNKNOWN",
            "text": ""
        }