import asyncio
import websockets
import json
import time 

# ---------------- 實際讀卡邏輯 (使用從 Java 程式碼獲得的 APDU) ----------------
# APDU 指令來自您提供的 Java 範例程式碼
# 適用於特定版本的台灣健保卡 (通常是使用 AID D158...11 的卡片)

# 選取健保卡應用程式的 APDU 指令
# Java: (byte)0x00, (byte)0xA4, (byte)0x04, (byte)0x00, (byte)0x10, (byte)0xD1, (byte)0x58, (byte)0x00, (byte)0x00, (byte)0x01, (byte)0x00, (byte)0x00, (byte)0x00, (byte)0x00, (byte)0x00, (byte)0x00, (byte)0x00, (byte)0x00, (byte)0x00, (byte)0x11, (byte)0x00
SELECT_NHI_APP_APDU_BYTES = [
    0x00, 0xA4, 0x04, 0x00, 0x10, 0xD1, 0x58, 0x00, 0x00, 0x01, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x11, 
    0x00
]

# 讀取基本資料 Profile 的 APDU 指令
# Java: (byte)0x00, (byte)0xca, (byte)0x11, (byte)0x00, (byte)0x02, (byte)0x00, (byte)0x00
READ_PROFILE_APDU_BYTES = [0x00, 0xCA, 0x11, 0x00, 0x02, 0x00, 0x00]


def parse_profile_data(data_bytes_list): # 傳入的是 byte list
    """
    解析從 ReadProfileAPDU 回傳的資料。
    根據 Java 程式碼中的偏移量和長度。
    """
    profile = {}
    # 將整數列表轉換回 bytes 物件以便解碼
    data_bytes = bytes(data_bytes_list)

    try:
        # 卡號: bytes 0-11 (12 bytes)
        profile["card_number"] = data_bytes[0:12].decode('ascii', errors='replace').strip()
        
        # 姓名: bytes 12-31 (20 bytes), Big5 編碼
        raw_name_bytes = data_bytes[12:32] 
        profile["name"] = raw_name_bytes.decode('big5', errors='replace').strip().replace('\x00', '')
        
        # 身份證字號: bytes 32-41 (10 bytes)
        profile["id_number"] = data_bytes[32:42].decode('ascii', errors='replace').strip()
        
        # 出生年月日: bytes 42-48 (7 bytes) - 格式通常是民國年 YYYMMDD
        dob_roc = data_bytes[42:49].decode('ascii', errors='replace').strip()
        profile["date_of_birth_roc"] = dob_roc
        if len(dob_roc) == 7:
            try:
                year_roc = int(dob_roc[0:3])
                year_ad = year_roc + 1911
                profile["date_of_birth_ad"] = f"{year_ad}{dob_roc[3:5]}{dob_roc[5:7]}"
            except ValueError:
                profile["date_of_birth_ad"] = "格式錯誤"
        
        # 性別: bytes 49 (1 byte) - '1' 為男, '2' 為女
        gender_code = data_bytes[49:50].decode('ascii', errors='replace').strip()
        profile["gender"] = "男" if gender_code == "1" else "女" if gender_code == "2" else "未知"
        
        # 發卡年月日: bytes 50-56 (7 bytes) - 格式通常是民國年 YYYMMDD
        issue_date_roc = data_bytes[50:57].decode('ascii', errors='replace').strip()
        profile["card_issue_date_roc"] = issue_date_roc

        print(f"ℹ️ 解析後的資料: {profile}")
        return profile

    except Exception as e:
        print(f"❌ 解析 Profile 資料時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None


def read_health_card_data():
    """
    嘗試從 IT500U 讀卡機讀取健保卡資料，使用從 Java 範例獲得的 APDU。
    回傳一個包含卡片資料的字典，例如 {"name": "姓名", "chart": "卡號"}
    如果讀卡失敗或沒有卡片，可以回傳 None。
    """
    patient_profile = None
    connection = None 

    try:
        from smartcard.System import readers
        from smartcard.util import toHexString 

        r = readers()
        if not r:
            print("❌ 錯誤：找不到任何 PC/SC 讀卡機。請確認 IT500U 已連接且驅動已安裝。")
            return None

        reader = r[0]
        print(f"ℹ️ 使用讀卡機: {reader}")

        connection = reader.createConnection()
        connection.connect() 

        # 1. 選取健保卡應用程式
        print(f"➡️ 發送選取應用程式 APDU: {toHexString(SELECT_NHI_APP_APDU_BYTES)}")
        # *** 修改點：正確解開 transmit 的回傳值 ***
        data_select, sw1_select, sw2_select = connection.transmit(SELECT_NHI_APP_APDU_BYTES)
        print(f"🔍 選取應用程式回應: SW1={sw1_select:02X}, SW2={sw2_select:02X}, Data={toHexString(data_select)}")

        if not (sw1_select == 0x90 and sw2_select == 0x00):
            if sw1_select == 0x61: 
                get_response_apdu = [0x00, 0xC0, 0x00, 0x00, sw2_select] 
                print(f"➡️ 發送 GET RESPONSE APDU: {toHexString(get_response_apdu)}")
                # *** 修改點：正確解開 transmit 的回傳值 ***
                data_get, sw1_get, sw2_get = connection.transmit(get_response_apdu)
                print(f"🔍 GET RESPONSE 回應: SW1={sw1_get:02X}, SW2={sw2_get:02X}") # data_get 通常是空的或確認訊息
                if not (sw1_get == 0x90 and sw2_get == 0x00):
                    print(f"❌ GET RESPONSE 失敗: SW1={sw1_get:02X}, SW2={sw2_get:02X}")
                    return None 
            else:
                print(f"❌ 選取健保卡應用程式失敗: SW1={sw1_select:02X}, SW2={sw2_select:02X}")
                return None 
        
        print(f"✅ 成功選取健保卡應用程式。")

        # 2. 讀取基本資料 Profile
        print(f"➡️ 發送讀取 Profile APDU: {toHexString(READ_PROFILE_APDU_BYTES)}")
        # *** 修改點：正確解開 transmit 的回傳值 ***
        data_profile_bytes_list, sw1_profile, sw2_profile = connection.transmit(READ_PROFILE_APDU_BYTES)
        # data_profile_bytes_list 是 byte list (整數列表), parse_profile_data 會處理
        print(f"🔍 讀取 Profile 回應: SW1={sw1_profile:02X}, SW2={sw2_profile:02X}, Data Length={len(data_profile_bytes_list)}")

        if sw1_profile == 0x90 and sw2_profile == 0x00:
            if data_profile_bytes_list and len(data_profile_bytes_list) >= 57: 
                patient_profile_parsed = parse_profile_data(data_profile_bytes_list) 
                if patient_profile_parsed and "name" in patient_profile_parsed:
                    patient_profile = {
                        "name": patient_profile_parsed.get("name"),
                        "chart": patient_profile_parsed.get("card_number"), 
                        "id_number": patient_profile_parsed.get("id_number"),
                        "date_of_birth_roc": patient_profile_parsed.get("date_of_birth_roc"),
                        "gender": patient_profile_parsed.get("gender")
                    }
                    print(f"✅ 成功讀取並解析 Profile 資料。")
                else:
                    print(f"❌ 解析 Profile 資料後無效或缺少姓名。")
            else:
                print(f"❌ 讀取 Profile 成功，但回傳資料長度不足 (需要至少57 bytes，得到 {len(data_profile_bytes_list)})。")
        else:
            print(f"❌ 讀取 Profile 失敗: SW1={sw1_profile:02X}, SW2={sw2_profile:02X}")

        return patient_profile


    except ImportError:
        print("❌ 錯誤：`pyscard` 函式庫未安裝。請執行 `pip install pyscard`。")
        return None
    except Exception as e:
        print(f"❌ 讀卡時發生未預期錯誤: {e}")
        import traceback
        traceback.print_exc() 
        return None
    finally:
        if connection:
            try:
                connection.disconnect()
                print("ℹ️ 已與卡片斷開連接。")
            except Exception as de:
                print(f"⚠️ 斷開卡片連接時發生錯誤: {de}")

# ---------------- 佔位符結束 -------------------------------------

async def card_reader_handler(websocket, path=None): 
    print("📡 健保讀卡 WebSocket 伺服器啟動，等待網頁端連線...")
    
    remote_addr_info = websocket.remote_address
    client_ip = remote_addr_info[0] if remote_addr_info and len(remote_addr_info) > 0 else "未知IP"
    client_port = remote_addr_info[1] if remote_addr_info and len(remote_addr_info) > 1 else "未知Port"
    
    print(f"🔗 新的網頁端連線來自: {client_ip}:{client_port}")
    if path: 
        print(f"ℹ️ 連線路徑: {path}")

    last_sent_data_json = None 

    try:
        while True:
            card_data = read_health_card_data() 

            if card_data and "name" in card_data and card_data["name"] is not None: 
                current_data_json = json.dumps(card_data)
                if current_data_json != last_sent_data_json: 
                    await websocket.send(current_data_json)
                    print(f"✅ 已傳送卡片資料: {card_data.get('name', '未知姓名')}, 病歷號/卡號: {card_data.get('chart', '未知')}")
                    last_sent_data_json = current_data_json
                else:
                    print(f"ℹ️ 卡片資料未變更 ({card_data.get('name')})，未重複發送。")
            else:
                print("ℹ️ 未讀取到有效卡片資料 (姓名欄位為空或讀取失敗)，未發送訊息。")
                pass
            await asyncio.sleep(3) 

    except websockets.exceptions.ConnectionClosedOK:
        print(f"💔 網頁端連線 ({client_ip}:{client_port}) 已正常關閉。")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"💥 網頁端連線 ({client_ip}:{client_port}) 異常關閉: {e}")
    except Exception as e:
        print(f"❌ 伺服器發生錯誤: {e}")
    finally:
        print(f"🔌 結束與 {client_ip}:{client_port} 的通訊。")


async def main():
    async with websockets.serve(card_reader_handler, "localhost", 8765):
        print("🔌 (修正 transmit 回傳處理) WebSocket 伺服器執行中：ws://localhost:8765")
        print("ℹ️ 將嘗試使用從 Java 範例獲得的 APDU 指令讀取健保卡。")
        await asyncio.Future()  

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 伺服器已由使用者手動停止。")

