import discord
from discord.ext import commands

class PlayerList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="playerlist", aliases=["pl"])
    async def player_list(self, ctx):
        """Display the current player list and teams"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("PlayerList").bot.__dict__["active_matches"]
        
        # Check if a match exists in this channel
        if ctx.channel.id not in active_matches:
            return await ctx.send("No match is going on in this channel.")
            
        match = active_matches[ctx.channel.id]
        
        # Create embed to show player list
        embed = discord.Embed(
            title="Kabaddi Match Player List",
            description=f"Mode: {match['mode'].capitalize()}",
            color=discord.Color.blue()
        )
        
        # Add Team A field
        team_a = match['teams']['team_a']
        team_a_name = team_a['name']
        
        # If captain exists, include in title
        if team_a['captain']:
            captain_user = self.bot.get_user(team_a['captain'])
            captain_name = captain_user.mention if captain_user else "Unknown"
            team_a_field_name = f"{team_a_name} - Captain: {captain_name}"
        else:
            team_a_field_name = team_a_name
            
        # Create list of players
        team_a_players = []
        for player_id in team_a['players']:
            player = self.bot.get_user(player_id)
            if player:
                # Mark the host
                if player_id == match['host_id']:
                    team_a_players.append(f"{player.mention} (Host)")
                else:
                    team_a_players.append(player.mention)
                    
        team_a_value = "\n".join(team_a_players) if team_a_players else "No players"
        embed.add_field(name=team_a_field_name, value=team_a_value, inline=False)
        
        # Add Team B field
        team_b = match['teams']['team_b']
        team_b_name = team_b['name']
        
        # If captain exists, include in title
        if team_b['captain']:
            captain_user = self.bot.get_user(team_b['captain'])
            captain_name = captain_user.mention if captain_user else "Unknown"
            team_b_field_name = f"{team_b_name} - Captain: {captain_name}"
        else:
            team_b_field_name = team_b_name
            
        # Create list of players
        team_b_players = []
        for player_id in team_b['players']:
            player = self.bot.get_user(player_id)
            if player:
                team_b_players.append(player.mention)
                    
        team_b_value = "\n".join(team_b_players) if team_b_players else "No players"
        embed.add_field(name=team_b_field_name, value=team_b_value, inline=False)
        
        # Add status field
        status = "Not Started" if not match['has_started'] else "In Progress"
        embed.add_field(name="Status", value=status, inline=False)
        
        # Add player count
        embed.set_footer(text=f"Players: {len(match['players'])}/6")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PlayerList(bot))
