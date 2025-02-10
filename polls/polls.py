import discord
from discord.ext import commands
import asyncio
from core import checks
from core.checks import PermissionLevel
import datetime

class PollModal(discord.ui.Modal, title="Create a Poll"):
    """Modal form to create a poll."""
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot  
        self.poll_data = {}

        self.add_item(discord.ui.TextInput(label="Poll Question", placeholder="Enter your poll question...", max_length=200))
        self.add_item(discord.ui.TextInput(label="Options (comma-separated)", placeholder="Option1, Option2, Option3... upto 10", max_length=500))
        self.add_item(discord.ui.TextInput(label="Duration (in minutes)", placeholder="Enter poll duration...", max_length=4))
        self.add_item(discord.ui.TextInput(label="Role Restriction (Role ID or 'none')", placeholder="ID1, ID2, ID3... or 'none'", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        """Handles poll creation after the user submits the form."""
        await interaction.response.defer(ephemeral=True)
        self.poll_data["question"] = self.children[0].value
        options = self.children[1].value.split(",")
        self.poll_data["options"] = [opt.strip() for opt in options if opt.strip()][:10]  # Max 10 options
        self.poll_data["duration"] = int(self.children[2].value) * 60  
        self.poll_data["role_ids"] = None if self.children[3].value.lower() == "none" else [int(role.strip()) for role in self.children[3].value.split(",")]

        if len(self.poll_data["options"]) < 2:
            return await interaction.response.send_message("❌ You need at least **2 options** for a poll.", ephemeral=True)

        embed = discord.Embed(title=self.poll_data["question"], color=0x7289da)
        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        description = ""
        for i, option in enumerate(self.poll_data["options"]):
            description += f"{reactions[i]} {option}\n"

        embed.description = description
        embed.set_footer(text="Poll ends:")
        embed.timestamp = discord.utils.utcnow() + datetime.timedelta(seconds=self.poll_data["duration"])

        poll_message = await interaction.channel.send(embed=embed)
        for i in range(len(self.poll_data["options"])):
            await poll_message.add_reaction(reactions[i])
        await interaction.message.delete()
        await interaction.followup.send("✅ **Poll Created Successfully!**", ephemeral=True)
        await asyncio.sleep(self.poll_data["duration"])
        await self.announce_results(interaction.channel, poll_message, embed)

    async def announce_results(self, channel, poll_message, embed):
        """Counts reactions and announces the poll results."""
        msg = await channel.fetch_message(poll_message.id)

        valid_reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][:len(self.poll_data["options"])]

        results = {emoji: 0 for emoji in valid_reactions}


        for reaction in msg.reactions:
            if reaction.emoji in results:
                users = [user async for user in reaction.users()]
                valid_votes = 0  

                for user in users:
                    if user.bot:
                        continue  

                    if self.poll_data["role_ids"]:  
                        member = channel.guild.get_member(user.id)
                        if member and any(role.id in self.poll_data["role_ids"] for role in member.roles):
                            valid_votes += 1
                    else:
                        valid_votes += 1  

            results[reaction.emoji] = valid_votes

        result_text = ""


        for emoji, count in results.items():
            result_text += f"{emoji}: {count} votes\n"

        max_votes = max(results.values())
        if not results or max_votes is 0:
            result_text = ":x: No votes were cast."

        if results and max_votes is not 0:
            max_votes = max(results.values())  
            winners = [emoji for emoji, count in results.items() if count == max_votes]

            if len(winners) == 1:
                result_text += f"\n🏆 **Winner:** {winners[0]} ({max_votes} votes)"
            else:
                result_text += f"\n🏆 **Winners:** {', '.join(winners)} ({max_votes} votes)"

        return await channel.send(embed=discord.Embed(title="Poll Results", description=result_text, color=0x7289da))


class Polls(commands.Cog):
    """Create Polls in your server"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    @commands.command(name="poll")
    async def poll(self, ctx):
        """Sends a button to open the modal for poll creation."""
        button = discord.ui.Button(label="Create Poll", style=discord.ButtonStyle.primary, custom_id="poll_create_button")
        view = discord.ui.View()
        view.add_item(button)
        
        await ctx.send(embed=discord.Embed(title="", description="📊 **Click on the button below to create a poll in this channel.**", color=0x7289da) ,view=view)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handles the button interaction and opens the modal."""
        if interaction.data["custom_id"] == "poll_create_button":
            await interaction.response.send_modal(PollModal(self.bot))  


async def setup(bot):
    """Cog setup function."""
    await bot.add_cog(Polls(bot))
