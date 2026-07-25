"""
Database ETL & Privilege Provisioning Pipeline.

Initializes the PostgreSQL database schema for clinical datasets (patients, encounters,
procedures), loads raw Synthea CSV files into database tables, and provisions a
restricted database role ('llm_user') with SELECT-only privileges.
"""

import psycopg

# Connection details matching docker-compose.yaml config
DB_CONN_STR = "host=localhost dbname=clinical_db user=admin_user password=admin_password"


def main():
    print("Connecting to the database...")
    with psycopg.connect(DB_CONN_STR) as conn:
        with conn.cursor() as cur:
            # Clean up existing tables and roles for an idempotent rerun
            print("Dropping existing tables and roles...")
            cur.execute("DROP TABLE IF EXISTS procedures CASCADE;")
            cur.execute("DROP TABLE IF EXISTS encounters CASCADE;")
            cur.execute("DROP TABLE IF EXISTS patients CASCADE;")
            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'llm_user') THEN
                        EXECUTE 'REVOKE ALL PRIVILEGES ON DATABASE clinical_db FROM llm_user;';
                        EXECUTE 'REVOKE ALL PRIVILEGES ON SCHEMA public FROM llm_user;';
                        EXECUTE 'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM llm_user;';
                        EXECUTE 'DROP ROLE llm_user;';
                    END IF;
                END
                $$;
            """)
            conn.commit()

            print("Creating relational database schema...")

            # Patients Table Definition
            cur.execute("""
                CREATE TABLE patients (
                    Id UUID PRIMARY KEY,
                    BIRTHDATE DATE,
                    DEATHDATE DATE,
                    PREFIX VARCHAR(10),
                    FIRST VARCHAR(100),
                    LAST VARCHAR(100),
                    SUFFIX VARCHAR(10),
                    MAIDEN VARCHAR(100),
                    MARITAL VARCHAR(10),
                    RACE VARCHAR(50),
                    ETHNICITY VARCHAR(100),
                    GENDER VARCHAR(10),
                    BIRTHPLACE VARCHAR(255),
                    ADDRESS VARCHAR(255),
                    CITY VARCHAR(100),
                    STATE VARCHAR(50),
                    COUNTY VARCHAR(50),
                    ZIP VARCHAR(20),
                    LAT NUMERIC(10,8),
                    LON NUMERIC(11,8)
                );
            """)

            # Encounters Table Definition
            cur.execute("""
                CREATE TABLE encounters (
                    Id UUID PRIMARY KEY,
                    START TIMESTAMP WITH TIME ZONE,
                    STOP TIMESTAMP WITH TIME ZONE,
                    PATIENT UUID REFERENCES patients(Id),
                    ORGANIZATION UUID,
                    PAYER UUID,
                    ENCOUNTERCLASS VARCHAR(100),
                    CODE BIGINT,
                    DESCRIPTION VARCHAR(255),
                    BASE_ENCOUNTER_COST NUMERIC(12,2),
                    TOTAL_CLAIM_COST NUMERIC(12,2),
                    PAYER_COVERAGE NUMERIC(12,2),
                    REASONCODE BIGINT,
                    REASONDESCRIPTION VARCHAR(255)
                );
            """)

            # Procedures Table Definition
            cur.execute("""
                CREATE TABLE procedures (
                    id SERIAL PRIMARY KEY,
                    START TIMESTAMP WITH TIME ZONE,
                    STOP TIMESTAMP WITH TIME ZONE,
                    PATIENT UUID REFERENCES patients(Id),
                    ENCOUNTER UUID REFERENCES encounters(Id),
                    CODE BIGINT,
                    DESCRIPTION VARCHAR(255),
                    BASE_COST NUMERIC(12,2),
                    REASONCODE BIGINT,
                    REASONDESCRIPTION VARCHAR(255)
                );
            """)
            conn.commit()

            # Load each CSV into PostgreSQL using COPY
            print("Loading data from CSVs into PostgreSQL...")

            print("Loading patients.csv...")
            with open("patients.csv", "r", encoding="utf-8") as f:
                with cur.copy("COPY patients FROM STDIN WITH (FORMAT CSV, HEADER)") as copy:
                    copy.write(f.read())

            print("Loading encounters.csv...")
            with open("encounters.csv", "r", encoding="utf-8") as f:
                with cur.copy("COPY encounters FROM STDIN WITH (FORMAT CSV, HEADER)") as copy:
                    copy.write(f.read())

            # Explicitly map CSV columns to bypass auto-incrementing SERIAL primary key ('id')
            print("Loading procedures.csv...")
            with open("procedures.csv", "r", encoding="utf-8") as f:
                with cur.copy(
                    "COPY procedures (START, STOP, PATIENT, ENCOUNTER, CODE, DESCRIPTION, BASE_COST, REASONCODE, REASONDESCRIPTION) "
                    "FROM STDIN WITH (FORMAT CSV, HEADER)"
                ) as copy:
                    copy.write(f.read())

            conn.commit()
            print("Data ingestion complete!")

            # Create the restricted LLM user role
            print("Creating restricted LLM user role...")

            cur.execute("CREATE ROLE llm_user WITH LOGIN PASSWORD 'llm_pass';")
            cur.execute("GRANT CONNECT ON DATABASE clinical_db TO llm_user;")
            cur.execute("GRANT USAGE ON SCHEMA public TO llm_user;")
            cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO llm_user;")
            conn.commit()

            print("Database setup and data load successful!")


if __name__ == "__main__":
    main()