-- Supabase / PostgreSQL Initial Domain Schema Migration
-- Migration 001: 001_initial_domain_schema.sql

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Patients Table
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_user_id VARCHAR(255) UNIQUE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for external user lookups & email
CREATE INDEX IF NOT EXISTS idx_patients_external_user_id ON patients(external_user_id);
CREATE INDEX IF NOT EXISTS idx_patients_email ON patients(email);

-- 2. Doctors Table
CREATE TABLE IF NOT EXISTS doctors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    bio TEXT,
    clinic_name VARCHAR(255),
    location VARCHAR(255),
    consultation_duration INT NOT NULL DEFAULT 30, -- Duration in minutes
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for doctor activity searches
CREATE INDEX IF NOT EXISTS idx_doctors_is_active ON doctors(is_active);

-- 3. Specialties Table
CREATE TABLE IF NOT EXISTS specialties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for searching specialties by name
CREATE INDEX IF NOT EXISTS idx_specialties_name ON specialties(name);

-- 4. Doctor Specialties Junction Table (Many-to-Many)
CREATE TABLE IF NOT EXISTS doctor_specialties (
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
    specialty_id UUID NOT NULL REFERENCES specialties(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (doctor_id, specialty_id)
);

CREATE INDEX IF NOT EXISTS idx_doctor_specialties_doctor_id ON doctor_specialties(doctor_id);
CREATE INDEX IF NOT EXISTS idx_doctor_specialties_specialty_id ON doctor_specialties(specialty_id);

-- 5. Doctor Availability Table
CREATE TABLE IF NOT EXISTS doctor_availability (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'AVAILABLE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_availability_time_order CHECK (start_time < end_time),
    CONSTRAINT chk_availability_status CHECK (status IN ('AVAILABLE', 'BOOKED', 'BLOCKED'))
);

-- Indexes for slot search patterns (doctor + time range + status)
CREATE INDEX IF NOT EXISTS idx_doctor_availability_doctor_id ON doctor_availability(doctor_id);
CREATE INDEX IF NOT EXISTS idx_doctor_availability_start_time ON doctor_availability(start_time);
CREATE INDEX IF NOT EXISTS idx_doctor_availability_search ON doctor_availability(doctor_id, start_time, status);

-- 6. Appointments Table
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_appointment_time_order CHECK (start_time < end_time),
    CONSTRAINT chk_appointment_status CHECK (
        status IN ('PENDING', 'CONFIRMED', 'CANCELLED', 'RESCHEDULED', 'COMPLETED', 'NO_SHOW', 'EXPIRED')
    )
);

-- Foreign key indexes & status/start_time query indexes
CREATE INDEX IF NOT EXISTS idx_appointments_patient_id ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor_id ON appointments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_appointments_start_time ON appointments(start_time);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);

-- Database-level exclusion / unique constraint to prevent overlapping appointments for the same doctor
-- Exclusion constraint requires btree_gist extension in PostgreSQL
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE appointments
    ADD CONSTRAINT prevent_doctor_overlapping_appointments
    EXCLUDE USING gist (
        doctor_id WITH =,
        tstzrange(start_time, end_time, '[)') WITH &&
    ) WHERE (status IN ('PENDING', 'CONFIRMED'));
