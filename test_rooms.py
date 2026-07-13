"""
Test Rooms API - Save to: test_rooms.py (in project root)
Run with: python test_rooms.py
"""
import requests
import json

print("\n" + "="*60)
print("TESTING ROOMS API - STEP 3")
print("="*60)

# Test 1: Get all rooms
print("\n1️⃣  GET ALL ROOMS:")
print("-" * 60)
try:
    response = requests.get("http://localhost:5000/api/rooms")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Rooms found: {data.get('count', 0)}")
    for room in data.get('rooms', []):
        print(f"  ✓ {room['name']} (Type: {room['type']}, Capacity: {room['capacity']})")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Get single room with occupancy
print("\n2️⃣  GET SINGLE ROOM (ID=1):")
print("-" * 60)
try:
    response = requests.get("http://localhost:5000/api/rooms/1")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Room Name: {data.get('name')}")
        print(f"Capacity: {data.get('capacity')}")
        print(f"Current Occupancy: {data.get('current_occupancy', 0)}")
        print(f"Available Seats: {data.get('available_seats', 0)}")
        print(f"Occupancy %: {data.get('occupancy_percentage', 0):.1f}%")
    else:
        print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Get room occupancy
print("\n3️⃣  GET ROOM OCCUPANCY (ID=1):")
print("-" * 60)
try:
    response = requests.get("http://localhost:5000/api/rooms/1/occupancy")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Get occupancy logs
print("\n4️⃣  GET OCCUPANCY LOGS:")
print("-" * 60)
try:
    response = requests.get("http://localhost:5000/api/rooms/logs/all")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total logs: {data.get('count', 0)}")
    if data.get('logs'):
        print("Sample logs:")
        for log in data.get('logs', [])[:3]:
            print(f"  - User {log['user_id']} in Room {log['room_id']}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*60)
print("✅ STEP 3 TESTING COMPLETE!")
print("="*60 + "\n")
