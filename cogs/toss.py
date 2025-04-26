import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import asyncio

class TossView(View):
    def __init__(self, chooser_id, callback, timeout=30.0):
        super().__init__(timeout=timeout)
        self.chooser_id = chooser_id
        self.callback = callback
        self.choice = None
        
        # Add Heads button
        heads_button = Button(
            style=discord.ButtonStyle.primary,
            label="Heads",
            custom_id="toss_heads"
        )
        heads_button.callback = self.heads_callback
        self.add_item(heads_button)
        
        # Add Tails button
        tails_button = Button(
            style=discord.ButtonStyle.primary,
            label="Tails",
            custom_id="toss_tails"
        )
        tails_button.callback = self.tails_callback
        self.add_item(tails_button)
    
    async def heads_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.chooser_id:
            return await interaction.response.send_message("You weren't selected to call the toss!", ephemeral=True)
        
        self.choice = "heads"
        self.stop()
        await interaction.response.defer()
        await self.callback("heads", interaction.user)
    
    async def tails_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.chooser_id:
            return await interaction.response.send_message("You weren't selected to call the toss!", ephemeral=True)
        
        self.choice = "tails"
        self.stop()
        await interaction.response.defer()
        await self.callback("tails", interaction.user)
    
    async def on_timeout(self):
        if not self.choice:
            await self.callback(None, None)


class TossChoiceView(View):
    def __init__(self, chooser_id, callback, timeout=30.0):
        super().__init__(timeout=timeout)
        self.chooser_id = chooser_id
        self.callback = callback
        self.choice = None
        
        # Add Court button
        court_button = Button(
            style=discord.ButtonStyle.primary,
            label="Court",
            custom_id="toss_court"
        )
        court_button.callback = self.court_callback
        self.add_item(court_button)
        
        # Add Raid button
        raid_button = Button(
            style=discord.ButtonStyle.primary,
            label="Raid",
            custom_id="toss_raid"
        )
        raid_button.callback = self.raid_callback
        self.add_item(raid_button)
    
    async def court_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.chooser_id:
            return await interaction.response.send_message("You're not the toss winner!", ephemeral=True)
        
        self.choice = "court"
        self.stop()
        await interaction.response.defer()
        await self.callback("court", interaction.user)
    
    async def raid_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.chooser_id:
            return await interaction.response.send_message("You're not the toss winner!", ephemeral=True)
        
        self.choice = "raid"
        self.stop()
        await interaction.response.defer()
        await self.callback("raid", interaction.user)
    
    async def on_timeout(self):
        if not self.choice:
            await self.callback("court", None)  # Default to court on timeout


class TossCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="toss")
    async def toss(self, ctx):
        """Conduct a toss between team captains to decide court/raid"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("TossCommand").bot.__dict__["active_matches"]
        
        # Check if a match exists in this channel
        if ctx.channel.id not in active_matches:
            return await ctx.send("No match is going on in this channel.")
            
        match = active_matches[ctx.channel.id]
        
        # Check if toss is already complete
        if match['toss_winner_team'] and match['toss_winner_choice']:
            return await ctx.send("Toss has already been completed for this match.")
        
        # Captains must be set for both teams
        team_a_captain = match['teams']['team_a']['captain']
        team_b_captain = match['teams']['team_b']['captain']
        
        if not team_a_captain or not team_b_captain:
            return await ctx.send("Both teams must have captains set before conducting the toss. Use `.changecaptain` command.")
        
        # Only host or captains can use
        if ctx.author.id != match['host_id'] and ctx.author.id != team_a_captain and ctx.author.id != team_b_captain:
            return await ctx.send("Only the host or team captains can conduct the toss.")
        
        # Reset toss information if we're retrying after timeout
        if match['toss_winner_team'] and not match['toss_winner_choice']:
            match['toss_winner_team'] = None
            match['toss_chooser_user_id'] = None
            match['toss_choice'] = None
            match['toss_result'] = None
        
        # Pick a random captain to call the toss
        captains = [team_a_captain, team_b_captain]
        chooser_id = random.choice(captains)
        chooser_team = "team_a" if chooser_id == team_a_captain else "team_b"
        
        # Store in match data
        match['toss_chooser_user_id'] = chooser_id
        
        # Get chooser user
        chooser_user = self.bot.get_user(chooser_id)
        if not chooser_user:
            return await ctx.send("Error finding captain user. Please try again.")
        
        # Send toss prompt
        embed = discord.Embed(
            title="Kabaddi Match Toss",
            description=f"{chooser_user.mention}, captain of {match['teams'][chooser_team]['name']}, please call the toss!",
            color=discord.Color.gold()
        )
        embed.add_field(name="Time Limit", value="30 seconds to choose")
        
        # Define the toss callback
        async def toss_callback(choice, user):
            if choice is None:
                # Timeout occurred
                await ctx.send("Toss expired! The captain didn't make a call in time. Use `.toss` to try again.")
                return
            
            # Store the choice
            match['toss_choice'] = choice
            
            # Generate random result
            result = random.choice(["heads", "tails"])
            match['toss_result'] = result
            
            # Check if call was correct
            if choice == result:
                # Chooser won
                winner_id = chooser_id
                winner_team = chooser_team
                winner_user = user
            else:
                # Other captain won
                winner_id = team_b_captain if chooser_id == team_a_captain else team_a_captain
                winner_team = "team_b" if chooser_team == "team_a" else "team_a"
                winner_user = self.bot.get_user(winner_id)
            
            # Store winner
            match['toss_winner_team'] = winner_team
            
            # Send toss result
            embed = discord.Embed(
                title="Toss Result",
                description=f"The coin shows **{result.upper()}**!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Winner", 
                value=f"{winner_user.mention}, captain of {match['teams'][winner_team]['name']}"
            )
            embed.add_field(
                name="Next Step", 
                value=f"The winner will now choose Court or Raid"
            )
            await ctx.send(embed=embed)
            
            # Ask winner to choose Court or Raid
            choice_embed = discord.Embed(
                title="Court or Raid?",
                description=f"{winner_user.mention}, please choose Court or Raid!",
                color=discord.Color.blue()
            )
            choice_embed.add_field(name="Time Limit", value="30 seconds (defaults to Court)")
            
            # Define the choice callback
            async def choice_callback(winner_choice, choice_user):
                # Remove buttons from previous message
                choice_view.clear_items()
                await choice_message.edit(view=choice_view)
                
                # Store winner's choice
                match['toss_winner_choice'] = winner_choice
                
                # Send result
                if choice_user:
                    result_msg = f"{winner_user.mention} chose **{winner_choice.upper()}**!"
                else:
                    result_msg = f"Time expired! Defaulting to **COURT** for {winner_user.mention}."
                
                result_embed = discord.Embed(
                    title="Toss Decision",
                    description=result_msg,
                    color=discord.Color.green()
                )
                
                team_a_name = match['teams']['team_a']['name']
                team_b_name = match['teams']['team_b']['name']
                
                if winner_team == "team_a":
                    if winner_choice == "court":
                        result_embed.add_field(name="Result", value=f"{team_a_name} will defend first\n{team_b_name} will raid first")
                    else:  # raid
                        result_embed.add_field(name="Result", value=f"{team_a_name} will raid first\n{team_b_name} will defend first")
                else:  # team_b won
                    if winner_choice == "court":
                        result_embed.add_field(name="Result", value=f"{team_b_name} will defend first\n{team_a_name} will raid first")
                    else:  # raid
                        result_embed.add_field(name="Result", value=f"{team_b_name} will raid first\n{team_a_name} will defend first")
                
                await ctx.send(embed=result_embed)
            
            # Create choice view and send
            choice_view = TossChoiceView(winner_id, choice_callback)
            choice_message = await ctx.send(embed=choice_embed, view=choice_view)
        
        # Create toss view and send
        view = TossView(chooser_id, toss_callback)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(TossCommand(bot))
