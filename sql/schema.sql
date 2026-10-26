DROP TABLE IF EXISTS tracking_events, packages, shipments, locations, customers;

CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,     -- the SERIAL will allow auto increment pri-key, here the alternative and the most practical way to do it would GENERATED ALWAYS AS IDENTITY
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    phone       VARCHAR(20)
);

CREATE TABLE locations (
    location_id SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    city        VARCHAR(100) NOT NULL,
    state       CHAR(2)      NOT NULL
);

CREATE TABLE shipments (
    shipment_id             SERIAL PRIMARY KEY,
    customer_id             INT NOT NULL REFERENCES customers(customer_id),
    origin_location_id      INT NOT NULL REFERENCES locations(location_id),
    destination_location_id INT NOT NULL REFERENCES locations(location_id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE packages (
    package_id       SERIAL PRIMARY KEY,
    tracking_id      VARCHAR(20)  NOT NULL UNIQUE,
    shipment_id      INT          NOT NULL REFERENCES shipments(shipment_id),
    weight_kg        NUMERIC(6,2) NOT NULL CHECK (weight_kg > 0),
    package_metadata JSONB        NOT NULL DEFAULT '{}',
    current_status   VARCHAR(30)  NOT NULL DEFAULT 'Label Created'
);

CREATE TABLE tracking_events (
    event_id        SERIAL PRIMARY KEY,
    package_id      INT         NOT NULL REFERENCES packages(package_id),
    location_id     INT         NOT NULL REFERENCES locations(location_id),
    status          VARCHAR(30) NOT NULL CHECK (status IN
                        ('Label Created', 'Picked Up', 'In Transit',
                         'Out for Delivery', 'Delivered', 'Exception')),
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);