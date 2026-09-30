--
-- PostgreSQL database dump
--

\restrict zRXYcJZ85aS65Uejr5mFldcPa4sFUWgOENcbiZfidc633f8LAntrjP5kEp9cUEZ

-- Dumped from database version 17.9 (Debian 17.9-1.pgdg13+1)
-- Dumped by pg_dump version 17.9 (Debian 17.9-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: capstone_v2_migrator
--

COPY public.alembic_version (version_num) FROM stdin;
pg_v2_baseline
\.


--
-- Data for Name: experiment_execution_gate; Type: TABLE DATA; Schema: public; Owner: capstone_v2_migrator
--

COPY public.experiment_execution_gate (singleton, owner, db_pid, process_evidence, blocked_reason, updated_at) FROM stdin;
t	\N	\N	{}	\N	2026-09-30 15:21:15.023629+00
\.


--
-- PostgreSQL database dump complete
--

\unrestrict zRXYcJZ85aS65Uejr5mFldcPa4sFUWgOENcbiZfidc633f8LAntrjP5kEp9cUEZ

