import asyncio


def test_polling_service_runs_once():
    from app.services.polling_service import PollingService

    s = PollingService(poll_interval=0.01)

    async def run_one():
        # run for a short amount of time then stop
        async def handler(_):
            pass

        task = asyncio.create_task(s.start(handler))
        await asyncio.sleep(0.02)
        s.stop()
        await asyncio.sleep(0.01)
        task.cancel()

    asyncio.get_event_loop().run_until_complete(run_one())

