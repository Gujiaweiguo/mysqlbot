BEGIN;
SET client_min_messages TO WARNING;
SET session_replication_role = replica;

DO $$
DECLARE
    t record;
    c record;
    has_rows boolean;
    cols text;
    vals text;
    stmt text;
BEGIN
    FOR t IN
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    LOOP
        EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I.%I)', 'public', t.table_name) INTO has_rows;
        IF has_rows THEN
            CONTINUE;
        END IF;

        cols := '';
        vals := '';

        FOR c IN
            SELECT
                column_name,
                data_type,
                udt_name,
                ordinal_position
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = t.table_name
              AND is_nullable = 'NO'
              AND column_default IS NULL
              AND coalesce(is_identity, 'NO') = 'NO'
              AND coalesce(is_generated, 'NEVER') = 'NEVER'
            ORDER BY ordinal_position
        LOOP
            cols := cols || CASE WHEN cols = '' THEN '' ELSE ', ' END || format('%I', c.column_name);
            vals := vals || CASE WHEN vals = '' THEN '' ELSE ', ' END ||
                CASE
                    WHEN c.data_type IN ('character varying', 'character', 'text') THEN quote_literal(left(t.table_name || '_' || c.column_name || '_test', 120))
                    WHEN c.data_type IN ('timestamp without time zone', 'timestamp with time zone') THEN quote_literal('2024-01-01 00:00:00')
                    WHEN c.data_type = 'date' THEN quote_literal('2024-01-01')
                    WHEN c.data_type = 'time without time zone' THEN quote_literal('00:00:00')
                    WHEN c.data_type = 'boolean' THEN 'false'
                    WHEN c.data_type IN ('smallint', 'integer', 'bigint', 'numeric', 'real', 'double precision') THEN '1'
                    WHEN c.data_type = 'uuid' THEN quote_literal('00000000-0000-0000-0000-000000000001')
                    WHEN c.data_type IN ('json', 'jsonb') THEN quote_literal('{}')
                    WHEN c.udt_name = 'bytea' THEN 'decode('''', ''hex'')'
                    ELSE quote_literal('sample')
                END;
        END LOOP;

        BEGIN
            IF cols = '' THEN
                stmt := format('INSERT INTO %I.%I DEFAULT VALUES', 'public', t.table_name);
            ELSE
                stmt := format('INSERT INTO %I.%I (%s) VALUES (%s)', 'public', t.table_name, cols, vals);
            END IF;
            EXECUTE stmt;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Skip table % due to: %', t.table_name, SQLERRM;
        END;
    END LOOP;
END $$;

SET session_replication_role = DEFAULT;
COMMIT;
