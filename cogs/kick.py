import discord
from discord.ext import commands

class KickCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="kick", aliases=["k"])
    async def kick(self, ctx, user: discord.Member = None):
        """Kick a player from your match (host only)"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("KickCommand").bot.__dict__["active_matches"]
        user_match_map = self.bot.get_cog("KickCommand").bot.__dict__["user_match_map"]
        
        # Check if a match exists in this channel
        if ctx.channel.id not in active_matches:
            return await ctx.send("No match is going on in this channel.")
            
        match = active_matches[ctx.channel.id]
        
        # Check if user is the host
        if ctx.author.id != match['host_id']:
            return await ctx.send("Only the host can kick players.")
            
        # Check if match has already started
        if match['has_started']:
            return await ctx.send("You can't kick players after the match has started.")
            
        # Check if a user was mentioned
        if not user:
            return await ctx.send("Please mention a user to kick.")
            
        # Check if mentioned user is in the match
        if user.id not in match['players']:
            return await ctx.send(f"{user.mention} is not in this match.")
            
        # Can't kick the host
        if user.id == match['host_id']:
            return await ctx.send("You can't kick yourself as the host. Use `.yeet` to cancel the match instead.")
            
        # Remove user from the match
        match['players'].remove(user.id)
        
        # Remove from team
        for team in ['team_a', 'team_b']:
            if user.id in match['teams'][team]['players']:
                match['teams'][team]['players'].remove(user.id)
                # If user was captain, remove captain
                if match['teams'][team]['captain'] == user.id:
                    match['teams'][team]['captain'] = None
                    
        # Remove from individual scores
        if user.id in match['individual_scores']:
            del match['individual_scores'][user.id]
            
        # Remove from user_match_map
        del user_match_map[user.id]
        
        # Confirm kick
        await ctx.send(f"Kicked {user.mention} from match.")

async def setup(bot):
    await bot.add_cog(KickCommand(bot))
