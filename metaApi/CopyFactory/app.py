import asyncio
import os

from dotenv import load_dotenv
from metaapi_cloud_sdk import CopyFactory, MetaApi

load_dotenv()

token = os.getenv("TOKEN")
provider_account_id = os.getenv("PROVIDER_ACCOUNT_ID")
subscriber_account_ids = os.getenv("SUBSCRIBER_ACCOUNT_IDS", "").split(",")


async def configure_copyfactory():
    api = MetaApi(token)
    copyfactory = CopyFactory(token)

    try:
        provider_metaapi_account = await api.metatrader_account_api.get_account(
            provider_account_id
        )
        if (
            provider_metaapi_account is None
            or provider_metaapi_account.copy_factory_roles is None
            or "PROVIDER" not in provider_metaapi_account.copy_factory_roles
        ):
            raise Exception(
                "Please specify PROVIDER copyFactoryRoles value in your MetaApi "
                "account in order to use it in CopyFactory API"
            )

        configuration_api = copyfactory.configuration_api
        strategies = (
            await configuration_api.get_strategies_with_infinite_scroll_pagination()
        )
        strategy = next(
            (s for s in strategies if s["accountId"] == provider_metaapi_account.id),
            None,
        )

        if strategy:
            strategy_id = strategy["_id"]
        else:
            strategy_id = (await configuration_api.generate_strategy_id())["id"]

        # Create a strategy being copied
        await configuration_api.update_strategy(
            strategy_id,
            {
                "name": "Test strategy",
                "description": "Some useful description about your strategy",
                "accountId": provider_metaapi_account.id,
                "copyStopLoss": True,
                "copyTakeProfit": True,
                "tradeSizeScaling": {"mode": "none"},
            },
        )

        # Create subscribers
        for subscriber_id in subscriber_account_ids:
            subscriber_id = subscriber_id.strip()
            if not subscriber_id:
                continue  # Skip empty values

            subscriber_metaapi_account = await api.metatrader_account_api.get_account(
                subscriber_id
            )
            if (
                subscriber_metaapi_account is None
                or subscriber_metaapi_account.copy_factory_roles is None
                or "SUBSCRIBER" not in subscriber_metaapi_account.copy_factory_roles
            ):
                print(f"Skipping {subscriber_id}: Not a valid subscriber.")
                continue

            await configuration_api.update_subscriber(
                subscriber_metaapi_account.id,
                {
                    "name": f"Subscriber {subscriber_metaapi_account.id}",
                    "subscriptions": [
                        {
                            "strategyId": strategy_id,
                            "multiplier": 1.56,
                            "copyStopLoss": True,
                            "copyTakeProfit": True,
                        }
                    ],
                },
            )
            print(
                f"Successfully subscribed {subscriber_metaapi_account.id} to strategy {strategy_id}"
            )

    except Exception as err:
        print(api.format_error(err))


asyncio.run(configure_copyfactory())
