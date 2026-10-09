# Moderation history

Moderation actions recorded through the bot are saved in SQLite at
`data/moderation.sqlite3` by default. Set `MODERATION_DB_PATH` to override the
location. When deploying on Railway, create a Railway Volume and mount it at
`/app/data`; Dockerfile `VOLUME` instructions are not supported by Railway.
Without a persistent volume mounted there, the database is lost when the
container is replaced.

Set `MODERATION_INDEXER_USER_ID` to the Discord user ID authorized to run the
one-time import. It defaults to the configured moderator's ID. The bot also
needs permission to view the moderation log channel and read its history.

Run `/index_moderation_history` once in the server containing the configured
moderation log channel. The command imports moderation embeds and refuses to
run again after a successful import. If an import fails, it can be retried;
already imported log entries are deduplicated.

Use `/moderate user:<user>` to privately review the latest recorded actions,
including reasons and durations, and choose Timeout, Ban, Kick, or Blacklist.
The action form requires at least one uploaded evidence file. Timeout also
requires a duration. Blacklist accepts comma-separated categories: `tickets`,
`code_sharing`, `exalted`, and `creations`.

The configured indexer ID is `816889500813754399`. Change the
`MODERATION_INDEXER_USER_ID` environment variable if the authorized account
changes.
