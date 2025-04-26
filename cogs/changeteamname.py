import discord
from discord.ext import commands

class ChangeTeamName(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="changeteamname", aliases=["ct"])
    async def change_team_name(self, ctx, team=None, *, name=None):
        """Change a team's name (host only)"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("ChangeTeamName").bot.__dict__["active_matches"]
        
        # Check if a match exists in this channel
        if ctx.channel.id not in active_matches:
            return await ctx.send("No match is going on in this channel.")
            
        match = active_matches[ctx.channel.id]
        
        # Check if user is the host
        if ctx.author.id != match['host_id']:
            return await ctx.send("Only the host can change team names.")
            
        # Check if the command was used correctly
        if not team or not name:
            return await ctx.send("Usage: `.changeteamname teama/teamb New Team Name`")
            
        # Validate team
        team = team.lower()
        if team not in ["teama", "teamb"]:
            return await ctx.send("Invalid team. Use 'teama' or 'teamb'.")
            
        # Convert team name to match key
        team_key = "team_a" if team == "teama" else "team_b"
        other_team_key = "team_b" if team == "teama" else "team_a"
        
        # Check if name is the same as the other team
        if name == match['teams'][other_team_key]['name']:
            return await ctx.send(f"Team name must be different from {match['teams'][other_team_key]['name']}.")
        
        # Store old name for confirmation message
        old_name = match['teams'][team_key]['name']
        
        # Update team name
        match['teams'][team_key]['name'] = name
        
        # Confirm change
        await ctx.send(f"Team name changed from **{old_name}** to **{name}**!")

async def setup(bot):
    await bot.add_cog(ChangeTeamName(bot))
