-- PHONIX Platform - Test Users SQL Insert Script
-- PostgreSQL / SQLite'da ishlatish uchun
-- Django ORM'ni qo'llash tavsiyalangan, lekin database'ga to'g'ridan-to'g'ri access uchun

-- Admin user
INSERT INTO users_user (
    id, 
    phone, 
    email, 
    password, 
    first_name, 
    last_name, 
    patronymic, 
    role, 
    affiliation, 
    is_active, 
    is_staff, 
    is_superuser, 
    date_joined, 
    last_login,
    gamification_level,
    gamification_badges,
    gamification_points
) VALUES (
    '550e8400-e29b-41d4-a716-446655440001',
    '998901001001',
    'admin@ilmiyfaoliyat.uz',
    'pbkdf2_sha256$720000$Hash$Hash==',  -- Django password (use manage.py create_user)
    'Admin',
    'Bosh',
    'Superuser',
    'super_admin',
    'Phoenix Scientific Platform',
    TRUE,
    TRUE,
    TRUE,
    datetime('now'),
    datetime('now'),
    'Administrator',
    '["Administrator", "Verifikatsiyalangan"]',
    500
);

-- Editor (Journal Admin) user
INSERT INTO users_user (
    id,
    phone,
    email,
    password,
    first_name,
    last_name,
    patronymic,
    role,
    affiliation,
    is_active,
    is_staff,
    is_superuser,
    date_joined,
    last_login,
    gamification_level,
    gamification_badges,
    gamification_points
) VALUES (
    '550e8400-e29b-41d4-a716-446655440002',
    '998901001002',
    'editor@ilmiyfaoliyat.uz',
    'pbkdf2_sha256$720000$Hash$Hash==',  -- Django password
    'Tahrirchi',
    'Bosh',
    'Admin',
    'journal_admin',
    'Phoenix Scientific Platform',
    TRUE,
    TRUE,
    FALSE,
    datetime('now'),
    datetime('now'),
    'Administrator',
    '["Administrator", "Verifikatsiyalangan"]',
    500
);

-- Reviewer user
INSERT INTO users_user (
    id,
    phone,
    email,
    password,
    first_name,
    last_name,
    patronymic,
    role,
    affiliation,
    is_active,
    is_staff,
    is_superuser,
    date_joined,
    last_login,
    gamification_level,
    gamification_badges,
    gamification_points,
    specializations,
    reviews_completed,
    average_review_time,
    acceptance_rate
) VALUES (
    '550e8400-e29b-41d4-a716-446655440003',
    '998901001003',
    'reviewer1@ilmiyfaoliyat.uz',
    'pbkdf2_sha256$720000$Hash$Hash==',
    'Reviewer',
    'Birinchi',
    'Ilmiy',
    'reviewer',
    'Tashkent State University',
    TRUE,
    FALSE,
    FALSE,
    datetime('now'),
    datetime('now'),
    'Yangi Reviewer',
    '["Yangi Reviewer", "Ulug\'bek"]',
    100,
    '["Computer Science", "Information Technology"]',
    0,
    0.0,
    0.0
);

-- Author user
INSERT INTO users_user (
    id,
    phone,
    email,
    password,
    first_name,
    last_name,
    patronymic,
    role,
    affiliation,
    is_active,
    is_staff,
    is_superuser,
    date_joined,
    last_login,
    gamification_level,
    gamification_badges,
    gamification_points
) VALUES (
    '550e8400-e29b-41d4-a716-446655440005',
    '998901001005',
    'author1@ilmiyfaoliyat.uz',
    'pbkdf2_sha256$720000$Hash$Hash==',
    'Muallif',
    'Birinchi',
    'Ilmiy',
    'author',
    'Tashkent Institute of Technology',
    TRUE,
    FALSE,
    FALSE,
    datetime('now'),
    datetime('now'),
    'Yangi Muallif',
    '["Yangi Muallif", "Innovator"]',
    0
);

-- NOTE: Django password hashing'i uslubini ishlatish uchun
-- Python'da:
-- from django.contrib.auth.hashers import make_password
-- password_hash = make_password('Admin@123456')
-- Password hashing format: pbkdf2_sha256$iterations$salt$hash

-- SQL'da qayta ishlatish:
-- UPDATE users_user SET password = 'pbkdf2_sha256$...' WHERE email = 'admin@ilmiyfaoliyat.uz'
