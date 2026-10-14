"""Read-only scripts behind the super admin skills (R-38, R-46; ``.claude/skills/``).

They read and report; they never approve, publish or write. Database reads use the application's own read
functions in a read-only transaction on the synthetic demo or test database named by ``QMS_DATABASE_URL``; in MVP-1
``operational`` mode is refused. No API credentials, no network calls, no file writes, and no path under ``.private``
or the ``.env`` file is ever opened.
"""
