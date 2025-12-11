import asyncio


def test_abbyy_client_stub():
    # basic smoke test for the client stub
    from app.services.abbyy_client import AbbyyClient

    client = AbbyyClient("https://example.com")

    async def run():
        res = await client.submit_document("/tmp/file.pdf")
        assert res.get("status") == "submitted"

    asyncio.get_event_loop().run_until_complete(run())

