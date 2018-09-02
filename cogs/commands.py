import asyncio
import re
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from ext.utils import get_perm_level
from ext.command import command


class MemberOrID(commands.MemberConverter):
    async def convert(self, ctx, argument):
        try:
            result = await super().convert(ctx, argument)
        except commands.BadArgument as e:
            match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
            if match:
                result = discord.Object(int(match.group(1)))
            else:
                raise commands.BadArgument(f'Member {argument} not found') from e

        return result


class Commands:
    def __init__(self, bot):
        self.bot = bot

    async def __error(self, ctx, error):
        """Handles discord.Forbidden"""
        if isinstance(error, discord.Forbidden):
            await ctx.send(f'I do not have the required permissions needed to run `{ctx.command.name}`.')

    @command(0, aliases=['level'])
    async def mylevel(self, ctx):
        """Checks your permission level"""
        perm_level = get_perm_level(ctx.author, await ctx.guild_info())
        await ctx.send(f'You are on level {perm_level[0]} ({perm_level[1]})')

    @command(5)
    async def user(self, ctx, member: discord.Member):
        """Get a user's info"""
        async def timestamp(created):
            delta = datetime.utcnow() - created
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            days, hours = divmod(hours, 24)
            months, days = divmod(days, 30)
            years, months = divmod(months, 12)
            fmt = '{hours} hours'
            if days:
                fmt = '{days} days ' + fmt
            if months:
                fmt = '{months} months ' + fmt
            if years:
                fmt = '{years} years ' + fmt

            offset = (await ctx.guild_config()).get('time_offset', 0)
            created += timedelta(hours=offset)

            return f"{fmt.format(hours=hours, days=days, months=months, years=years)} ago ({created.strftime('%H:%M:%S')})"

        created = await timestamp(member.created_at)
        joined = await timestamp(member.joined_at)
        member_info = f'**Joined** {joined}\n'

        for n, i in enumerate(reversed(member.roles)):
            if i != ctx.guild.default_role:
                if n == 0:
                    member_info += '**Roles**: '
                member_info += i.name
                if n != len(member.roles) - 2:
                    member_info += ', '
                else:
                    member_info += '\n'

        em = discord.Embed(color=member.color)
        em.set_author(name=member, icon_url=member.avatar_url)
        em.add_field(name='Basic Information', value=f'**ID**: {member.id}\n**Nickname**: {member.nick}\n**Mention**: {member.mention}\n**Created** {created}', inline=False)
        em.add_field(name='Member Information', value=member_info, inline=False)
        await ctx.send(embed=em)

    @command(5)
    async def mute(self, ctx, member: discord.Member, duration: int=None, *, reason=None):
        """Mutes a user"""
        if get_perm_level(member, await ctx.guild_info()) >= get_perm_level(ctx.author, await ctx.guild_info()):
            await ctx.send('User has insufficient permissions')
        else:
            await self.bot.mute(member, duration, reason=reason)
            await ctx.send(self.bot.accept)

    @command(5)
    async def unmute(self, ctx, member: discord.Member, *, reason=None):
        """Unmutes a user"""
        if get_perm_level(member, await ctx.guild_info()) >= get_perm_level(ctx.author, await ctx.guild_info()):
            await ctx.send('User has insufficient permissions')
        else:
            await self.bot.unmute(ctx.guild.id, member.id, None, reason=reason)
            await ctx.send(self.bot.accept)

    @command(5, aliases=['clean', 'prune'])
    async def purge(self, ctx, limit: int, member: MemberOrID=None):
        """Deletes messages in bulk"""
        def predicate(m):
            if member:
                return m.id == member.id
            return True

        await ctx.channel.purge(limit, check=predicate)
        accept = await ctx.send(self.bot.accept)
        await asyncio.sleep(3)
        await accept.delete()
        await ctx.message.delete()

    @command(6)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Kicks a user"""
        if get_perm_level(member, await ctx.guild_info()) >= get_perm_level(ctx.author, await ctx.guild_info()):
            await ctx.send('User has insufficient permissions')
        else:
            await member.kick(reason=reason)
            await ctx.send(self.bot.accept)

    @command(6)
    async def softban(self, ctx, member: discord.Member, *, reason=None):
        """Swings the banhammer"""
        if get_perm_level(member, await ctx.guild_info()) >= get_perm_level(ctx.author, await ctx.guild_info()):
            await ctx.send('User has insufficient permissions')
        else:
            await member.ban(reason=reason)
            await asyncio.sleep(2)
            await member.unban(reason=reason)
            await ctx.send(self.bot.accept)

    @command(6)
    async def ban(self, ctx, member: MemberOrID, *, reason=None):
        """Swings the banhammer"""
        await ctx.guild.ban(member, reason=reason)
        await ctx.send(self.bot.accept)


def setup(bot):
    bot.add_cog(Commands(bot))