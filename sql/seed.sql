INSERT INTO customers (name, email, phone) VALUES
    ('Amara Okafor', 'amara@example.com',  '555-0101'),
    ('Daniel Reyes', 'daniel@example.com', '555-0102'),
    ('Grace Kim',    'grace@example.com',  NULL);

INSERT INTO locations (name, city, state) VALUES
    ('Chicago Warehouse', 'Chicago',    'IL'),
    ('Louisville Hub',    'Louisville', 'KY'),
    ('Memphis Hub',       'Memphis',    'TN'),
    ('Atlanta Station',   'Atlanta',    'GA');

INSERT INTO shipments (customer_id, origin_location_id, destination_location_id) VALUES
    (1, 1, 4),
    (2, 1, 3);

INSERT INTO packages (tracking_id, shipment_id, weight_kg, package_metadata, current_status) VALUES
    ('TRK1001', 1, 2.50, '{"fragile": true, "requires_signature": true}', 'Delivered'),
    ('TRK1002', 1, 1.20, '{"fragile": false, "requires_signature": false}', 'In Transit'),
    ('TRK1003', 2, 8.00, '{"fragile": false, "requires_signature": true}', 'Label Created');

INSERT INTO tracking_events (package_id, location_id, status, event_timestamp) VALUES
    (1, 1, 'Label Created',    '2026-10-20 08:00'),
    (1, 1, 'Picked Up',        '2026-10-20 11:00'),
    (1, 2, 'In Transit',       '2026-10-21 02:30'),
    (1, 4, 'Out for Delivery', '2026-10-22 07:15'),
    (1, 4, 'Delivered',        '2026-10-22 13:40'),
    (2, 1, 'Label Created',    '2026-10-20 08:00'),
    (2, 1, 'Picked Up',        '2026-10-20 11:00'),
    (2, 2, 'In Transit',       '2026-10-21 02:45'),
    (3, 1, 'Label Created',    '2026-10-25 09:00');