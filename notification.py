from database import get_subscriptions_by_currency, delete_subscription

async def check_alerts(currency_id, current_price, bot, pool):
    subscriptions = await get_subscriptions_by_currency(currency_id, pool)

    for sub in subscriptions:
        if current_price <= sub["target_price"]:
            try:
                await bot.send_message(
                    sub["telegram_id"],
                    f"Цена упала!\n"
                    f"{sub['currency_symbol']} сейчас: {current_price}$\n"
                    f"Ваш порог: {sub['target_price']}$"
                )

                await delete_subscription(sub["id"], pool)
                
            except Exception as e:
                print(f"Не удалось отправить уведомление пользователю {sub['telegram_id']}: {e}")