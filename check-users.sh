#!/bin/bash
# Check users in database and test login

echo "=== Checking Users in Database ==="
echo ""

cd /phonix/backend
source venv/bin/activate

# Check if users exist
echo "1. Checking users in database..."
python manage.py shell << 'EOF'
from apps.users.models import User
users = User.objects.all()
print(f"Total users: {users.count()}")
if users.exists():
    print("\nUsers list:")
    for user in users[:10]:  # Show first 10 users
        print(f"  - ID: {user.id}, Phone: {user.phone}, Email: {user.email}, Role: {user.role}, Active: {user.is_active}")
        if user.phone:
            # Show phone formats
            print(f"    Phone formats: +{user.phone}, {user.phone}")
else:
    print("No users found in database")
EOF

echo ""
echo "2. Testing login with a real user (if exists)..."
echo "   Please provide a valid phone number and password"
echo ""

# Test login endpoint
echo "3. Testing login endpoint structure..."
curl -X POST http://127.0.0.1:8003/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"phone":"998901234567","password":"test123"}' \
  2>&1 | head -20

echo ""
echo "=== Check Complete ==="
echo ""
echo "To test login, use a real user's phone number and password from the database"
