import discord
from discord.ext import commands

class SwapCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="swap")
    async def swap(self, ctx, user1: discord.Member = None, user2: discord.Member = None):
        """Swap two players between teams (host only)"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("SwapCommand").bot.__dict__["active_matches"]
        
        # Check if a match exists in this channel
        if ctx.channel.id not in active_matches:
            return await ctx.send("No match is going on in this channel.")
            
        match = active_matches[ctx.channel.id]
        
        # Check if user is the host
        if ctx.author.id != match['host_id']:
            return await ctx.send("Only the host can swap players.")
            
        # Check if match has already started
        if match['has_started']:
            return await ctx.send("You can't swap players after the match has started.")
            
        # Check if both users were mentioned
        if not user1 or not user2:
            return await ctx.send("Usage: `.swap @user1 @user2`")
            
        # Check if both users are in the match
        if user1.id not in match['players'] or user2.id not in match['players']:
            return await ctx.send("Both users must be in the match.")
            
        # Check which teams the users are in
        user1_in_team_a = user1.id in match['teams']['team_a']['players']
        user2_in_team_a = user2.id in match['teams']['team_a']['players']
        
        # Users must be in different teams
        if (user1_in_team_a and user2_in_team_a) or (not user1_in_team_a and not user2_in_team_a):
            return await ctx.send("Users must be in different teams to swap.")
            
        # Perform the swap
        if user1_in_team_a:
            # user1 is in Team A, user2 is in Team B
            match['teams']['team_a']['players'].remove(user1.id)
            match['teams']['team_b']['players'].append(user1.id)
            
            match['teams']['team_b']['players'].remove(user2.id)
            match['teams']['team_a']['players'].append(user2.id)
            
            # Update captains if needed
            if match['teams']['team_a']['captain'] == user1.id:
                match['teams']['team_a']['captain'] = None
            if match['teams']['team_b']['captain'] == user2.id:
                match['teams']['team_b']['captain'] = None
        else:
            # user1 is in Team B, user2 is in Team A
            match['teams']['team_b']['players'].remove(user1.id)
            match['teams']['team_a']['players'].append(user1.id)
            
            match['teams']['team_a']['players'].remove(user2.id)
            match['teams']['team_b']['players'].append(user2.id)
            
            # Update captains if needed
            if match['teams']['team_b']['captain'] == user1.id:
                match['teams']['team_b']['captain'] = None
            if match['teams']['team_a']['captain'] == user2.id:
                match['teams']['team_a']['captain'] = None
                
        # Confirm swap
        await ctx.send(f"Swapped {user1.mention} and {user2.mention} between teams!")

async def setup(bot):
    await bot.add_cog(SwapCommand(bot))
