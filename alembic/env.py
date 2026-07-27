from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db import normalize_sqlalchemy_url

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", normalize_sqlalchemy_url(get_settings().database_url))
target_metadata = None


def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    supplied_connection = config.attributes.get("connection")
    connectable = supplied_connection or engine_from_config(
        config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    def migrate(connection):
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    if supplied_connection is not None:
        migrate(supplied_connection)
    else:
        with connectable.connect() as connection:
            migrate(connection)


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
