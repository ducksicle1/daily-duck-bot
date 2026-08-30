# ============================================================
# /DUCK
# ============================================================

@bot.tree.command(
    name="duck",
    description="Immediately summon a random duck!"
)
async def duck(interaction: discord.Interaction):

    server = get_server(
        interaction.guild.id
    )

    if not server or not server[1]:

        await interaction.response.send_message(
            "🦆 I don't have a duck channel configured yet!\n"
            "Use `/setup` first.",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    success = await post_duck(
        interaction.guild.id
    )

    if success:
        # Remove the temporary interaction response
        await interaction.delete_original_response()

    else:
        await interaction.edit_original_response(
            content=(
                "I couldn't post the duck. "
                "Make sure I can view and send messages "
                "in the configured channel."
            )
        )


# ============================================================
# /SETTINGS
# ============================================================

@bot.tree.command(
    name="settings",
    description="View the current DailyDuck settings."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def settings(
    interaction: discord.Interaction
):

    server = get_server(
        interaction.guild.id
    )

    if not server or not server[1]:

        await interaction.response.send_message(
            "🦆 DailyDuck hasn't been configured yet.\n"
            "Use `/setup` to get started.",
            ephemeral=True
        )

        return

    channel = bot.get_channel(server[1])

    channel_text = (
        channel.mention
        if channel
        else "Unknown channel"
    )

    enabled = server[5]

    if not enabled:

        schedule = "Disabled"

    elif server[2] == "interval":

        minutes = server[3]

        if minutes % 60 == 0:
            schedule = (
                f"Every {minutes // 60} hour(s)"
            )
        else:
            schedule = (
                f"Every {minutes} minute(s)"
            )

    elif server[2] == "daily":

        schedule = (
            f"Daily at {server[4]}"
        )

    else:

        schedule = "Not configured"

    embed = discord.Embed(
        title="🦆 DailyDuck Settings",
        color=DUCK_COLOR
    )

    embed.add_field(
        name="Posting Channel",
        value=channel_text,
        inline=False
    )

    embed.add_field(
        name="Autopost",
        value=schedule,
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )
