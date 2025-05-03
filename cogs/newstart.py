import discord
from discord.ext import commands
from discord.ui import Select, Button, View
import random
import asyncio
from datetime import datetime, timedelta
import motor.motor_asyncio

class StartMatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_raids = {}

    @commands.command(name="simulate")
    async def simulate(self, ctx):
        """Simulate a 7v7 custom match with predefined players (admin only)"""
        # Check if user is authorized
        if ctx.author.id != 823178354118885388:
            return await ctx.send("Only the bot owner can use this command.")
    
        # Check if a match already exists in this channel
        if ctx.channel.id in self.bot.active_matches:
            return await ctx.send("A match is already in progress in this channel.")

        # Create the match data structure
        match_data = {
            "host_id": 823178354118885388,  # You as host
            "mode": "custom",
            "time_created": datetime.now(),
            "teams": {
                "team_a": {
                    "name": "Team A",
                    "players": [
                        743318400180158544,  # raider
                        1102092875807870986,  # raider
                        823178354118885388,  # raider (host/captain)
                        782812619408408616,  # allrounder
                        861320825592348702,  # defender
                        759713678013890560,  # defender
                        871958885290893322   # raider
                    ],
                    "captain": 823178354118885388,
                    "raiders": [
                        743318400180158544,
                        1102092875807870986,
                        823178354118885388,
                        871958885290893322
                    ],
                    "defenders": [
                        861320825592348702,
                        759713678013890560
                    ],
                    "allrounders": [
                        782812619408408616
                    ]
                },
                "team_b": {
                    "name": "Team B",
                    "players": [
                        976718339026083911,  # raider
                        760480907256791081,  # raider
                        774147065592676373,  # raider
                        743633216384008242,  # allrounder (captain)
                        1365636725031960693,  # defender
                        819514581088862208,  # defender
                        771985432812322828   # raider
                    ],
                    "captain": 743633216384008242,
                    "raiders": [
                        976718339026083911,
                        760480907256791081,
                        774147065592676373,
                        771985432812322828
                    ],
                    "defenders": [
                        1365636725031960693,
                        819514581088862208
                    ],
                    "allrounders": [
                        743633216384008242
                    ]
                }
            },
            "players": [
                # Team A players
                743318400180158544,
                1102092875807870986,
                823178354118885388,
                782812619408408616,
                861320825592348702,
                759713678013890560,
                871958885290893322,
                # Team B players
                976718339026083911,
                760480907256791081,
                774147065592676373,
                743633216384008242,
                1365636725031960693,
                819514581088862208,
                771985432812322828
            ],
            "players_role": {
                # Team A roles - making sure these are strings
                "743318400180158544": "raider",
                "1102092875807870986": "raider",
                "823178354118885388": "raider",
                "782812619408408616": "allrounder",
                "861320825592348702": "defender",
                "759713678013890560": "defender",
                "871958885290893322": "raider",
                # Team B roles - making sure these are strings
                "976718339026083911": "raider",
                "760480907256791081": "raider",
                "774147065592676373": "raider",
                "743633216384008242": "allrounder",
                "1365636725031960693": "defender",
                "819514581088862208": "defender",
                "771985432812322828": "raider"
            },
            "has_started": False,
            "toss_winner_team": "team_a",
            "toss_winner_choice": "raid",
            "current_raid_number": 1,
            "individual_scores": {}
        }

        # Initialize individual scores (using string keys)
        for player_id in match_data['players']:
            player_id_str = str(player_id)
            match_data['individual_scores'][player_id_str] = {
                'raids': 0,
                'tackles': 0
            }

        # Store the match in active_matches
        self.bot.active_matches[ctx.channel.id] = match_data

        # Update user_match_map
        for player_id in match_data['players']:
            self.bot.user_match_map[player_id] = ctx.channel.id

        # Mark match as started
        match_data['has_started'] = True
        match_data['start_time'] = datetime.now()
        match_data['scores'] = {
            "team_a": 0,
            "team_b": 0
        }
        match_data['raiding_team'] = "team_a"  # Team A chose to raid first

        # Send starting message
        embed = discord.Embed(
            title="Custom Kabaddi Match Simulation Started!",
            description="The simulated match has begun!",
            color=discord.Color.green()
        )

        embed.add_field(
            name="First Raiders", 
            value=f"Team A will raid first\nTeam B will defend first"
        )

        embed.add_field(
            name="Total Raids", 
            value="20 (10 per team)"
        )

        await ctx.send(embed=embed)

        # Create and send initial scorecard
        scorecard_embed = await self.create_scorecard(match_data)
        scorecard_msg = await ctx.send(embed=scorecard_embed)
        match_data['scorecard_message_id'] = scorecard_msg.id

        # Begin raid sequence
        await self.start_raid_sequence(ctx, match_data)
    
    @commands.command(name="start", aliases=["s"])
    async def start(self, ctx):
        """Start a match that has been set up (host only)"""
        # Get reference to global data structures
        active_matches = self.bot.active_matches
        user_match_map = self.bot.user_match_map
        
        # Check if a match exists in this channel
        if ctx.channel.id not in active_matches:
            return await ctx.send("No match is going on in this channel.")
            
        match = active_matches[ctx.channel.id]
        
        # Check if user is the host
        if ctx.author.id != match['host_id']:
            return await ctx.send("Only the host can start the match.")
            
        # Check if match has already started
        if match['has_started']:
            return await ctx.send("Match has already started.")

        # Check for correct player count based on mode
        expected_players = 14 if match['mode'] == 'custom' else 6
        if len(match['players']) != expected_players:
            return await ctx.send(f"Need exactly {expected_players} players to start (currently {len(match['players'])}/{expected_players}).")

        # Check team player distribution
        if match['mode'] == 'custom':
            for team_key in ['team_a', 'team_b']:
                team = match['teams'][team_key]
                if len(team['players']) != 7:
                    return await ctx.send(f"{team['name']} must have exactly 7 players.")
                if len(team.get('raiders', [])) > 4:
                    return await ctx.send(f"{team['name']} cannot have more than 4 raiders.")
                if len(team.get('defenders', [])) < 3:
                    return await ctx.send(f"{team['name']} must have at least 3 defenders.")
                if len(team.get('allrounders', [])) > 1:
                    return await ctx.send(f"{team['name']} cannot have more than 1 allrounder.")
        else:
            if len(match['teams']['team_a']['players']) != 3 or len(match['teams']['team_b']['players']) != 3:
                return await ctx.send("Both teams must have exactly 3 players each.")

        
        # Check if toss is complete
        if not match['toss_winner_team'] or not match['toss_winner_choice']:
            return await ctx.send("Toss must be completed before starting the match. Use `.toss` command.")
            
        # Check if both teams have captains
        if not match['teams']['team_a']['captain'] or not match['teams']['team_b']['captain']:
            return await ctx.send("Both teams must have captains. Use `.changecaptain` command.")
            
        # Mark match as started
        match['has_started'] = True
        match['start_time'] = datetime.now()
        match['current_raid_number'] = 1
        match['scores'] = {
            "team_a": 0,
            "team_b": 0
        }
        
        # Initialize individual scores
        match['individual_scores'] = {}
        for player_id in match['players']:
            match['individual_scores'][player_id] = {
                'raids': 0,
                'tackles': 0
            }
        
        # Determine which team raids first based on toss result
        winner_team = match['toss_winner_team']
        winner_choice = match['toss_winner_choice']
        
        if winner_team == "team_a":
            if winner_choice == "raid":
                match['raiding_team'] = "team_a"
            else:  # court
                match['raiding_team'] = "team_b"
        else:  # team_b won toss
            if winner_choice == "raid":
                match['raiding_team'] = "team_b"
            else:  # court
                match['raiding_team'] = "team_a"
        
        # Send starting message
        embed = discord.Embed(
            title=f"{match['mode'].capitalize()} Kabaddi Match Started!",
            description="The match has begun! Get ready for some Kabaddi action!",
            color=discord.Color.green()
        )
        
        team_a_name = match['teams']['team_a']['name']
        team_b_name = match['teams']['team_b']['name']
        
        # Add raiding info to embed
        raiding_team_name = match['teams'][match['raiding_team']]['name']
        defending_team_name = match['teams']['team_b' if match['raiding_team'] == 'team_a' else 'team_a']['name']
        
        embed.add_field(
            name="First Raiders", 
            value=f"{raiding_team_name} will raid first\n{defending_team_name} will defend first"
        )
        
        embed.add_field(
            name="Total Raids", 
            value="20 (10 per team)"
        )
        
        # Send initial message
        await ctx.send(embed=embed)
        
        # Create and send initial scorecard
        scorecard_embed = await self.create_scorecard(match)
        scorecard_msg = await ctx.send(embed=scorecard_embed)
        match['scorecard_message_id'] = scorecard_msg.id
        
        # Begin raid sequence
        await self.start_raid_sequence(ctx, match)
    
    async def create_scorecard(self, match):
        """Create scorecard embed for the match"""
        team_a_name = match['teams']['team_a']['name']
        team_b_name = match['teams']['team_b']['name']
        
        team_a_score = match.get('scores', {}).get('team_a', 0)
        team_b_score = match.get('scores', {}).get('team_b', 0)
        
        embed = discord.Embed(
            title="Live Scorecard",
            description=f"Raid {match['current_raid_number']}/10",
            color=discord.Color.blue()
        )
        
        if match.get('current_raid_number', 1) < 10:
            embed.set_thumbnail(url="https://raw.githubusercontent.com/alphaYG263/Hand-Kabaddi/main/images/i0tlRDQSRhmCrW_Did4OyQ.webp")
        
        embed.add_field(
            name=team_a_name,
            value=f"**{team_a_score}** points",
            inline=True
        )
        
        embed.add_field(
            name=team_b_name,
            value=f"**{team_b_score}** points",
            inline=True
        )
        
        # Add current status
        current_raiders = "Preparing..."
        if match.get('current_raider_id'):
            raider = self.bot.get_user(match['current_raider_id'])
            raider_name = raider.name if raider else "Unknown"
            raiding_team = match['teams'][match['raiding_team']]['name']
            current_raiders = f"{raider_name} raiding for {raiding_team}"
        
        embed.add_field(
            name="Current Raid",
            value=current_raiders,
            inline=False
        )
        
        # Add recent raid results if available
        if match.get('last_raid_result'):
            embed.add_field(
                name="Last Raid Result",
                value=match['last_raid_result'],
                inline=False
            )
        
        return embed
    
    async def update_scorecard(self, ctx, match):
        """Update the scorecard message with current scores"""
        try:
            scorecard_msg = await ctx.channel.fetch_message(match['scorecard_message_id'])
            updated_embed = await self.create_scorecard(match)
            await scorecard_msg.edit(embed=updated_embed)
        except discord.NotFound:
            # If message was deleted, create a new one
            scorecard_embed = await self.create_scorecard(match)
            scorecard_msg = await ctx.send(embed=scorecard_embed)
            match['scorecard_message_id'] = scorecard_msg.id
    
    async def start_raid_sequence(self, ctx, match):
        """Start the raid sequence for the current raid"""
        # Check if match has ended
        if match['current_raid_number'] > 10:
            return await self.end_match(ctx, match)
        
        # Get current raiding and defending teams
        raiding_team_key = match['raiding_team']
        defending_team_key = "team_b" if raiding_team_key == "team_a" else "team_a"
        
        raiding_team = match['teams'][raiding_team_key]
        defending_team = match['teams'][defending_team_key]
        
        # Get captain of raiding team to select raider
        captain_id = raiding_team['captain']
        captain = self.bot.get_user(captain_id)
        
        # Create message to ask captain to select raider
        embed = discord.Embed(
            title=f"Raid #{match['current_raid_number']}",
            description=f"Captain of {raiding_team['name']}, please select a raider!",
            color=discord.Color.gold()
        )
        
        # Create dropdown to select raider
        class RaiderSelect(View):
            def __init__(self, raiding_team, bot, timeout_callback):
                super().__init__(timeout=10.0)
                self.raider_selected = None
                self.bot = bot
                self.timeout_callback = timeout_callback

                select = Select(
                    placeholder='Choose a raider...',
                    min_values=1,
                    max_values=1
                )

                # Track valid raiders found
                valid_raiders_found = False

                for player_id in raiding_team['players']:
                    # Convert player_id to string when accessing players_role dictionary
                    player_id_str = str(player_id)
                    role = match.get('players_role', {}).get(player_id_str)
            
                    print(f"Checking player_id: {player_id} ({player_id_str})")
                    print(f"Role fetched: {role}")
            
                    # Check if player role allows raiding
                    if match['mode'] == 'custom' and role not in ['raider', 'allrounder']:
                        print(f"Skipping player {player_id} with role {role} - not a valid raider")
                        continue
            
                    player = bot.get_user(player_id)
                    if player:
                        select.add_option(
                            label=player.name,
                            value=str(player_id),
                            description=f'Select {player.name} as raider'
                        )
                        valid_raiders_found = True
                        print(f"Added player {player.name} as valid raider option")

                # If no valid raiders found, add a message option
                if not valid_raiders_found:
                    # Debug output to help diagnose
                    print(f"No valid raiders found. Player roles: {match.get('players_role')}")
                    print(f"Team players: {raiding_team['players']}")
        
                    # Add a default option to prevent API error
                    select.add_option(
                        label="Error CRS",
                        value="none",
                        description="Please report CRS"
                    )

                select.callback = self.raider_selected_callback
                self.add_item(select)
            
            async def raider_selected_callback(self, interaction):
                # Check if the person selecting is the captain
                if interaction.user.id != captain_id:
                    return await interaction.response.send_message("Only the team captain can select raiders!", ephemeral=True)
    
                # Get selected raider ID
                selected_value = interaction.data['values'][0]
    
                # Handle the "no valid raiders" case
                if selected_value == "none":
                    await interaction.response.send_message("No valid raiders found in your team. Please check team composition.", ephemeral=True)
                    await ctx.send("Error: No players with raider or allrounder role in the raiding team!")
                    self.stop()
                    return
        
                self.raider_selected = int(selected_value)
    
                # Stop the view
                self.stop()
                await interaction.response.defer()
            
            async def on_timeout(self):
                await self.timeout_callback()
        
        async def captain_timeout():
            # Captain didn't select in time, pick random raider
            raider_id = random.choice(raiding_team['players'])
            raider = self.bot.get_user(raider_id)
            await ctx.send(f"⏱️ Captain didn't select in time. Randomly selected {raider.mention} as raider!")
            await self.handle_raider_selection(ctx, match, raider_id)
        
        # Send the selection message
        raider_view = RaiderSelect(raiding_team, self.bot, captain_timeout)
        selection_msg = await ctx.send(embed=embed, view=raider_view)
        
        # Add captain ping message
        await ctx.send(f"{captain.mention}")
        
        # Wait for selection
        await raider_view.wait()
        
        if raider_view.raider_selected:
            # Captain selected a raider
            raider_id = raider_view.raider_selected
            await self.handle_raider_selection(ctx, match, raider_id)
    
    async def handle_raider_selection(self, ctx, match, raider_id):
        """Handle raider selection and continue with raid"""
        # Get raider user
        raider = self.bot.get_user(raider_id)
        if not raider:
            # Fallback in case user was not found
            await ctx.send("Error finding raider. Picking random raider...")
            raiding_team = match['teams'][match['raiding_team']]
            raider_id = random.choice(raiding_team['players'])
            raider = self.bot.get_user(raider_id)
        
        # Validate raider role in custom mode
        if match['mode'] == 'custom':
            role = match.get('players_role', {}).get(str(raider.id))
            if role not in ['raider', 'allrounder']:
                await ctx.send(f"Error: {raider.name} is not assigned as a raider or allrounder!")
                return
        
        # Store current raider in match data
        match['current_raider_id'] = raider_id
        
        # Get defending team key
        defending_team_key = "team_b" if match['raiding_team'] == "team_a" else "team_a"
        
        # Announce raider
        await ctx.send(f"🏃‍♂️ **{raider.name}** is raiding for {match['teams'][match['raiding_team']]['name']}!")
        
        # Update scorecard
        await self.update_scorecard(ctx, match)
        
        # Get player numbers from both raider and defenders
        raider_number, defender_numbers = await self.get_player_numbers(ctx, match, raider, defending_team_key)
        
        # Process raid result
        await self.process_raid_result(ctx, match, raider_id, raider_number, defender_numbers)
    
    async def get_player_numbers(self, ctx, match, raider, defending_team_key):
            """Get player numbers from both raider and defenders"""
            defenders = []
            for player_id in match['teams'][defending_team_key]['players']:
                player_id_str = str(player_id)
                # Get the defender's role, not the raider's role
                role = match.get('players_role', {}).get(player_id_str)
        
                print(f"Checking defender_id: {player_id} ({player_id_str})")
                print(f"Role fetched: {role}")
        
                # Check if player role allows defending
                if match['mode'] == 'custom' and role not in ['defender', 'allrounder']:
                    print(f"Skipping player {player_id} with role {role} - not a valid defender")
                    continue
            
                defender = self.bot.get_user(player_id)
                if defender:
                    defenders.append(defender)
                    print(f"Added {defender.name} to defenders list")
    
            # Create timeout timestamp (15 seconds from now)
            timeout_time = datetime.now() + timedelta(seconds=15)
            discord_timestamp = f"<t:{int(timeout_time.timestamp())}:R>"
    
            # Get raider number first
            raider_number = await self.get_raider_number(raider, discord_timestamp, match['mode'])
    
            # If raider didn't respond in elite mode, skip defender number collection
            if match['mode'] == 'elite' and raider_number is None:
                return None, {}
    
            # Start defender number collection in parallel for all defenders
            defender_dm_tasks = [self.get_defender_number(defender, discord_timestamp) for defender in defenders]
    
            # Gather all defender numbers (wait for all to complete or timeout)
            defender_results = await asyncio.gather(*defender_dm_tasks, return_exceptions=True)
    
            # Process defender results
            defender_numbers = {}
            afk_defenders = 0
            for i, result in enumerate(defender_results):
                defender = defenders[i]
                # Check if defender responded
                if isinstance(result, Exception):
                    # Defender didn't respond in time
                    afk_defenders += 1
                    defender_numbers[defender.id] = random.randint(0, 6)
                else:
                    # Defender responded
                    defender_numbers[defender.id] = result
    
            # For elite mode, handle AFK defenders by giving penalty points to raiding team
            if match['mode'] == 'elite' and afk_defenders > 0:
                raiding_team_key = match['raiding_team']
                # Add penalty points to raiding team (opponent of defender team)
                match['scores'][raiding_team_key] += afk_defenders
                await ctx.send(f"⚠️ {afk_defenders} defender(s) didn't respond in time! {match['teams'][raiding_team_key]['name']} gets +{afk_defenders} penalty point(s)!")
    
            return raider_number, defender_numbers
    
    async def get_raider_number(self, raider, timeout_timestamp, mode):
        """DM the raider to get their number"""
        try:
            # Create DM embed
            embed = discord.Embed(
                title="Your Turn to Raid!",
                description=f"Choose a number between 0-6. You have until {timeout_timestamp}",
                color=discord.Color.red()
            )
            
            if mode == 'elite':
                embed.add_field(
                    name="Elite Mode Warning",
                    value="If you don't respond in time, no number will be selected and the defending team will get a point penalty!"
                )
            else:
                embed.add_field(
                    name="Classic Mode Warning",
                    value="If you don't respond in time, a random number will be selected for you!"
                )
            
            # Send DM
            dm_channel = await raider.create_dm()
            await dm_channel.send(embed=embed)
            
            # Wait for response
            def check(m):
                return m.author.id == raider.id and isinstance(m.channel, discord.DMChannel)
            
            try:
                valid_number = None
                end_time = datetime.now() + timedelta(seconds=15)
                
                while valid_number is None and datetime.now() < end_time:
                    remaining_seconds = (end_time - datetime.now()).total_seconds()
                    if remaining_seconds <= 0:
                        break
                        
                    try:
                        msg = await self.bot.wait_for('message', check=check, timeout=remaining_seconds)
                        
                        try:
                            number = int(msg.content.strip())
                            if 0 <= number <= 6:
                                valid_number = number
                                await dm_channel.send(f"Number {number} selected! Wait for raid results in the match channel.")
                            else:
                                await dm_channel.send("Invalid number! Must be between 0-6. Please try again.")
                        except ValueError:
                            await dm_channel.send("Invalid input! Must be a number between 0-6. Please try again.")
                    except asyncio.TimeoutError:
                        break
                
                if valid_number is not None:
                    return valid_number
                    
                if mode == 'elite':
                    await dm_channel.send("Time's up! No number selected. This will give the defending team a point penalty!")
                    return None
                else:
                    random_number = random.randint(0, 6)
                    await dm_channel.send(f"Time's up! Randomly selected number {random_number} for you.")
                    return random_number
                    
            except asyncio.TimeoutError:
                if mode == 'elite':
                    await dm_channel.send("Time's up! No number selected. This will give the defending team a point penalty!")
                    return None
                else:
                    random_number = random.randint(0, 6)
                    await dm_channel.send(f"Time's up! Randomly selected number {random_number} for you.")
                    return random_number
                    
        except discord.Forbidden:
            if mode == 'elite':
                return None
            else:
                return random.randint(0, 6)
    
    async def get_defender_number(self, defender, timeout_timestamp):
        """DM a defender to get their number"""
        try:
            embed = discord.Embed(
                title="Defend Against Raid!",
                description=f"Choose a number between 0-6 to defend against the raider. You have until {timeout_timestamp}",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Defense Strategy",
                value="If you pick the same number as the raider, you'll tackle them! If multiple defenders choose the same number and it matches the raider, it's a Super Tackle!"
            )
            
            dm_channel = await defender.create_dm()
            await dm_channel.send(embed=embed)
            
            def check(m):
                return m.author.id == defender.id and isinstance(m.channel, discord.DMChannel)
            
            valid_number = None
            end_time = datetime.now() + timedelta(seconds=15)
            
            while valid_number is None and datetime.now() < end_time:
                remaining_seconds = (end_time - datetime.now()).total_seconds()
                if remaining_seconds <= 0:
                    break
                    
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=remaining_seconds)
                    
                    try:
                        number = int(msg.content.strip())
                        if 0 <= number <= 6:
                            valid_number = number
                            await dm_channel.send(f"Number {number} selected! Wait for raid results in the match channel.")
                        else:
                            await dm_channel.send("Invalid number! Must be between 0-6. Please try again.")
                    except ValueError:
                        await dm_channel.send("Invalid input! Must be a number between 0-6. Please try again.")
                except asyncio.TimeoutError:
                    break
            
            if valid_number is not None:
                return valid_number
                
            random_number = random.randint(0, 6)
            await dm_channel.send(f"Time's up! Randomly selected number {random_number} for you.")
            return random_number
                
        except discord.Forbidden:
            return random.randint(0, 6)
    
    async def process_raid_result(self, ctx, match, raider_id, raider_number, defender_numbers):
        """Process the raid result based on numbers chosen"""
        raiding_team_key = match['raiding_team']
        defending_team_key = "team_b" if raiding_team_key == "team_a" else "team_a"
        
        raider = self.bot.get_user(raider_id)
        
        # Handle elite mode raider timeout
        if match['mode'] == 'elite' and raider_number is None:
            # Elite mode: if raider times out, defending team gets a point
            result_embed = discord.Embed(
                title="Raid Result - Elite Mode Penalty!",
                description=f"Raider {raider.mention} didn't select a number in time!",
                color=discord.Color.red()
            )
            
            # Apply penalty to raiding team (give point to defending team)
            match['scores'][defending_team_key] += 1
                
            result_embed.add_field(
                name="Penalty",
                value=f"Defending team ({match['teams'][defending_team_key]['name']}) receives a point!"
            )
            
            # Store result description
            match['last_raid_result'] = f"Elite Mode Penalty: Raider was AFK. Defending team gets 1 point"
            
            await ctx.send(embed=result_embed)
            
        elif match['mode'] == 'classic' and raider_number is None:
            # This shouldn't happen in classic, but just in case
            raider_number = random.randint(0, 6)
            await ctx.send(f"System error: Raider number was not selected. Using random number {raider_number}.")
            
            # Now continue with normal processing
            await self.process_normal_raid(ctx, match, raider_id, raider_number, defender_numbers)
            
        else:
            # Normal processing for both modes
            await self.process_normal_raid(ctx, match, raider_id, raider_number, defender_numbers)
        
        # Update scorecard
        await self.update_scorecard(ctx, match)
        
        # Move to next raid
        match['current_raid_number'] += 1
        
        # Switch raiding team if we haven't reached the end
        if match['current_raid_number'] <= 10:
            match['raiding_team'] = defending_team_key
            
            # Add a small delay before next raid
            await asyncio.sleep(2)
            await self.start_raid_sequence(ctx, match)
        else:
            # End match if we've completed all raids
            await self.end_match(ctx, match)
    
    async def process_normal_raid(self, ctx, match, raider_id, raider_number, defender_numbers):
        """Process a normal raid where raider has selected a number"""
        raiding_team_key = match['raiding_team']
        defending_team_key = "team_b" if raiding_team_key == "team_a" else "team_a"

        raider = self.bot.get_user(raider_id)
        raider_id_str = str(raider_id)

        # Create result embed
        result_embed = discord.Embed(
            title=f"Raid #{match['current_raid_number']} Result",
            description=f"Raider {raider.mention} chose number **{raider_number}**",
            color=discord.Color.from_rgb(255, 165, 0)
        )

        # Count how many defenders chose each number
        defender_number_counts = {}
        for defender_id, number in defender_numbers.items():
            defender_number_counts[number] = defender_number_counts.get(number, 0) + 1

        # List of defenders who chose the same number as raider
        matching_defenders = []
        for defender_id, number in defender_numbers.items():
            if number == raider_number:
                defender = self.bot.get_user(defender_id)
                if defender:
                    matching_defenders.append(defender)

        # Check for defenders who picked the same number (potential super raid/tackle)
        super_possibilities = {}
        for number, count in defender_number_counts.items():
            if count > 1:
                super_possibilities[number] = count

        # Ensure individual_scores for raider exists
        if raider_id_str not in match['individual_scores']:
            match['individual_scores'][raider_id_str] = {'raids': 0, 'tackles': 0}

        # Ensure individual_scores for defenders exist
        for defender_id in defender_numbers.keys():
            defender_id_str = str(defender_id)
            if defender_id_str not in match['individual_scores']:
                match['individual_scores'][defender_id_str] = {'raids': 0, 'tackles': 0}

        # Handle different raid outcomes
        if matching_defenders:
            # Tackle scenario - defenders caught the raider
            if len(matching_defenders) > 1:
                # Super tackle - multiple defenders caught the raider
                points = 2
                match['scores'][defending_team_key] += points

                # Update individual scores for each defender
                for defender in matching_defenders:
                    defender_id_str = str(defender.id)
                    if defender_id_str in match['individual_scores']:
                        match['individual_scores'][defender_id_str]['tackles'] += 1
                    else:
                        # Initialize if not exists
                        match['individual_scores'][defender_id_str] = {'raids': 0, 'tackles': 1}

                # Create defender list for display
                defender_mentions = [defender.mention for defender in matching_defenders]
                defender_text = ", ".join(defender_mentions)

                result_embed.add_field(
                    name="SUPER TACKLE!",
                    value=f"Multiple defenders ({defender_text}) guessed the raider's number!\n**+{points} points** to {match['teams'][defending_team_key]['name']}",
                    inline=False
                )

                match['last_raid_result'] = f"Super Tackle! {len(matching_defenders)} defenders guessed correctly. +{points} to defending team."

            else:
                # Normal tackle - one defender caught the raider
                points = 1
                match['scores'][defending_team_key] += points

                # Update individual score for the defender
                defender_id_str = str(matching_defenders[0].id)
                if defender_id_str in match['individual_scores']:
                    match['individual_scores'][defender_id_str]['tackles'] += 1
                else:
                    # Initialize if not exists
                    match['individual_scores'][defender_id_str] = {'raids': 0, 'tackles': 1}

                result_embed.add_field(
                    name="TACKLE!",
                    value=f"{matching_defenders[0].mention} guessed the raider's number!\n**+{points} point** to {match['teams'][defending_team_key]['name']}",
                    inline=False
                )

                match['last_raid_result'] = f"Tackle! Defender guessed correctly. +{points} to defending team."

        elif super_possibilities and raider_number not in super_possibilities:
            # Super raid scenario - multiple defenders chose same number, but raider chose different
            # Find the number that multiple defenders picked
            super_number = max(super_possibilities.items(), key=lambda x: x[1])[0]
            count = super_possibilities[super_number]

            # Calculate points based on how many defenders chose the same wrong number
            points = count  # 2 for double super raid, 3 for triple
            match['scores'][raiding_team_key] += points

            # Update individual score for raider
            if raider_id_str in match['individual_scores']:
                match['individual_scores'][raider_id_str]['raids'] += points
            else:
                # Initialize if not exists
                match['individual_scores'][raider_id_str] = {'raids': points, 'tackles': 0}

            # List defenders who fell for the super raid
            super_raid_defenders = []
            for defender_id, number in defender_numbers.items():
                if number == super_number:
                    defender = self.bot.get_user(defender_id)
                    if defender:
                        super_raid_defenders.append(defender.mention)

            defender_text = ", ".join(super_raid_defenders)

            result_embed.add_field(
                name="SUPER RAID!",
                value=f"Multiple defenders ({defender_text}) chose {super_number}, but raider chose {raider_number}!\n**+{points} points** to {match['teams'][raiding_team_key]['name']}",
                inline=False
            )

            match['last_raid_result'] = f"Super Raid! {count} defenders guessed the same wrong number. +{points} to raiding team."

        else:
            # Escape scenario - raider escaped without being tackled
            points = 1
            match['scores'][raiding_team_key] += points

            # Update individual score for raider
            if raider_id_str in match['individual_scores']:
                match['individual_scores'][raider_id_str]['raids'] += points
            else:
                # Initialize if not exists
                match['individual_scores'][raider_id_str] = {'raids': points, 'tackles': 0}

            result_embed.add_field(
                name="ESCAPE!",
                value=f"No defender guessed the raider's number!\n**+{points} point** to {match['teams'][raiding_team_key]['name']}",
                inline=False
            )

            match['last_raid_result'] = f"Escape! No defender guessed correctly. +{points} to raiding team."

        # Show defender numbers for transparency
        defender_numbers_text = []
        for defender_id, number in defender_numbers.items():
            defender = self.bot.get_user(defender_id)
            if defender:
                defender_numbers_text.append(f"{defender.name}: {number}")

        result_embed.add_field(
            name="Defender Numbers",
            value="\n".join(defender_numbers_text) if defender_numbers_text else "No defenders responded",
            inline=False
        )

        # Show current scores
        result_embed.add_field(
            name="Current Score",
            value=f"{match['teams']['team_a']['name']}  {match['scores']['team_a']}  -  {match['scores']['team_b']}  {match['teams']['team_b']['name']}",
            inline=False
        )

        await ctx.send(embed=result_embed)
    
    async def end_match(self, ctx, match):
        team_a_score = match['scores']['team_a']
        team_b_score = match['scores']['team_b']

        # Determine winner
        if team_a_score > team_b_score:
            winner = "team_a"
        elif team_b_score > team_a_score:
            winner = "team_b"
        else:
            winner = "tie"

        # Create end match embed
        embed = discord.Embed(
            title="🏆 Kabaddi Match Complete! 🏆",
            description=f"The {match['mode'].capitalize()} match has ended after 20 raids!",
            color=discord.Color.gold()
        )

        # Add final score
        embed.add_field(
            name="Final Score",
            value=f"{match['teams']['team_a']['name']}  **{team_a_score}** - **{team_b_score}**  {match['teams']['team_b']['name']}",
            inline=False
        )

        # Add winner announcement
        if winner == "tie":
            embed.add_field(
                name="Result",
                value="It's a TIE! Both teams played exceptionally well!",
                inline=False
            )
        else:
            embed.add_field(
                name="Winner",
                value=f"**{match['teams'][winner]['name']}** WINS! 🎉",
                inline=False
            )

        # Add match duration
        if match.get('start_time'):
            duration = datetime.now() - match['start_time']
            minutes = int(duration.total_seconds() // 60)
            seconds = int(duration.total_seconds() % 60)
            embed.add_field(
                name="Match Duration",
                value=f"{minutes} minutes, {seconds} seconds",
                inline=False
            )

        await ctx.send(embed=embed)

        # Ensure all player IDs are properly stored as strings in individual_scores
        for player_id in match['players']:
            player_id_str = str(player_id)
            # Initialize empty stats for players who don't have any
            if player_id_str not in match['individual_scores']:
                match['individual_scores'][player_id_str] = {'raids': 0, 'tackles': 0}

        # Find top raider and defender across both teams
        top_raider_id = None
        top_defender_id = None

        top_raiders = []
        top_defenders = []

        # Step 1: Find all players with highest raid/tackle points
        max_raid = max_tackle = -1
        for player_id in match['players']:
            player_id_str = str(player_id)
            stats = match['individual_scores'].get(player_id_str, {})
            raids = stats.get('raids', 0)
            tackles = stats.get('tackles', 0)

            if raids > max_raid:
                max_raid = raids
                top_raiders = [player_id]
            elif raids == max_raid and raids > 0:  # Only include if they actually scored
                top_raiders.append(player_id)

            if tackles > max_tackle:
                max_tackle = tackles
                top_defenders = [player_id]
            elif tackles == max_tackle and tackles > 0:  # Only include if they actually scored
                top_defenders.append(player_id)

        # Step 2: If multiple top raiders/defenders, use total points, then team result
        def resolve_top(players):
            if not players:  # Handle empty list case
                return None

            if len(players) == 1:
                return players[0]

            # Compare total points
            totals = {}
            for pid in players:
                pid_str = str(pid)
                if pid_str in match['individual_scores']:
                    totals[pid] = match['individual_scores'][pid_str]['raids'] + match['individual_scores'][pid_str]['tackles']
                else:
                    totals[pid] = 0

            if not totals:  # Handle case where none of the players have scores
                return players[0]

            max_total = max(totals.values())
            top_total_players = [pid for pid, total in totals.items() if total == max_total]

            if len(top_total_players) == 1:
                return top_total_players[0]

            # Prefer player from winning team
            winning_team = None
            if match['scores']['team_a'] > match['scores']['team_b']:
                winning_team = "team_a"
            elif match['scores']['team_b'] > match['scores']['team_a']:
                winning_team = "team_b"

            if winning_team:
                for pid in top_total_players:
                    if pid in match['teams'][winning_team]['players']:
                        return pid

            # Fallback to first
            return top_total_players[0]

        top_raider_id = resolve_top(top_raiders)
        top_defender_id = resolve_top(top_defenders)

        # Get user objects for top performers
        top_raider = self.bot.get_user(top_raider_id) if top_raider_id else None
        top_defender = self.bot.get_user(top_defender_id) if top_defender_id else None

        # Create player stats embed
        stats_embed = discord.Embed(
            title="Player Statistics",
            description="Individual player performance",
            color=discord.Color.blue()
        )

        # Add stats for Team A
        team_a_stats = []
        for player_id in match['teams']['team_a']['players']:
            player = self.bot.get_user(player_id)
            player_id_str = str(player_id)
            if player and player_id_str in match['individual_scores']:
                raids = match['individual_scores'][player_id_str]['raids']
                tackles = match['individual_scores'][player_id_str]['tackles']
                total = raids + tackles

                # Highlight the top performers in their respective teams
                player_name = player.name
                if player_id == top_raider_id:
                    player_name = f"{player_name} <:top_raider:1367024739910160465>"
                elif player_id == top_defender_id:
                    player_name = f"{player_name} <:top_defender:1367026449638228030>"

                team_a_stats.append(f"{player_name}: {total} pts ({raids} raid, {tackles} tackle)")

        stats_embed.add_field(
            name=f"{match['teams']['team_a']['name']} - Players Performance",
            value="\n".join(team_a_stats) if team_a_stats else "No stats",
            inline=False
        )

        # Add stats for Team B
        team_b_stats = []
        for player_id in match['teams']['team_b']['players']:
            player = self.bot.get_user(player_id)
            player_id_str = str(player_id)
            if player and player_id_str in match['individual_scores']:
                raids = match['individual_scores'][player_id_str]['raids']
                tackles = match['individual_scores'][player_id_str]['tackles']
                total = raids + tackles

                # Highlight the top performers in their respective teams
                player_name = player.name
                if player_id == top_raider_id:
                    player_name = f"{player_name} <:top_raider:1367024739910160465>"
                elif player_id == top_defender_id:
                    player_name = f"{player_name} <:top_defender:1367026449638228030>"

                team_b_stats.append(f"{player_name}: {total} pts ({raids} raid, {tackles} tackle)")

        stats_embed.add_field(
            name=f"{match['teams']['team_b']['name']} - Players Performance",
            value="\n".join(team_b_stats) if team_b_stats else "No stats",
            inline=False
        )

        # Send the stats embed
        await ctx.send(embed=stats_embed)

        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://yogeswar165a:yogialpha12345@marvelo.air6zj6.mongodb.net/?retryWrites=true&w=majority&appName=Marvelo")

        # Ping to confirm connection is alive
        try:
            await client.admin.command("ping")
        except Exception as e:
            await ctx.send(f"❌ MongoDB connection failed: {str(e)}")
            return  # stop match cleanup if DB is not reachable

        db = client["Handkabaddi"]
        collection = db["userdata"]
        now_ts = int(datetime.now().timestamp())

        # Determine MVP(s)
        scores = match["individual_scores"]
        player_totals = {pid: data["raids"] + data["tackles"] for pid, data in scores.items()}

        if player_totals:  # Check if we have any scores at all
            top_score = max(player_totals.values())
            mvp_ids = [pid for pid, total in player_totals.items() if total == top_score]
        else:
            mvp_ids = []

        for player_id in match["players"]:
            pid_str = str(player_id)

            # Make sure player has stats entry
            if pid_str not in scores:
                scores[pid_str] = {"raids": 0, "tackles": 0}

            raids = scores[pid_str]["raids"]
            tackles = scores[pid_str]["tackles"]
            total = raids + tackles

            # Determine match result
            won = False
            team = "team_a" if player_id in match["teams"]["team_a"]["players"] else "team_b"
            if match["scores"]["team_a"] > match["scores"]["team_b"]:
                won = (team == "team_a")
            elif match["scores"]["team_b"] > match["scores"]["team_a"]:
                won = (team == "team_b")
            tie = match["scores"]["team_a"] == match["scores"]["team_b"]

            # MVP logic: give only if sole top scorer or among top but in winning team
            mvp = False
            if pid_str in mvp_ids:
                if len(mvp_ids) == 1 or won:
                    mvp = True

            # Fetch existing user doc
            user = await collection.find_one({"userid": pid_str})
            new_user = user is None

            # Build update document
            update_doc = {
                    "$inc": {
                    "matches": 1,
                    "wins": int(won),
                    "losses": int(not won and not tie),
                    "tie": int(tie),
                    "raidpoints": raids,
                    "defendpoints": tackles,
                    "super10s": int(raids > 5),
                    "high5s": int(tackles > 5),
                    "mvps": int(mvp)
                },
                "$set": {
                    "lastmatch": int(won)
                }
            }

            # On insert only
            if new_user:
                update_doc["$setOnInsert"] = {
                    "userid": pid_str,
                    "winstreak": 1 if won else 0,
                    "achievements": [],
                    "premium": now_ts
                }
            else:
                # Check win streak if already in DB
                if user.get("lastmatch") == 1 and won:
                    update_doc["$inc"]["winstreak"] = 1

            # Perform upsert
            await collection.update_one({"userid": pid_str}, update_doc, upsert=True)

            # Confirmation message
            player = self.bot.get_user(player_id)
            await ctx.send(f"✅ Updated DB for {player.name if player else pid_str}")


        # Clean up match data
        channel_id = ctx.channel.id

        # Remove all players from user_match_map
        for player_id in match['players']:
            if player_id in self.bot.__dict__["user_match_map"]:
                del self.bot.__dict__["user_match_map"][player_id]

        # Remove match from active_matches
        if channel_id in self.bot.__dict__["active_matches"]:
            del self.bot.__dict__["active_matches"][channel_id]

        # Send final message
        await ctx.send("Match has ended and all match data has been cleaned up. Thanks for playing!")


async def setup(bot):
    await bot.add_cog(StartMatch(bot))
