import discord
from discord.ext import commands
from datetime import datetime

class CreateMatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="createclassic", aliases=["cc"])
    async def create_classic(self, ctx):
        """Create a classic 3v3 Kabaddi match"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("CreateMatch").bot.__dict__["active_matches"]
        user_match_map = self.bot.get_cog("CreateMatch").bot.__dict__["user_match_map"]
        
        # Check if match already exists in the channel
        if ctx.channel.id in active_matches:
            return await ctx.send("A match is already running in this channel.")
        
        # Check if user has already created a match elsewhere
        if ctx.author.id in user_match_map:
            channel = self.bot.get_channel(user_match_map[ctx.author.id])
            channel_mention = f"<#{user_match_map[ctx.author.id]}>"
            return await ctx.send(f"You already have an active match in {channel_mention}.")
        
        # Create new match
        match_data = {
            "host_id": ctx.author.id,
            "mode": "classic",
            "time_created": datetime.now(),
            "teams": {
                "team_a": {
                    "name": "Team A",
                    "players": [ctx.author.id],
                    "captain": None
                },
                "team_b": {
                    "name": "Team B", 
                    "players": [],
                    "captain": None
                }
            },
            "players": [ctx.author.id],
            "has_started": False,
            "toss_winner_team": None,
            "toss_chooser_user_id": None,
            "toss_choice": None,
            "toss_result": None,
            "toss_winner_choice": None,
            "scorecard_message_id": None,
            "current_raid_number": 0,
            "individual_scores": {}
        }
        
        # Initialize individual score for host
        match_data["individual_scores"][ctx.author.id] = {"raids": 0, "tackles": 0}
        
        # Store match data in memory
        active_matches[ctx.channel.id] = match_data
        user_match_map[ctx.author.id] = ctx.channel.id
        
        # Send confirmation
        embed = discord.Embed(
            title="Classic Kabaddi Match Created!",
            description=f"Match created by {ctx.author.mention}. Join with `.join` command.",
            color=discord.Color.green()
        )
        embed.add_field(name="Mode", value="Classic (3v3)")
        embed.add_field(name="Timeout", value="Match will be auto-deleted after 300 seconds if not started.")
        embed.add_field(name="Players", value=f"1/6 (Host: {ctx.author.mention} in Team A)")
        await ctx.send(embed=embed)
    
    @commands.command(name="createelite", aliases=["ce"])
    async def create_elite(self, ctx):
        """Create an elite 3v3 Kabaddi match"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("CreateMatch").bot.__dict__["active_matches"]
        user_match_map = self.bot.get_cog("CreateMatch").bot.__dict__["user_match_map"]
        
        # Check if match already exists in the channel
        if ctx.channel.id in active_matches:
            return await ctx.send("A match is already running in this channel.")
        
        # Check if user has already created a match elsewhere
        if ctx.author.id in user_match_map:
            channel = self.bot.get_channel(user_match_map[ctx.author.id])
            channel_mention = f"<#{user_match_map[ctx.author.id]}>"
            return await ctx.send(f"You already have an active match in {channel_mention}.")
        
        # Create new match
        match_data = {
            "host_id": ctx.author.id,
            "mode": "elite",
            "time_created": datetime.now(),
            "teams": {
                "team_a": {
                    "name": "Team A",
                    "players": [ctx.author.id],
                    "captain": None
                },
                "team_b": {
                    "name": "Team B", 
                    "players": [],
                    "captain": None
                }
            },
            "players": [ctx.author.id],
            "has_started": False,
            "toss_winner_team": None,
            "toss_chooser_user_id": None,
            "toss_choice": None,
            "toss_result": None,
            "toss_winner_choice": None,
            "scorecard_message_id": None,
            "current_raid_number": 0,
            "individual_scores": {}
        }
        
        # Initialize individual score for host
        match_data["individual_scores"][ctx.author.id] = {"raids": 0, "tackles": 0}
        
        # Store match data in memory
        active_matches[ctx.channel.id] = match_data
        user_match_map[ctx.author.id] = ctx.channel.id
        
        # Send confirmation
        embed = discord.Embed(
            title="Elite Kabaddi Match Created!",
            description=f"Match created by {ctx.author.mention}. Join with `.join` command.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Mode", value="Elite (3v3)")
        embed.add_field(name="Timeout", value="Match will be auto-deleted after 300 seconds if not started.")
        embed.add_field(name="Players", value=f"1/6 (Host: {ctx.author.mention} in Team A)")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CreateMatch(bot))
