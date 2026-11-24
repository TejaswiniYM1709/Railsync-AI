-- SQLite schema reconstructed from the raw SQL used by the app.
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(15) UNIQUE,
    role VARCHAR(10) NOT NULL,
    account_status VARCHAR(10) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stations (
    station_id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_code VARCHAR(10) NOT NULL UNIQUE,
    station_name VARCHAR(100) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100),
    station_type VARCHAR(30),
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS routes (
    route_id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_name VARCHAR(100) NOT NULL,
    source_station_id INTEGER NOT NULL REFERENCES stations(station_id),
    destination_station_id INTEGER NOT NULL REFERENCES stations(station_id),
    distance_km NUMERIC(10, 2)
);

CREATE TABLE IF NOT EXISTS route_stops (
    route_stop_id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL REFERENCES routes(route_id),
    station_id INTEGER NOT NULL REFERENCES stations(station_id),
    stop_number INTEGER NOT NULL,
    distance_from_source NUMERIC(10, 2)
);

CREATE TABLE IF NOT EXISTS trains (
    train_id INTEGER PRIMARY KEY AUTOINCREMENT,
    train_number VARCHAR(20) NOT NULL UNIQUE,
    train_name VARCHAR(100) NOT NULL,
    train_type VARCHAR(30) NOT NULL,
    route_id INTEGER REFERENCES routes(route_id),
    total_capacity INTEGER,
    operating_status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    train_id INTEGER NOT NULL REFERENCES trains(train_id),
    journey_date DATE NOT NULL,
    schedule_status VARCHAR(20) DEFAULT 'SCHEDULED'
);

CREATE TABLE IF NOT EXISTS schedule_stops (
    schedule_stop_id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL REFERENCES schedules(schedule_id),
    route_stop_id INTEGER NOT NULL REFERENCES route_stops(route_stop_id),
    scheduled_arrival TIME,
    scheduled_departure TIME,
    estimated_arrival TIME,
    estimated_departure TIME,
    platform_id INTEGER
);

CREATE TABLE IF NOT EXISTS fare_rules (
    fare_id INTEGER PRIMARY KEY AUTOINCREMENT,
    train_type VARCHAR(30) NOT NULL,
    coach_type VARCHAR(30) NOT NULL,
    base_fare NUMERIC(10, 2) NOT NULL,
    fare_per_km NUMERIC(10, 2) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pnr_number VARCHAR(20) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    schedule_id INTEGER NOT NULL REFERENCES schedules(schedule_id),
    boarding_schedule_stop_id INTEGER NOT NULL REFERENCES schedule_stops(schedule_stop_id),
    alighting_schedule_stop_id INTEGER NOT NULL REFERENCES schedule_stops(schedule_stop_id),
    total_passengers INTEGER NOT NULL,
    total_fare NUMERIC(10, 2) NOT NULL,
    booking_status VARCHAR(20) DEFAULT 'CONFIRMED',
    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS booking_passengers (
    booking_passenger_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL REFERENCES bookings(booking_id),
    passenger_name VARCHAR(100) NOT NULL,
    age INTEGER NOT NULL,
    gender VARCHAR(10) NOT NULL,
    passenger_status VARCHAR(20) DEFAULT 'CONFIRMED'
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL REFERENCES bookings(booking_id),
    transaction_reference VARCHAR(50) NOT NULL UNIQUE,
    payment_method VARCHAR(20) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    payment_status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL REFERENCES bookings(booking_id),
    ticket_reference VARCHAR(50) NOT NULL UNIQUE,
    ticket_status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS qr_tokens (
    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_passenger_id INTEGER NOT NULL REFERENCES booking_passengers(booking_passenger_id),
    token_reference VARCHAR(50) NOT NULL UNIQUE,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_time TIMESTAMP NOT NULL,
    token_status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS delay_records (
    delay_id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL REFERENCES schedules(schedule_id),
    station_id INTEGER NOT NULL REFERENCES stations(station_id),
    delay_minutes INTEGER NOT NULL,
    reason VARCHAR(255),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS staff (
    staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id),
    station_id INTEGER REFERENCES stations(station_id),
    employment_status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS platforms (
    platform_id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id INTEGER NOT NULL REFERENCES stations(station_id),
    platform_number VARCHAR(10) NOT NULL,
    platform_status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS platform_allocations (
    allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_stop_id INTEGER NOT NULL REFERENCES schedule_stops(schedule_stop_id),
    platform_id INTEGER NOT NULL REFERENCES platforms(platform_id),
    arrival_time TIME,
    departure_time TIME,
    allocation_status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS platform_conflicts (
    conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_id INTEGER NOT NULL REFERENCES platforms(platform_id),
    allocation_id_1 INTEGER NOT NULL REFERENCES platform_allocations(allocation_id),
    allocation_id_2 INTEGER NOT NULL REFERENCES platform_allocations(allocation_id),
    conflict_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolution_status VARCHAR(20) DEFAULT 'OPEN',
    resolution_notes VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS ticket_verifications (
    verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id INTEGER REFERENCES qr_tokens(token_id),
    staff_id INTEGER REFERENCES staff(staff_id),
    verification_status VARCHAR(20),
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entry_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id INTEGER REFERENCES qr_tokens(token_id),
    station_id INTEGER REFERENCES stations(station_id),
    staff_id INTEGER REFERENCES staff(staff_id),
    entry_status VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id INTEGER REFERENCES qr_tokens(token_id),
    station_id INTEGER REFERENCES stations(station_id),
    staff_id INTEGER REFERENCES staff(staff_id),
    exit_status VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS platform_access_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id INTEGER REFERENCES qr_tokens(token_id),
    platform_id INTEGER REFERENCES platforms(platform_id),
    staff_id INTEGER REFERENCES staff(staff_id),
    access_status VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    booking_id INTEGER REFERENCES bookings(booking_id),
    station_id INTEGER REFERENCES stations(station_id),
    complaint_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    complaint_status VARCHAR(20) DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- Indexes for the join and filter paths used by the app.
CREATE INDEX IF NOT EXISTS idx_schedules_journey_date ON schedules(journey_date);
CREATE INDEX IF NOT EXISTS idx_schedule_stops_schedule ON schedule_stops(schedule_id);
CREATE INDEX IF NOT EXISTS idx_route_stops_route ON route_stops(route_id);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_booking_passengers_booking ON booking_passengers(booking_id);
CREATE INDEX IF NOT EXISTS idx_payments_booking ON payments(booking_id);
CREATE INDEX IF NOT EXISTS idx_tickets_booking ON tickets(booking_id);
CREATE INDEX IF NOT EXISTS idx_qr_tokens_passenger ON qr_tokens(booking_passenger_id);
CREATE INDEX IF NOT EXISTS idx_delay_records_schedule ON delay_records(schedule_id);
CREATE INDEX IF NOT EXISTS idx_platform_allocations_stop ON platform_allocations(schedule_stop_id);
CREATE INDEX IF NOT EXISTS idx_staff_user ON staff(user_id);
