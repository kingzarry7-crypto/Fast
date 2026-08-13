def format_market(
    data,
    title
):

    message = (

        f"👑 **{title}**\n\n"

        f"📊 Market: **{data['symbol']}**\n"
        f"⏱ Timeframe: **{data['timeframe']}**\n\n"

        f"🎯 Signal: **{data['signal']}**\n"
        f"📈 Trend: **{data['trend']}**\n\n"

        f"💰 Entry: `${data['price']:,.5f}`\n"
    )

    if data["signal"] == "BUY":

        message += (
            f"\n🛑 Stop Loss: "
            f"`${data['stop_loss']:,.5f}`\n"

            f"🎯 Take Profit: "
            f"`${data['take_profit']:,.5f}`\n"

            f"⚖️ Risk/Reward: **1:2**\n"
        )

    elif data["signal"] == "SELL":

        message += (
            f"\n🛑 Stop Loss: "
            f"`${data['stop_loss']:,.5f}`\n"

            f"🎯 Take Profit: "
            f"`${data['take_profit']:,.5f}`\n"

            f"⚖️ Risk/Reward: **1:2**\n"
        )

    else:

        message += (
            "\n⏸️ No trade setup.\n"
            "Wait for a stronger signal.\n"
        )

    message += (

        f"\n🟢 Support: "
        f"`${data['support']:,.5f}`\n"

        f"🔴 Resistance: "
        f"`${data['resistance']:,.5f}`\n\n"

        f"EMA 9: `${data['ema9']:,.5f}`\n"
        f"EMA 21: `${data['ema21']:,.5f}`\n"
        f"EMA 50: `${data['ema50']:,.5f}`\n"
        f"RSI: **{data['rsi']:.2f}**\n\n"

        "⚠️ Algorithmic analysis only. "
        "No guaranteed profit."
    )

    return message
