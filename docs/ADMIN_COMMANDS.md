# Admin Commands Guide

All admin commands are **slash commands** (use `/` prefix).

## Permission Model

- **Server commands**: Guild owner only
- **Club/Member/Session/Discussion commands**: Guild owner OR club admin/owner in the target club

Guild owners have unrestricted access to all commands in their server. This allows bootstrapping:
register server → create first club → add members → promote an admin.

## Using an Admin Channel

All club/member/session/discussion commands accept an optional `channel` parameter so they can be
issued from a dedicated `#admin` channel without needing to navigate to the club channel.

```
# From #admin channel, targeting #book-club (id: 123456789)
/member_add user: alice channel: 123456789
/session_create title: "Dune" author: "Frank Herbert" channel: 123456789
/club_delete channel: 123456789
```

Omitting the `channel` parameter targets the current channel as usual.

---

## Server Commands

These are server-wide operations and do **not** support the `channel` parameter.

### `/server_register`

Registers the Discord server with the bot.

**Permission**: Guild owner only  
**Usage**: `/server_register`

### `/server_update`

Updates the server's registered name.

**Permission**: Guild owner only  
**Usage**: `/server_update name: <new_name>`

**Example**: `/server_update name: "My Book Club Server"`

### `/server_delete`

Deletes the server registration and ALL associated data (clubs, members, sessions, discussions).

**Permission**: Guild owner only  
**Usage**: `/server_delete`  
**Confirmation**: Requires `y`

---

## Club Commands

### `/club_create`

Creates a new book club. The caller is **automatically assigned as club owner**.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/club_create name: <name> [channel: <channel_id>]`

**Examples**:
```
/club_create name: "Classic Literature"
/club_create name: "Sci-Fi Club" channel: 123456789
```

### `/club_update`

Updates club details. Use `new_channel` to move the club to a different Discord channel.
Use `channel` to target a specific club from another channel (e.g. `#admin`).

**Permission**: Guild owner OR club admin in the target channel  
**At least one of** `name` or `new_channel` required

**Examples**:
```
/club_update name: "Sci-Fi Readers"
/club_update new_channel: 987654321
/club_update name: "Updated" new_channel: 987654321 channel: 123456789
```

### `/club_delete`

Deletes the book club and all its data.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/club_delete [channel: <channel_id>]`  
**Confirmation**: Requires `y`

**Example**: `/club_delete channel: 123456789`

---

## Member Commands

### `/member_add`

Adds a Discord user to a club. If the user already has a member record (from another club),
they are linked to this club without creating a duplicate.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/member_add user: @Username [channel: <channel_id>]`

**Examples**:
```
/member_add user: alice
/member_add user: alice channel: 123456789
```

### `/member_remove`

Removes a member by their ID.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/member_remove member_id: <member_id> [channel: <channel_id>]`  
**Confirmation**: Requires `y`

**Example**: `/member_remove member_id: 42 channel: 123456789`

### `/member_role`

Updates a member's role in the club.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/member_role member_id: <member_id> role: <admin|member> [channel: <channel_id>]`

**Roles**:
- `admin` — Can manage club/members/sessions/discussions
- `member` — Standard membership, read-only access to club commands

**Examples**:
```
/member_role member_id: 42 role: admin
/member_role member_id: 42 role: member channel: 123456789
```

---

## Session Commands

### `/session_create`

Creates a new reading session for a club. Supports autocomplete for book search.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/session_create title: "<title>" author: <author> [channel: <channel_id>]`

**Examples**:
```
/session_create title: "The Great Gatsby" author: "F. Scott Fitzgerald"
/session_create title: "Dune" author: "Frank Herbert" channel: 123456789
```

### `/session_update`

Updates the active session. At least one of `due_date` or `book` required.

**Permission**: Guild owner OR club admin in the target channel  

**Parameters**:
- `due_date` — Session due date in YYYY-MM-DD format
- `book` — Book title and author (autocomplete-enabled)
- `channel` — Optional target channel ID

**Examples**:
```
/session_update due_date: 2026-06-15
/session_update book: "Dune" channel: 123456789
/session_update due_date: 2026-06-15 book: "Dune" channel: 123456789
```

### `/session_delete`

Deletes the active reading session.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/session_delete [channel: <channel_id>]`  
**Confirmation**: Requires `y`

**Example**: `/session_delete channel: 123456789`

---

## Discussion Commands

Discussion commands manage discussion topics for reading sessions. Discussions can be synced to Discord events for calendar integration.

### `/discussion_add`

Adds a discussion topic to the active session.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/discussion_add title: <title> date: <YYYY-MM-DD> [channel: <channel_id>]`

**Examples**:
```
/discussion_add title: "Character Analysis" date: 2026-05-15
/discussion_add title: "Plot Summary" date: 2026-05-20 channel: 123456789
```

### `/discussion_update`

Updates an existing discussion in the active session.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/discussion_update discussion: <discussion_id> title: <title> date: <YYYY-MM-DD> [channel: <channel_id>]`

**Note**: Use autocomplete to select from available discussions

**Examples**:
```
/discussion_update discussion: "Character Analysis — 2026-05-15" title: "Character Deep Dive" date: 2026-05-22
/discussion_update discussion: "Theme Discussion — 2026-05-25" title: "Major Themes" channel: 123456789
```

### `/discussion_delete`

Deletes a discussion from the active session.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/discussion_delete discussion: <discussion_id> [channel: <channel_id>]`  
**Confirmation**: Requires `y`

**Example**: `/discussion_delete discussion: "Character Analysis — 2026-05-15"`

### `/discussion_sync`

Creates Discord events (calendar entries) for any discussions that don't have one yet.
Automatically syncs discussion date and title to the Discord event.

**Permission**: Guild owner OR club admin in the target channel  
**Usage**: `/discussion_sync [channel: <channel_id>]`

**Example**: `/discussion_sync channel: 123456789`

---

## Utility Commands

### `/version`

Shows the current version of the bot.

**Usage**: `/version`

### `/admin_help`

Shows detailed admin command reference (in-Discord).

**Usage**: `/admin_help`

### `/setup`

First-run wizard: registers the server and creates a book club in one command.

**Permission**: Guild owner only  
**Usage**: `/setup`

---

## Error Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `❌ Only the server owner can use this command` | Non-owner running a server command | Ask the guild owner |
| `❌ You need to be a club admin or owner` | Insufficient permissions | Ask a club admin or the guild owner |
| `❌ No book club found in that channel` | No club linked to the target channel | Create one with `/club_create` |
| `❌ No active session found in that channel` | No reading session in progress | Create one with `/session_create` |
| `❌ Role must be 'admin' or 'member'` | Invalid role in `/member_role` | Use `admin` or `member` |
| `⏰ Confirmation timed out` | No response within 30 seconds | Re-run the command |

---

## Bootstrap Workflow

Fresh server setup from an `#admin` channel (channel ID: `123456`):

```
1. /server_register
   ✅ Server registered

2. /club_create name: "My Book Club" channel: 123456
   ✅ Club created — caller assigned as owner

3. /member_add user: alice channel: 123456
   ✅ Alice added

4. /member_role member_id: <alice_id> role: admin channel: 123456
   ✅ Alice is now admin

5. /session_create title: "Dune" author: "Frank Herbert" channel: 123456
   ✅ Session created

6. /session_update due_date: 2026-06-15 channel: 123456
   ✅ Due date set

7. /discussion_add title: "Character Analysis" date: 2026-05-15 channel: 123456
   ✅ Discussion added

8. /discussion_sync channel: 123456
   ✅ Discord events created for discussions
```
