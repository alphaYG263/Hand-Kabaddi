import discord
from discord.ext import commands

class ChangeCaptain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="changecaptain", aliases=["cc"])
    async def change_captain(self, ctx, team=None, user: discord.Member = None):
        """Set team captain (host only)"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("ChangeCaptain").bot.__dict__["active_matches"]
        
        # Check if a match exists in this channel
        if ctx.channel.id not in active_matches:
            return await ctx.send("No match is going on in this channel.")
            
        match = active_matches[ctx.channel.id]
        
        # Check if user is the host
        if ctx.author.id != match['host_id']:
            return await ctx.send("Only the host can change team captains.")
            
        # Check if the command was used correctly
        if not team or not user:
            return await ctx.send("Usage: `.changecaptain teama/teamb @user`")
            
        # Validate team
        team = team.lower()
        if team not in ["teama", "teamb"]:
            return await ctx.send("Invalid team. Use 'teama' or 'teamb'.")
            
        # Convert team name to match key
        team_key = "team_a" if team == "teama" else "team_b"
        
        # Check if user is in the team
        if user.id not in match['teams'][team_key]['players']:
            return await ctx.send(f"{user.mention} is not in {match['teams'][team_key]['name']}.")
            
        # Update captain
        match['teams'][team_key]['captain'] = user.id
        
        # Confirm change
        await ctx.send(f"{user.mention} is now the captain of {match['teams'][team_key]['name']}!")

async def setup(bot):
    await bot.add_cog(ChangeCaptain(bot))
