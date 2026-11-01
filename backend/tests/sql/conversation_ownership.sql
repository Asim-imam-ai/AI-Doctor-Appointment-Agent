-- Run only against a disposable database after applying migration 006.
BEGIN;
INSERT INTO public.patients (id, external_user_id) VALUES
 ('10000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000001'),
 ('10000000-0000-4000-8000-000000000002', '20000000-0000-4000-8000-000000000002'),
 ('20000000-0000-4000-8000-000000000003', NULL),
 ('20000000-0000-4000-8000-000000000004', '20000000-0000-4000-8000-000000000005');
INSERT INTO public.conversations (id, patient_id, title) VALUES
 ('30000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', 'First'),
 ('30000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000002', 'Second');
INSERT INTO public.conversation_messages (conversation_id, role, content) VALUES
 ('30000000-0000-4000-8000-000000000001', 'USER', 'First message'),
 ('30000000-0000-4000-8000-000000000002', 'USER', 'Second message');
INSERT INTO public.user_memories (patient_id, memory_type, key, value) VALUES
 ('10000000-0000-4000-8000-000000000001', 'TIMEZONE', 'timezone', 'UTC'),
 ('10000000-0000-4000-8000-000000000002', 'TIMEZONE', 'timezone', 'UTC');

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '20000000-0000-4000-8000-000000000001', true);
DO $$
BEGIN
    IF (SELECT count(*) FROM public.conversations) <> 1
       OR (SELECT count(*) FROM public.conversation_messages) <> 1
       OR (SELECT count(*) FROM public.user_memories) <> 1 THEN
        RAISE EXCEPTION 'RLS must expose only the authenticated patient records';
    END IF;
    BEGIN
        INSERT INTO public.conversations (patient_id) VALUES ('10000000-0000-4000-8000-000000000001');
        RAISE EXCEPTION 'Direct authenticated writes should be denied';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
END;
$$;
SELECT set_config('request.jwt.claim.sub', '20000000-0000-4000-8000-000000000003', true);
DO $$
BEGIN
    IF NOT public.conversation_patient_owned_by_current_user('20000000-0000-4000-8000-000000000003') THEN
        RAISE EXCEPTION 'Unlinked legacy patient ID should resolve';
    END IF;
END;
$$;
SELECT set_config('request.jwt.claim.sub', '20000000-0000-4000-8000-000000000004', true);
DO $$
BEGIN
    IF public.conversation_patient_owned_by_current_user('20000000-0000-4000-8000-000000000004') THEN
        RAISE EXCEPTION 'A patient linked to a different user must not resolve by ID';
    END IF;
END;
$$;
ROLLBACK;
