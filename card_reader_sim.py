import asyncio
import websockets
import json
import time

async def handler(websocket, path):
    print("📡 模擬讀卡伺服器啟動，等待網頁端連線...")
    while True:
        data = {"name": "王小明"}
        await websocket.send(json.dumps(data))
        print(f"✅ 已傳送：{data['name']}")
        await asyncio.sleep(8)

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("🔌 WebSocket 伺服器執行中：ws://localhost:8765")
        await asyncio.Future()  # 永不結束

if __name__ == "__main__":
    asyncio.run(main())