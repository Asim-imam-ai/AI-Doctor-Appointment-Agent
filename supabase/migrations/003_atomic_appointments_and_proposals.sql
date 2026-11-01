-- Additive consistency and approval storage. Existing notification/reminder
-- tables are intentionally left untouched as historical schema.

ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS availability_id UUID
    REFERENCES doctor_availability(id) ON DELETE RESTRICT;

-- Link legacy appointments only where exactly one matching slot exists.
WITH matches AS (
    SELECT a.id AS appointment_id, s.id AS slot_id,
           count(*) OVER (PARTITION BY a.id) AS slots_for_appointment,
           count(*) OVER (PARTITION BY s.id) AS appointments_for_slot
    FROM appointments AS a
    JOIN doctor_availability AS s
      ON s.doctor_id = a.doctor_id
     AND s.start_time = a.start_time
     AND s.end_time = a.end_time
    WHERE a.availability_id IS NULL
      AND a.status IN ('PENDING', 'CONFIRMED')
), unique_matches AS (
    SELECT appointment_id, slot_id
    FROM matches
    WHERE slots_for_appointment = 1 AND appointments_for_slot = 1
)
UPDATE appointments AS a
SET availability_id = m.slot_id
FROM unique_matches AS m
WHERE a.id = m.appointment_id;

UPDATE doctor_availability AS s
SET status = 'BOOKED', updated_at = NOW()
FROM appointments AS a
WHERE a.availability_id = s.id
  AND a.status IN ('PENDING', 'CONFIRMED')
  AND s.status = 'AVAILABLE';

CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_active_availability
    ON appointments(availability_id)
    WHERE availability_id IS NOT NULL AND status IN ('PENDING', 'CONFIRMED');

CREATE TABLE IF NOT EXISTS appointment_proposals (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    action TEXT NOT NULL CHECK (action IN ('BOOKING', 'CANCELLATION', 'RESCHEDULING')),
    version INTEGER NOT NULL CHECK (version > 0),
    status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL'
        CHECK (status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EXPIRED', 'EXECUTED', 'FAILED')),
    payload JSONB NOT NULL,
    result JSONB,
    expires_at TIMESTAMPTZ NOT NULL,
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointment_proposals_patient_created
    ON appointment_proposals(patient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_appointment_proposals_pending_expiry
    ON appointment_proposals(expires_at) WHERE status = 'PENDING_APPROVAL';

ALTER TABLE appointment_proposals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS appointment_proposals_owner_select ON appointment_proposals;
CREATE POLICY appointment_proposals_owner_select
    ON appointment_proposals FOR SELECT TO authenticated
    USING (patient_id = auth.uid());
DROP POLICY IF EXISTS appointment_proposals_owner_insert ON appointment_proposals;
CREATE POLICY appointment_proposals_owner_insert
    ON appointment_proposals FOR INSERT TO authenticated
    WITH CHECK (patient_id = auth.uid());

ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS appointments_owner_select ON appointments;
CREATE POLICY appointments_owner_select
    ON appointments FOR SELECT TO authenticated
    USING (patient_id = auth.uid());

CREATE OR REPLACE FUNCTION book_appointment_slot(
    p_patient_id UUID,
    p_doctor_id UUID,
    p_slot_id UUID,
    p_reason TEXT DEFAULT NULL
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE
    v_slot doctor_availability%ROWTYPE;
    v_appointment appointments%ROWTYPE;
BEGIN
    SELECT * INTO v_slot
      FROM doctor_availability
     WHERE id = p_slot_id AND doctor_id = p_doctor_id
       AND status = 'AVAILABLE'
     FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Selected availability slot is no longer available.' USING ERRCODE = 'P0001';
    END IF;
    IF v_slot.start_time <= NOW() THEN
        RAISE EXCEPTION 'Cannot book an appointment in the past.' USING ERRCODE = 'P0001';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM patients WHERE id = p_patient_id) THEN
        RAISE EXCEPTION 'Patient profile does not exist.' USING ERRCODE = 'P0001';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM doctors WHERE id = p_doctor_id AND is_active) THEN
        RAISE EXCEPTION 'Doctor is not active.' USING ERRCODE = 'P0001';
    END IF;

    UPDATE doctor_availability
       SET status = 'BOOKED', updated_at = NOW()
     WHERE id = p_slot_id AND status = 'AVAILABLE';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Selected availability slot was concurrently reserved.' USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO appointments (
        patient_id, doctor_id, availability_id, start_time, end_time, status, reason
    ) VALUES (
        p_patient_id, p_doctor_id, p_slot_id, v_slot.start_time,
        v_slot.end_time, 'CONFIRMED', p_reason
    ) RETURNING * INTO v_appointment;
    RETURN jsonb_build_object('status', 'EXECUTED', 'appointment', to_jsonb(v_appointment));
END;
$$;

CREATE OR REPLACE FUNCTION cancel_appointment_atomic(
    p_appointment_id UUID,
    p_patient_id UUID,
    p_cancellation_window_minutes INTEGER DEFAULT 120
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE
    v_appointment appointments%ROWTYPE;
BEGIN
    SELECT * INTO v_appointment
      FROM appointments
     WHERE id = p_appointment_id AND patient_id = p_patient_id
     FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Appointment was not found for this patient.' USING ERRCODE = 'P0001';
    END IF;
    IF v_appointment.status NOT IN ('PENDING', 'CONFIRMED') THEN
        RAISE EXCEPTION 'Appointment is not cancellable in its current state.' USING ERRCODE = 'P0001';
    END IF;
    IF v_appointment.start_time < NOW() + make_interval(mins => p_cancellation_window_minutes) THEN
        RAISE EXCEPTION 'Appointment is within the cancellation window.' USING ERRCODE = 'P0001';
    END IF;

    UPDATE appointments SET status = 'CANCELLED', updated_at = NOW()
     WHERE id = p_appointment_id RETURNING * INTO v_appointment;
    IF v_appointment.availability_id IS NOT NULL THEN
        UPDATE doctor_availability SET status = 'AVAILABLE', updated_at = NOW()
         WHERE id = v_appointment.availability_id AND status = 'BOOKED';
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Appointment slot state is inconsistent.' USING ERRCODE = 'P0001';
        END IF;
    END IF;
    RETURN jsonb_build_object('status', 'EXECUTED', 'appointment', to_jsonb(v_appointment));
END;
$$;

CREATE OR REPLACE FUNCTION reschedule_appointment_atomic(
    p_appointment_id UUID,
    p_patient_id UUID,
    p_new_slot_id UUID
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE
    v_appointment appointments%ROWTYPE;
    v_new_slot doctor_availability%ROWTYPE;
BEGIN
    SELECT * INTO v_appointment FROM appointments
     WHERE id = p_appointment_id AND patient_id = p_patient_id
     FOR UPDATE;
    IF NOT FOUND OR v_appointment.status NOT IN ('PENDING', 'CONFIRMED') THEN
        RAISE EXCEPTION 'Appointment cannot be rescheduled.' USING ERRCODE = 'P0001';
    END IF;
    IF v_appointment.start_time <= NOW() THEN
        RAISE EXCEPTION 'Past appointments cannot be rescheduled.' USING ERRCODE = 'P0001';
    END IF;
    SELECT * INTO v_new_slot FROM doctor_availability
     WHERE id = p_new_slot_id AND doctor_id = v_appointment.doctor_id
       AND status = 'AVAILABLE'
     FOR UPDATE;
    IF NOT FOUND OR v_new_slot.start_time <= NOW() THEN
        RAISE EXCEPTION 'Replacement availability slot is unavailable.' USING ERRCODE = 'P0001';
    END IF;

    UPDATE doctor_availability SET status = 'BOOKED', updated_at = NOW()
     WHERE id = p_new_slot_id AND status = 'AVAILABLE';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Replacement slot was concurrently reserved.' USING ERRCODE = 'P0001';
    END IF;
    IF v_appointment.availability_id IS NOT NULL THEN
        UPDATE doctor_availability SET status = 'AVAILABLE', updated_at = NOW()
         WHERE id = v_appointment.availability_id AND status = 'BOOKED';
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Original appointment slot state is inconsistent.' USING ERRCODE = 'P0001';
        END IF;
    END IF;
    UPDATE appointments
       SET availability_id = p_new_slot_id,
           start_time = v_new_slot.start_time,
           end_time = v_new_slot.end_time,
           status = 'CONFIRMED', updated_at = NOW()
     WHERE id = p_appointment_id
     RETURNING * INTO v_appointment;
    RETURN jsonb_build_object('status', 'EXECUTED', 'appointment', to_jsonb(v_appointment));
END;
$$;

CREATE OR REPLACE FUNCTION reject_appointment_proposal(
    p_proposal_id UUID,
    p_patient_id UUID,
    p_version INTEGER
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE
    v_proposal appointment_proposals%ROWTYPE;
BEGIN
    SELECT * INTO v_proposal FROM appointment_proposals
     WHERE id = p_proposal_id AND patient_id = p_patient_id FOR UPDATE;
    IF NOT FOUND OR v_proposal.version <> p_version THEN
        RETURN jsonb_build_object('status', 'FAILED', 'error', 'Proposal was not found.');
    END IF;
    IF v_proposal.status <> 'PENDING_APPROVAL' THEN
        RETURN jsonb_build_object('status', v_proposal.status, 'error', 'Proposal is no longer pending.');
    END IF;
    IF v_proposal.expires_at <= NOW() THEN
        UPDATE appointment_proposals SET status = 'EXPIRED', updated_at = NOW()
         WHERE id = p_proposal_id;
        RETURN jsonb_build_object('status', 'EXPIRED', 'error', 'Proposal has expired.');
    END IF;
    UPDATE appointment_proposals SET status = 'REJECTED', updated_at = NOW()
     WHERE id = p_proposal_id;
    RETURN jsonb_build_object('status', 'REJECTED');
END;
$$;

CREATE OR REPLACE FUNCTION execute_appointment_proposal(
    p_proposal_id UUID,
    p_patient_id UUID,
    p_version INTEGER,
    p_cancellation_window_minutes INTEGER DEFAULT 120
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE
    v_proposal appointment_proposals%ROWTYPE;
    v_result JSONB;
BEGIN
    SELECT * INTO v_proposal FROM appointment_proposals
     WHERE id = p_proposal_id AND patient_id = p_patient_id FOR UPDATE;
    IF NOT FOUND OR v_proposal.version <> p_version THEN
        RETURN jsonb_build_object('status', 'FAILED', 'error', 'Proposal was not found.');
    END IF;
    IF v_proposal.status = 'EXECUTED' THEN
        RETURN COALESCE(v_proposal.result, jsonb_build_object('status', 'EXECUTED'));
    END IF;
    IF v_proposal.status <> 'PENDING_APPROVAL' THEN
        RETURN jsonb_build_object('status', v_proposal.status, 'error', 'Proposal is no longer pending.');
    END IF;
    IF v_proposal.expires_at <= NOW() THEN
        UPDATE appointment_proposals SET status = 'EXPIRED', updated_at = NOW()
         WHERE id = p_proposal_id;
        RETURN jsonb_build_object('status', 'EXPIRED', 'error', 'Proposal has expired.');
    END IF;

    UPDATE appointment_proposals SET status = 'APPROVED', approved_at = NOW(), updated_at = NOW()
     WHERE id = p_proposal_id;
    BEGIN
        IF v_proposal.action = 'BOOKING' THEN
            v_result := book_appointment_slot(
                p_patient_id,
                (v_proposal.payload->>'doctor_id')::uuid,
                (v_proposal.payload->>'slot_id')::uuid,
                v_proposal.payload->>'reason'
            );
        ELSIF v_proposal.action = 'CANCELLATION' THEN
            v_result := cancel_appointment_atomic(
                (v_proposal.payload->>'appointment_id')::uuid,
                p_patient_id,
                p_cancellation_window_minutes
            );
        ELSE
            v_result := reschedule_appointment_atomic(
                (v_proposal.payload->>'appointment_id')::uuid,
                p_patient_id,
                (v_proposal.payload->>'new_slot_id')::uuid
            );
        END IF;
    EXCEPTION WHEN OTHERS THEN
        UPDATE appointment_proposals
           SET status = 'FAILED',
               result = jsonb_build_object('status', 'FAILED', 'error', 'Appointment operation could not be completed.'),
               updated_at = NOW()
         WHERE id = p_proposal_id;
        RETURN jsonb_build_object('status', 'FAILED', 'error', 'Appointment operation could not be completed.');
    END;
    UPDATE appointment_proposals
       SET status = 'EXECUTED', result = v_result, executed_at = NOW(), updated_at = NOW()
     WHERE id = p_proposal_id;
    RETURN v_result;
END;
$$;

REVOKE ALL ON FUNCTION book_appointment_slot(UUID, UUID, UUID, TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION cancel_appointment_atomic(UUID, UUID, INTEGER) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION reschedule_appointment_atomic(UUID, UUID, UUID) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION reject_appointment_proposal(UUID, UUID, INTEGER) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION execute_appointment_proposal(UUID, UUID, INTEGER, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION book_appointment_slot(UUID, UUID, UUID, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION cancel_appointment_atomic(UUID, UUID, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION reschedule_appointment_atomic(UUID, UUID, UUID) TO service_role;
GRANT EXECUTE ON FUNCTION reject_appointment_proposal(UUID, UUID, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION execute_appointment_proposal(UUID, UUID, INTEGER, INTEGER) TO service_role;
