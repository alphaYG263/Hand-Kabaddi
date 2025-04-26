import discord
from discord.ext import commands
from discord.ui import Select, Button, View
import random
import asyncio
from datetime import datetime, timedelta

class StartMatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_raids = {}
    
    @commands.command(name="start", aliases=["s"])
    async def start(self, ctx):
        """Start a match that has been set up (host only)"""
        # Get reference to global data structures
        active_matches = self.bot.get_cog("StartMatch").bot.__dict__["active_matches"]
        
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
            
        # Check if there are 6 players (3v3)
        if len(match['players']) != 6:
            return await ctx.send(f"Need exactly 6 players to start (currently {len(match['players'])}/6).")
            
        # Check if both teams have 3 players each
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
            value="30 (15 per team)"
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
            description=f"Raid {match['current_raid_number']}/30",
            color=discord.Color.blue()
        )
        
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
        if match['current_raid_number'] > 30:
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
                
                # Create select menu
                select = Select(
                    placeholder="Choose a raider...",
                    min_values=1,
                    max_values=1
                )
                
                # Add options for each player in raiding team
                for player_id in raiding_team['players']:
                    player = bot.get_user(player_id)
                    if player:
                        select.add_option(
                            label=player.name,
                            value=str(player_id),
                            description=f"Select {player.name} as raider"
                        )
                
                # Set callback
                select.callback = self.raider_selected_callback
                self.add_item(select)
            
            async def raider_selected_callback(self, interaction):
                # Check if the person selecting is the captain
                if interaction.user.id != captain_id:
                    return await interaction.response.send_message("Only the team captain can select raiders!", ephemeral=True)
                
                # Get selected raider ID
                self.raider_selected = int(interaction.data['values'][0])
                
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
        await ctx.send(embed=embed, view=raider_view)
        
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
            defender = self.bot.get_user(player_id)
            if defender:
                defenders.append(defender)
        
        # Create timeout timestamp (15 seconds from now)
        timeout_time = datetime.now() + timedelta(seconds=15)
        discord_timestamp = f"<t:{int(timeout_time.timestamp())}:R>"
        
        # Send DMs to all players
        raider_dm_task = asyncio.create_task(self.get_raider_number(raider, discord_timestamp, match['mode']))
        defender_dm_tasks = [self.get_defender_number(defender, discord_timestamp) for defender in defenders]
        
        # Wait for all DMs to be completed
        raider_task_result = None
        try:
            # Wait for raider number with timeout
            raider_task_result = await asyncio.wait_for(raider_dm_task, timeout=16)
        except asyncio.TimeoutError:
            # Pick random number for raider if timed out
            raider_number = None
            if match['mode'] == 'classic':
                raider_number = random.randint(0, 6)
                await ctx.send(f"⏱️ Raider {raider.mention} didn't choose a number in time! Random number was chosen.")
            # For elite mode, leave as None
        else:
            raider_number = raider_task_result
        
        # Gather defender numbers
        defender_numbers = {}
        for i, defender in enumerate(defenders):
            try:
                # Wait for defender number with timeout
                defender_task = defender_dm_tasks[i]
                number = await asyncio.wait_for(defender_task, timeout=16)
                if number is not None:  # Only add if defender responded
                    defender_numbers[defender.id] = number
            except asyncio.TimeoutError:
                # Pick random number for defender if timed out
                defender_numbers[defender.id] = random.randint(0, 6)
        
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
                # Check if the message is from the raider and in their DM channel
                return m.author.id == raider.id and isinstance(m.channel, discord.DMChannel)
            
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                
                # Parse number
                try:
                    number = int(msg.content.strip())
                    if 0 <= number <= 6:
                        await dm_channel.send(f"Number {number} selected! Wait for raid results in the match channel.")
                        return number
                    else:
                        await dm_channel.send("Invalid number! Must be between 0-6. Selecting a random number...")
                        return random.randint(0, 6)
                except ValueError:
                    await dm_channel.send("Invalid input! Must be a number between 0-6. Selecting a random number...")
                    return random.randint(0, 6)
                    
            except asyncio.TimeoutError:
                if mode == 'elite':
                    await dm_channel.send("Time's up! No number selected. This will give the defending team a point penalty!")
                    return None
                else:  # classic mode
                    random_number = random.randint(0, 6)
                    await dm_channel.send(f"Time's up! Randomly selected number {random_number} for you.")
                    return random_number
                    
        except discord.Forbidden:
            # Couldn't DM the user
            return random.randint(0, 6)
    
    async def get_defender_number(self, defender, timeout_timestamp):
        """DM a defender to get their number"""
        try:
            # Create DM embed
            embed = discord.Embed(
                title="Defend Against Raid!",
                description=f"Choose a number between 0-6 to defend against the raider. You have until {timeout_timestamp}",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Defense Strategy",
                value="If you pick the same number as the raider, you'll tackle them! If multiple defenders choose the same number and it matches the raider, it's a Super Tackle!"
            )
            
            # Send DM
            dm_channel = await defender.create_dm()
            await dm_channel.send(embed=embed)
            
            # Wait for response
            def check(m):
                # Check if the message is from the defender and in their DM channel
                return m.author.id == defender.id and isinstance(m.channel, discord.DMChannel)
            
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                
                # Parse number
                try:
                    number = int(msg.content.strip())
                    if 0 <= number <= 6:
                        await dm_channel.send(f"Number {number} selected! Wait for raid results in the match channel.")
                        return number
                    else:
                        await dm_channel.send("Invalid number! Must be between 0-6. Selecting a random number...")
                        return random.randint(0, 6)
                except ValueError:
                    await dm_channel.send("Invalid input! Must be a number between 0-6. Selecting a random number...")
                    return random.randint(0, 6)
                    
            except asyncio.TimeoutError:
                random_number = random.randint(0, 6)
                await dm_channel.send(f"Time's up! Randomly selected number {random_number} for you.")
                return random_number
                
        except discord.Forbidden:
            # Couldn't DM the user
            return random.randint(0, 6)
    
    async def process_raid_result(self, ctx, match, raider_id, raider_number, defender_numbers):
        """Process the raid result based on numbers chosen"""
        raiding_team_key = match['raiding_team']
        defending_team_key = "team_b" if raiding_team_key == "team_a" else "team_a"
        
        raider = self.bot.get_user(raider_id)
        
        # Handle elite mode raider timeout
        if match['mode'] == 'elite' and raider_number is None:
            # Elite mode: if raider times out, defending team gets 1 point penalty
            result_embed = discord.Embed(
                title="Raid Result - Elite Mode Penalty!",
                description=f"Raider {raider.mention} didn't select a number in time!",
                color=discord.Color.red()
            )
            
            # Apply penalty to defending team
            match['scores'][defending_team_key] -= 1
            if match['scores'][defending_team_key] < 0:
                match['scores'][defending_team_key] = 0  # Prevent negative scores
                
            result_embed.add_field(
                name="Penalty",
                value=f"Defending team ({match['teams'][defending_team_key]['name']}) receives a 1 point penalty!"
            )
            
            # Store result description
            match['last_raid_result'] = f"Elite Mode Penalty: Defending team loses 1 point"
            
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
        if match['current_raid_number'] <= 30:
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
        
        # Create result embed
        result_embed = discord.Embed(
            title=f"Raid #{match['current_raid_number']} Result",
            description=f"Raider {raider.mention} chose number **{raider_number}**",
            color=discord.Color.gold()
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
        
        # Handle different raid outcomes
        if matching_defenders:
            # Tackle scenario - defenders caught the raider
            if len(matching_defenders) > 1:
                # Super tackle - multiple defenders caught the raider
                points = 2
                match['scores'][defending_team_key] += points
                
                # Update individual scores for each defender
                for defender in matching_defenders:
                    match['individual_scores'][defender.id]['tackles'] += 1
                
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
                match['individual_scores'][matching_defenders[0].id]['tackles'] += 1
                
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
            match['individual_scores'][raider_id]['raids'] += points
            
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
            match['individual_scores'][raider_id]['raids'] += points
            
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
            value=f"{match['teams']['team_a']['name']}: {match['scores']['team_a']}\n{match['teams']['team_b']['name']}: {match['scores']['team_b']}",
            inline=False
        )
        
        await ctx.send(embed=result_embed)
    
    async def end_match(self, ctx, match):
        """End the match and determine the winner"""
        # Calculate final scores
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
            description=f"The {match['mode'].capitalize()} match has ended after 30 raids!",
            color=discord.Color.gold()
        )
        
        # Add final score
        embed.add_field(
            name="Final Score",
            value=f"{match['teams']['team_a']['name']}: **{team_a_score}**\n{match['teams']['team_b']['name']}: **{team_b_score}**",
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
            if player and player_id in match['individual_scores']:
                raids = match['individual_scores'][player_id]['raids']
                tackles = match['individual_scores'][player_id]['tackles']
                total = raids + tackles
                team_a_stats.append(f"{player.name}: {total} pts ({raids} raid, {tackles} tackle)")
        
        stats_embed.add_field(
            name=match['teams']['team_a']['name'],
            value="\n".join(team_a_stats) if team_a_stats else "No stats",
            inline=False
        )
        
        # Add stats for Team B
        team_b_stats = []
        for player_id in match['teams']['team_b']['players']:
            player = self.bot.get_user(player_id)
            if player and player_id in match['individual_scores']:
                raids = match['individual_scores'][player_id]['raids']
                tackles = match['individual_scores'][player_id]['tackles']
                total = raids + tackles
                team_b_stats.append(f"{player.name}: {total} pts ({raids} raid, {tackles} tackle)")
        
        stats_embed.add_field(
            name=match['teams']['team_b']['name'],
            value="\n".join(team_b_stats) if team_b_stats else "No stats",
            inline=False
        )
        
        # Send the stats embed
        await ctx.send(embed=stats_embed)
        
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


def setup(bot):
    bot.add_cog(StartMatch(bot))
