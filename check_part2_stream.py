import asyncio
import json
import websockets

async def main():
    uri = "ws://localhost:8000/api/v1/ws/stream"

    print("=" * 70)
    print("ARGUS PART 2 WEBSOCKET TEST")
    print("=" * 70)
    print(f"Connecting to: {uri}")

    try:
        async with websockets.connect(uri, open_timeout=10) as ws:
            print("CONNECTED TO PART 2")
            print("Waiting for events...")

            for i in range(10):
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)

                print(f"\n===== EVENT {i + 1} =====")
                print(json.dumps(data, indent=2))

    except asyncio.TimeoutError:
        print("\nTIMEOUT: No WebSocket event received within 10 seconds.")
    except Exception as e:
        print(f"\nWEBSOCKET ERROR: {type(e).__name__}: {e}")

asyncio.run(main())
