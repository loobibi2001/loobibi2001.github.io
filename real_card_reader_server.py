import asyncio
import websockets
import json
import time # 保留用於潛在的延遲或超時

# ---------------- 實際讀卡邏輯的佔位符 ----------------
# 您需要根據您的健保讀卡機 SDK 來實現這個函數
# This is a placeholder. You'll need to implement this using your card reader's SDK.
# It might involve libraries like 'pyscard' if your reader is PC/SC compatible,
# but the SDK provided by the manufacturer is the definitive source.

def read_health_card_data():
    """
    模擬從健保卡讀取資料。
    在真實的應用中，這裡應該包含與讀卡機硬體互動的程式碼。
    回傳一個包含卡片資料的字典，例如 {"name": "從卡片讀到的名字", "id_number": "A123456789", ...}
    如果讀卡失敗或沒有卡片，可以回傳 None 或引發一個自訂錯誤。
    """
    # --- 實際讀卡邏輯開始 (範例概念) ---
    # 1. 初始化讀卡機 (Initialize card reader)
    # 2. 檢查是否有卡片 (Check for card presence)
    # 3. 連接到卡片 (Connect to the card)
    # 4. 發送 APDU 指令以讀取所需資料 (Send APDU commands to read data, e.g., name)
    #    - 這部分非常依賴讀卡機型號和健保卡標準
    # 5. 解析回傳的資料 (Parse the returned data)
    # 6. 關閉與卡片的連接 (Disconnect from the card)

    # 舉例：如果使用 pyscard (需先 `pip install pyscard`) 且讀卡機相容
    # from smartcard.System import readers
    # from smartcard.util import toHexString
    # try:
    #     r = readers()
    #     if not r:
    #         print("錯誤：找不到任何讀卡機。")
    #         return None
    #     connection = r[0].createConnection()
    #     connection.connect()
    #     # 實際的 APDU 指令會更複雜，且需要針對健保卡
    #     # SELECT_AID_COMMAND = [0x00, 0xA4, 0x04, 0x00, 0x10, 0xD1, 0x58, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x11, 0x00] # 假設的健保卡 AID
    #     # data, sw1, sw2 = connection.transmit(SELECT_AID_COMMAND)
    #     # if (sw1, sw2) == (0x90, 0x00):
    #     #     # 接著傳送讀取姓名的指令...
    #     #     # READ_NAME_COMMAND = [...]
    #     #     # name_data, nsw1, nsw2 = connection.transmit(READ_NAME_COMMAND)
    #     #     # if (nsw1, nsw2) == (0x90, 0x00):
    #     #     #     decoded_name = name_data.decode('utf-8') # 或其他編碼
    #     #     #     return {"name": decoded_name} # 假設只回傳姓名
    #     #     pass # 繼續處理
    #     # print(f"卡片狀態: {sw1:02X} {sw2:02X}")
    # except Exception as e:
    #     print(f"讀卡時發生錯誤: {e}")
    #     return None
    # --- 實際讀卡邏輯結束 ---

    # 如果尚未實作真實讀卡，最好明確告知或返回 None
    print("警告：read_health_card_data() 函數尚未實作真實讀卡邏輯。請替換此部分。")
    # 為了讓伺服器在沒有真實讀卡邏輯時也能運行並給前端一個反應，可以暫時返回一個固定的模擬資料
    # time.sleep(1) # 模擬讀卡延遲
    # return {"name": "模擬真實姓名", "id_number": "A000000000"} # 包含一個模擬的姓名
    return None # 或者直接返回 None，讓前端處理沒有資料的情況
# ---------------- 佔位符結束 -------------------------------------

async def card_reader_handler(websocket, path):
    print("📡 健保讀卡 WebSocket 伺服器啟動，等待網頁端連線...")
    client_ip, client_port = websocket.remote_address
    print(f"🔗 新的網頁端連線來自: {client_ip}:{client_port}")

    last_sent_data_json = None # 用於避免重複發送相同的資料

    try:
        while True:
            # 在真實應用中，您可能不希望無限迴圈地主動讀卡，
            # 而是根據事件（例如，偵測到卡片插入）或客戶端請求來觸發。
            # 但為了簡化，我們先保留一個輪詢的結構。

            card_data = read_health_card_data() # 呼叫讀卡函數

            if card_data and "name" in card_data: # 確保讀取到資料且包含 'name'
                current_data_json = json.dumps(card_data)
                # 只有當資料更新時才發送
                if current_data_json != last_sent_data_json:
                    await websocket.send(current_data_json)
                    print(f"✅ 已傳送卡片資料: {card_data.get('name', '未知姓名')}")
                    last_sent_data_json = current_data_json
                else:
                    # print("ℹ️ 卡片資料未變更，未發送。") # 如果不想顯示太多訊息可以註解掉
                    pass
            else:
                # print("ℹ️ 未讀取到有效卡片資料或姓名。") # 如果不想顯示太多訊息可以註解掉
                # 如果沒有讀到卡，可以考慮發送一個空訊息或特定狀態給前端
                # 例如: await websocket.send(json.dumps({"status": "no_card_detected"}))
                pass

            # 調整輪詢間隔，真實應用中可能不需要這麼頻繁，
            # 或者應該由其他事件觸發。
            await asyncio.sleep(3)  # 每 3 秒嘗試讀取一次

    except websockets.exceptions.ConnectionClosedOK:
        print(f"💔 網頁端連線 ({client_ip}:{client_port}) 已正常關閉。")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"💥 網頁端連線 ({client_ip}:{client_port}) 異常關閉: {e}")
    except Exception as e:
        print(f"❌ 伺服器發生錯誤: {e}")
    finally:
        print(f"🔌 結束與 {client_ip}:{client_port} 的通訊。")


async def main():
    # 設定 websockets.serve 的 log_level 可以看到更多底層訊息
    # import logging
    # logger = logging.getLogger('websockets')
    # logger.setLevel(logging.INFO)
    # logger.addHandler(logging.StreamHandler())

    async with websockets.serve(card_reader_handler, "localhost", 8765):
        print("🔌 (真實版基礎) WebSocket 伺服器執行中：ws://localhost:8765")
        print("請確保已在 read_health_card_data() 函數中實作真實的讀卡邏輯。")
        await asyncio.Future()  # 保持伺服器運行

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 伺服器已由使用者手動停止。")

