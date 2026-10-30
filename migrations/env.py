
import asyncio
from logging.config import fileConfig
import selectors
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.modules.users.profile_models import UserProfile
from app.db.base import Base
from app.modules.users.models import User
from app.modules.workspaces.models import (
    Workspace,
    WorkspaceMember,
    Role,
    Permission,
    RolePermission,
)
                                      
# Importing Base registers the User model and its table metadata.
target_metadata = Base.metadata
# Alembic configuration
config = context.config

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the application's database URL.
# Escape percent signs because Config uses interpolation.
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("%", "%%"),
)




def run_migrations_offline() -> None:
    """Generate migration SQL without opening a DB connection."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using a synchronous connection bridge."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations."""

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    asyncio.run(
    run_async_migrations(),
    loop_factory=lambda: asyncio.SelectorEventLoop(
        selectors.SelectSelector()
    ),
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
