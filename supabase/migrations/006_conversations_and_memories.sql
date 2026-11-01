-- Add the persistence required by conversation history and patient preferences.
-- This migration preserves existing rows and fails rather than deleting duplicates.
BEGIN;

CREATE TABLE IF NOT EXISTS public.conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id uuid NOT NULL REFERENCES public.patients(id) ON DELETE RESTRICT,
    title varchar(255) NOT NULL DEFAULT 'New Conversation',
    status varchar(50) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'ARCHIVED', 'DELETED')),
    summary text,
    last_message_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.conversation_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES public.conversations(id) ON DELETE RESTRICT,
    role varchar(50) NOT NULL,
    content varchar(4000) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.user_memories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id uuid NOT NULL REFERENCES public.patients(id) ON DELETE RESTRICT,
    memory_type varchar(50) NOT NULL,
    key varchar(100) NOT NULL,
    value varchar(500) NOT NULL,
    source varchar(50) NOT NULL DEFAULT 'EXPLICIT_USER',
    is_active boolean NOT NULL DEFAULT true,
    expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Existing installations may already contain these tables without foreign keys.
-- NOT VALID keeps existing rows intact while enforcing the relationship for new
-- writes; validate any legacy rows separately after inspecting them.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE contype = 'f' AND conrelid = 'public.conversations'::regclass
          AND confrelid = 'public.patients'::regclass
          AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'public.conversations'::regclass AND attname = 'patient_id')]::smallint[]
          AND confkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'public.patients'::regclass AND attname = 'id')]::smallint[]
    ) THEN
        ALTER TABLE public.conversations ADD CONSTRAINT conversations_patient_fk_v1
            FOREIGN KEY (patient_id) REFERENCES public.patients(id) ON DELETE RESTRICT NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE contype = 'f' AND conrelid = 'public.conversation_messages'::regclass
          AND confrelid = 'public.conversations'::regclass
          AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'public.conversation_messages'::regclass AND attname = 'conversation_id')]::smallint[]
          AND confkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'public.conversations'::regclass AND attname = 'id')]::smallint[]
    ) THEN
        ALTER TABLE public.conversation_messages ADD CONSTRAINT conversation_messages_conversation_fk_v1
            FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE RESTRICT NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE contype = 'f' AND conrelid = 'public.user_memories'::regclass
          AND confrelid = 'public.patients'::regclass
          AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'public.user_memories'::regclass AND attname = 'patient_id')]::smallint[]
          AND confkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'public.patients'::regclass AND attname = 'id')]::smallint[]
    ) THEN
        ALTER TABLE public.user_memories ADD CONSTRAINT user_memories_patient_fk_v1
            FOREIGN KEY (patient_id) REFERENCES public.patients(id) ON DELETE RESTRICT NOT VALID;
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_conversations_patient_last_message
    ON public.conversations (patient_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_created
    ON public.conversation_messages (conversation_id, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_memories_patient_key
    ON public.user_memories (patient_id, key);
CREATE INDEX IF NOT EXISTS idx_user_memories_patient_active
    ON public.user_memories (patient_id, is_active);

-- Onboarding links patients.external_user_id to auth.uid(); legacy profiles
-- may instead use the Auth UUID as their patient ID. Restrict the function to
-- this ownership check and pin its search path because it bypasses patient RLS.
CREATE OR REPLACE FUNCTION public.conversation_patient_owned_by_current_user(target_patient uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT auth.uid() IS NOT NULL AND EXISTS (
        SELECT 1 FROM public.patients AS p
        WHERE p.id = target_patient
          AND (p.external_user_id = auth.uid()::text
               OR (p.external_user_id IS NULL AND p.id = auth.uid()))
    );
$$;
REVOKE ALL ON FUNCTION public.conversation_patient_owned_by_current_user(uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.conversation_patient_owned_by_current_user(uuid) TO authenticated, service_role;

ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_memories ENABLE ROW LEVEL SECURITY;

-- The backend uses the service-role client and enforces ownership before writes.
-- Direct authenticated access is read-only unless an existing policy permits more.
GRANT SELECT ON public.conversations, public.conversation_messages, public.user_memories TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.conversations, public.conversation_messages, public.user_memories TO service_role;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'conversations' AND policyname = 'conversation_owner_read_v1') THEN
        CREATE POLICY conversation_owner_read_v1 ON public.conversations
            FOR SELECT TO authenticated
            USING (public.conversation_patient_owned_by_current_user(patient_id));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'conversation_messages' AND policyname = 'conversation_message_owner_read_v1') THEN
        CREATE POLICY conversation_message_owner_read_v1 ON public.conversation_messages
            FOR SELECT TO authenticated
            USING (EXISTS (
                SELECT 1 FROM public.conversations AS c
                WHERE c.id = conversation_id
                  AND public.conversation_patient_owned_by_current_user(c.patient_id)
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'user_memories' AND policyname = 'conversation_memory_owner_read_v1') THEN
        CREATE POLICY conversation_memory_owner_read_v1 ON public.user_memories
            FOR SELECT TO authenticated
            USING (public.conversation_patient_owned_by_current_user(patient_id));
    END IF;
END;
$$;

-- Delivered on commit, prompting PostgREST to discover the new schema.
NOTIFY pgrst, 'reload schema';
COMMIT;
