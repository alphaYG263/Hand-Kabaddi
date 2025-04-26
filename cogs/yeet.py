import discord
from discord.ext import commands

class YeetCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="yeet", aliases=["yt"])
    async def yeet(self, ctx):
        """Cancel/delete your match (host only)"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("YeetCommand").bot.__dict__["active_matches"]
        user_match_map = self.bot.get_cog("YeetCommand").bot.__dict__["user_match_map"]
        
        # Check if a match exists in this channel
        if ctx.channel.id not in active_matches:
            return await ctx.send("No match is going on in this channel.")
            
        match = active_matches[ctx.channel.id]
        
        # Check if user is the host
        if ctx.author.id != match['host_id']:
            return await ctx.send("Only the host can delete the match.")
        
        # Store info for confirmation message
        match_mode = match['mode']
        player_count = len(match['players'])
        
        # Remove all users from user_match_map
        for player_id in match['players']:
            if player_id in user_match_map:
                del user_match_map[player_id]
        
        # Remove match from active_matches
        del active_matches[ctx.channel.id]
        
        # Confirm deletion
        await ctx.send(f"Match deleted! ({match_mode.capitalize()} mode with {player_count} players)")

async def setup(bot):
    await bot.add_cog(YeetCommand(bot))
