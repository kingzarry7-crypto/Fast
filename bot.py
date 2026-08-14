# ==========================================================
# /STATS (Analytics)
# ==========================================================

@client.tree.command(
    name="stats",
    description="Check King Zarry AI user analytics"
)
async def stats(
    interaction: discord.Interaction
):
    await interaction.response.defer(ephemeral=True)

    try:
        stats_data = memory.get_user_stats()
        total_guilds = len(client.guilds) if client.guilds else 1

        embed = discord.Embed(
            title="👑 King Zarry AI Statistics",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📊 Servers / Guilds", 
            value=str(total_guilds), 
            inline=True
        )
        embed.add_field(
            name="👥 Total Unique Users (DB)", 
            value=str(stats_data.get("total_users", 0)), 
            inline=True
        )
        embed.add_field(
            name="⚡ Active Users (Last 24h)", 
            value=str(stats_data.get("active_24h", 0)), 
            inline=True
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    except Exception as e:
        print("❌ /stats ERROR:", repr(e))
        await interaction.followup.send(
            f"❌ Stats error:\n`{str(e)[:1200]}`",
            ephemeral=True
        )
