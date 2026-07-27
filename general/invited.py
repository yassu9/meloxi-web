import discord
from discord.ext import commands
from discord.ui import View, Button
from sqlalchemy.orm import Session
from database.db import SessionLocal
from database.models import GuildRegistry
from ui.embeds import create_embed, create_error_embed, arrow, section, COLOR_PRIMARY

class InvitedPaginationView(View):
    def __init__(self, ctx, user, data):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.user = user
        self.data = data
        self.page = 0
        self.per_page = 10
        self.max_page = max(0, (len(data) - 1) // self.per_page)

        self.update_buttons()

    def update_buttons(self):
        # Access buttons via children since decoration order matters
        self.children[0].disabled = (self.page == 0) # Prev
        self.children[1].disabled = (self.page == self.max_page) # Next

    def get_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        chunk = self.data[start:end]
        
        embed = create_embed(user=self.ctx.author, bot_user=self.ctx.bot.user, show_footer=True)
        embed.set_author(name=f"{self.user.name} | Invites", icon_url=self.user.display_avatar.url)
        
        desc = []
        desc.append(f"> {arrow} **User**: {self.user.mention}")
        desc.append("")
        
        if not self.data:
            desc.append(f"{arrow} No servers found.")
        else:
            for s in chunk:
                desc.append(f"{arrow} **{s['name']}**")
                desc.append(f"   Members: `{s['members']}` | Role: `{s['role']}`")
                desc.append("")
        
        embed.description = "\n".join(desc)
        embed.set_footer(text=f"Page {self.page+1}/{self.max_page+1} | Total: {len(self.data)}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author: 
            return await interaction.response.defer()
        
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author: 
             return await interaction.response.defer()

        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

class InvitedCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Record who invited the bot."""
        session = SessionLocal()
        try:
            # Default to Owner
            inviter_id = str(guild.owner_id)
            
            # Try Audit Logs
            if guild.me.guild_permissions.view_audit_log:
                try:
                    async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                        if entry.target.id == self.bot.user.id:
                            inviter_id = str(entry.user.id)
                            break
                except:
                    pass
            
            entry = GuildRegistry(server_id=str(guild.id), inviter_id=inviter_id)
            session.merge(entry)
            session.commit()
        except Exception as e:
             print(f"Failed to record inviter: {e}")
             session.rollback()
        finally:
             session.close()

    @commands.hybrid_command(name="invited", aliases=["botinvited", "botservers", "myservers"])
    async def invited(self, ctx: commands.Context, user: discord.User = None):
        """Shows the list of servers where a user has added the bot."""
        user = user or ctx.author
        
        session = SessionLocal()
        try:
            processing_embed = create_embed(user=ctx.author, bot_user=self.bot.user)
            processing_embed.set_author(name=f"{user.name} | Invites", icon_url=user.display_avatar.url)
            processing_embed.description = f"> {arrow} **User**: {user.mention}\n> {arrow} Scanning servers..."
            msg = await ctx.send(embed=processing_embed)
            
            # Query DB
            records = session.query(GuildRegistry).filter_by(inviter_id=str(user.id)).all()
            
            server_data = []
            
            # Also check if user is Owner of any guilds the bot is in (Legacy Support)
            # This helps populate the list even if DB is empty for old servers
            for guild in self.bot.guilds:
                # Check DB Record first
                record = next((r for r in records if r.server_id == str(guild.id)), None)
                
                is_inviter = False
                if record: 
                    is_inviter = True
                elif guild.owner_id == user.id:
                    # Fallback: If they own the server, count it
                    is_inviter = True
                
                if is_inviter:
                    # Determine Role
                    role = "Member"
                    member = guild.get_member(user.id)
                    if member:
                        if guild.owner_id == user.id: role = "Owner"
                        elif member.guild_permissions.administrator: role = "Admin"
                        elif "Inviter" in [r.name for r in member.roles]: role = "Inviter" # Soft check
                    else:
                        role = "Left Server"

                    server_data.append({
                        "name": guild.name,
                        "id": guild.id,
                        "members": guild.member_count,
                        "role": role
                    })
            
            # Sort by Member Count
            server_data.sort(key=lambda x: x["members"], reverse=True)

            if not server_data:
                error_embed = create_error_embed(None, f"No servers found for **{user.mention}**.", user=ctx.author)
                await msg.edit(embed=error_embed)
                return

            view = InvitedPaginationView(ctx, user, server_data)
            embed = view.get_embed()
            
            await msg.edit(embed=embed, view=view if len(server_data) > 10 else None)
            
        except Exception as e:
            await ctx.send(embed=create_error_embed(None, f"Load failed: {e}", user=ctx.author), delete_after=10)
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(InvitedCog(bot))
