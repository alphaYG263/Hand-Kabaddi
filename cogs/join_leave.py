import discord
from discord.ext import commands

class JoinLeave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="join", aliases=["j"])
    async def join(self, ctx):
        """Join an existing Kabaddi match in the current channel"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("JoinLeave").bot.__dict__["active_matches"]
        user_match_map = self.bot.get_cog("JoinLeave").bot.__dict__["user_match_map"]
        
        # Check if a match exists in this channel
        if ctx.channel.id not in active_matches:
            return await ctx.send("No match is going on in this channel.")
            
        match = active_matches[ctx.channel.id]
        
        # Check if user is already in a match
        if ctx.author.id in user_match_map:
            if user_match_map[ctx.author.id] == ctx.channel.id:
                return await ctx.send("You're already in this match.")
            else:
                channel = self.bot.get_channel(user_match_map[ctx.author.id])
                channel_mention = f"<#{user_match_map[ctx.author.id]}>"
                return await ctx.send(f"You're already in a match in {channel_mention}.")
        
        # Check if match is full (6 players)
        if len(match['players']) >= 6:
            return await ctx.send("Match is full (6/6 players).")
            
        # Add user to the appropriate team (team with fewer players, or Team B if equal)
        team_a_count = len(match['teams']['team_a']['players'])
        team_b_count = len(match['teams']['team_b']['players'])
        
        if team_a_count <= team_b_count:
            team = 'team_a'
            team_name = match['teams']['team_a']['name']
        else:
            team = 'team_b'
            team_name = match['teams']['team_b']['name']
            
        # Update match data
        match['teams'][team]['players'].append(ctx.author.id)
        match['players'].append(ctx.author.id)
        match['individual_scores'][ctx.author.id] = {"raids": 0, "tackles": 0}
        user_match_map[ctx.author.id] = ctx.channel.id
        
        # Confirm join
        await ctx.send(f"{ctx.author.mention} has joined {team_name}!")
        
    @commands.command(name="leave", aliases=["l"])
    async def leave(self, ctx):
        """Leave a Kabaddi match you've joined"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("JoinLeave").bot.__dict__["active_matches"]
        user_match_map = self.bot.get_cog("JoinLeave").bot.__dict__["user_match_map"]
        
        # Check if a match exists in this channel
        if ctx.channel.id not in active_matches:
            return await ctx.send("No match is going on in this channel.")
            
        match = active_matches[ctx.channel.id]
        
        # Check if user is in the match
        if ctx.author.id not in match['players']:
            return await ctx.send("You haven't joined this match.")
            
        # Check if match has already started
        if match['has_started']:
            return await ctx.send("You can't leave after the match has started.")
            
        # Check if user is the host (cannot leave their own match)
        if ctx.author.id == match['host_id']:
            return await ctx.send("As the host, you cannot leave the match. Use `.yeet` to cancel it instead.")
        
        # Remove user from the match
        match['players'].remove(ctx.author.id)
        
        # Remove from team
        for team in ['team_a', 'team_b']:
            if ctx.author.id in match['teams'][team]['players']:
                match['teams'][team]['players'].remove(ctx.author.id)
                # If user was captain, remove captain
                if match['teams'][team]['captain'] == ctx.author.id:
                    match['teams'][team]['captain'] = None
                    
        # Remove from individual scores
        if ctx.author.id in match['individual_scores']:
            del match['individual_scores'][ctx.author.id]
            
        # Remove from user_match_map
        del user_match_map[ctx.author.id]
        
        # Confirm leave
        await ctx.send(f"{ctx.author.mention} has left the match.")

async def setup(bot):
    await bot.add_cog(JoinLeave(bot))
