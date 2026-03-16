import configparser
import win32com.client
import warnings
import time
from pywinauto import application
import os
import sys
#Bỏ cảnh báo
warnings.filterwarnings("ignore", category=UserWarning, message="32-bit application should be automated using 32-bit Python")

def ReadConfig():
    try:
        config = configparser.ConfigParser()
        if getattr(sys, 'frozen', False):
            BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(BASE_DIR, 'config.ini')
        config.read(config_path)
        env = config.get('ENV', 'current').upper() 
        sap_path = config.get(env, 'sap_path')
        name_connection =config.get(env,'name_connection')
        client = config.get(env,'client')
        user = config.get(env,'user')
        password = config.get(env,'password')
        language = config.get(env,'language')    
        return {'sap_path': sap_path,'name_connection': name_connection,'client': client,'user': user,'password': password,'language': language}
    except (configparser.Error, FileNotFoundError) as e:
        print("Lỗi khi đọc file config.ini:", e)
        return None

def ConnectSAP():
    config = ReadConfig()
    if config is None:
        print("Lỗi khi đọc file config.ini")
        return None
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass

    try:
        SapGuiAuto = win32com.client.GetObject('SAPGUI')
        application_sap = SapGuiAuto.GetScriptingEngine
        if application_sap.Children.Count > 0:
            connection_sap = application_sap.Children(0)
            # Tìm session đang có để dùng luôn
            if connection_sap.Children.Count > 0:
                session = connection_sap.Children(0)
                try:
                    _ = session.Info.SystemName
                    print(f"Dùng session SAP hiện có: {session.Info.SystemName} / {session.Info.Client}")
                    return session
                except Exception:
                    print("Session hiện có đã timeout.")
    except Exception:
        pass

    # Không có session nào → khởi động SAP Logon và login
    print("Không có session SAP nào đang mở. Thực hiện mở ứng dụng SAP...")
    try:
        app = application.Application().start(config["sap_path"])
        time.sleep(1)
        SapGuiAuto = win32com.client.GetObject('SAPGUI')
        application_sap = SapGuiAuto.GetScriptingEngine
        connection = application_sap.OpenConnection(config['name_connection'], True)
        time.sleep(1)
        session = connection.Children(0)
        session.FindById("wnd[0]").Maximize()
        session.findById("wnd[0]/usr/txtRSYST-MANDT").text = config['client']
        session.findById("wnd[0]/usr/txtRSYST-BNAME").text = config['user']
        session.findById("wnd[0]/usr/pwdRSYST-BCODE").text = config['password']
        session.findById("wnd[0]/usr/txtRSYST-LANGU").text = config['language']
        session.FindById("wnd[0]").SendVKey(0)
        time.sleep(1)
        try:
            if session.FindById("wnd[1]").text == "License Information for Multiple Logon":
                session.findById("wnd[1]/usr/radMULTI_LOGON_OPT2").Select()
                session.FindById("wnd[1]").SendVKey(0)
        except Exception:
            pass
        return session
    except Exception as e:
        print(f"Không kết nối được SAP: {e}")
        return None