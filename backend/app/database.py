import os
from databases import Database


DATABASE_URL = os.environ.get('DATABASE_URL')
EMBEDDINGS_SIZE = os.environ.get('EMBEDDINGS_SIZE', 1024)
database = Database(DATABASE_URL)


async def create_tables(database: Database):
    await database.execute(f"""
        CREATE TABLE IF NOT EXISTS "user" (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE,
            username VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255),
            preference_text TEXT,
            preference_keywords TEXT[],
            preference_embedding vector({EMBEDDINGS_SIZE})
        );
    """)

    await database.execute(f"""
        CREATE TABLE IF NOT EXISTS "sources"(
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            url TEXT,
            favicon TEXT
        );
    """)

    await database.execute(f"""
        CREATE TABLE IF NOT EXISTS "articles" (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE,
            title TEXT,
            date TIMESTAMP,
            summary TEXT,
            content TEXT,
            title_embedding vector({EMBEDDINGS_SIZE}),
            source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL
        );
    """)

    await database.execute("""
        CREATE TABLE IF NOT EXISTS "reports" (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES "user"(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            text TEXT
        );
    """)

    await database.execute("""
        CREATE TABLE IF NOT EXISTS "report_sections" (
            id SERIAL PRIMARY KEY,
            content TEXT,
            report_id INTEGER REFERENCES reports(id) ON DELETE SET NULL,
            article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL
        );
    """)


async def seed_database(database: Database):
    await database.execute("""
        INSERT INTO "user" (email, username, password_hash, subscription_status, subscription_id, preference_keywords)
        VALUES ('admin@example.com', 'admin', 'admin', 'active', 'test', ARRAY['nvidia', 'openai', 'langchain'])
        ON CONFLICT (email) DO NOTHING;
    """)


async def initialize_database(database: Database):
    await database.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    await create_tables(database)
    await seed_database(database)


async def tables_exist(database: Database) -> bool:
    required_tables = {'user', 'sources', 'articles', 'reports', 'report_sections'}
    existing_tables = await database.fetch_all(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
    )
    existing_table_names = {table['table_name'] for table in existing_tables}
    return required_tables.issubset(existing_table_names)
