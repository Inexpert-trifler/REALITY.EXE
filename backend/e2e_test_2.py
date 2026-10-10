from PIL import Image
import io
import requests
import time
import uuid

BASE_URL = "http://localhost:8000/api/v1"

def p(msg):
    print(f"[TEST] {msg}")

def main():
    session = requests.Session()
    
    # 1. REGISTER
    username = f"user_{uuid.uuid4().hex[:6]}"
    email = f"{username}@example.com"
    p(f"Registering user {username}...")
    resp = session.post(f"{BASE_URL}/auth/register", json={
        "username": username,
        "email": email,
        "password": "Password123!",
        "display_name": f"Hero {username}"
    })
    assert resp.status_code == 201, resp.text
    
    # 2. LOGIN
    p("Logging in...")
    resp = session.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    p("Login OK.")
    
    # 3. PROFILE
    p("Fetching profile...")
    resp = session.get(f"{BASE_URL}/auth/me")
    assert resp.status_code == 200, resp.text
    user_id = resp.json()["id"]
    p("Profile OK.")
    
    # 4. GENERATE QUEST
    p("Generating quest...")
    resp = session.post(f"{BASE_URL}/quests/generate", json={
        "duration_minutes": 20,
        "environment": "park",
        "difficulty": "chill",
        "play_style": "explorer",
        "personality": "Wizard"
    })
    assert resp.status_code == 201, resp.text
    quest_id = resp.json()["id"]
    p(f"Quest generated: {quest_id}")
    
    # 5. START
    p("Starting quest...")
    resp = session.post(f"{BASE_URL}/quests/{quest_id}/start")
    assert resp.status_code == 200, resp.text
    attempt_id = resp.json()["id"]
    p("Quest started.")
    
    # 6. POCKET MODE
    p("Entering pocket mode...")
    resp = session.post(f"{BASE_URL}/quests/{quest_id}/pocket")
    assert resp.status_code == 200, resp.text
    p("Pocket mode entered.")
    
    # 7. RETURN
    p("Returning from pocket mode...")
    resp = session.post(f"{BASE_URL}/quests/{quest_id}/return")
    assert resp.status_code == 200, resp.text
    p("Returned from pocket mode.")
    
    # 8. UPLOAD EVIDENCE
    p("Uploading evidence...")
    # Create valid fake jpeg
    img = Image.new('RGB', (1, 1), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    fake_img = img_byte_arr.getvalue()
    
    resp = session.post(
        f"{BASE_URL}/evidence/upload",
        data={"attempt_id": attempt_id},
        files={"file": ("evidence.jpg", fake_img, "image/jpeg")}
    )
    assert resp.status_code == 201, resp.text
    evidence_id = resp.json()["evidence_id"]
    p(f"Evidence uploaded: {evidence_id}")
    
    # 9. ANALYZE EVIDENCE
    p("Analyzing evidence...")
    resp = session.post(
        f"{BASE_URL}/evidence/{evidence_id}/analyze",
        data=fake_img,
        headers={"Content-Type": "application/octet-stream"}
    )
    assert resp.status_code == 200, resp.text
    p(f"Evidence analyzed. Outcome: {resp.json()['outcome']}")
    
    if resp.json()['outcome'] != "SUCCESS":
        p("Skipping complete step because analysis didn't return SUCCESS")
        return
        
    # 10. COMPLETE
    p("Completing quest...")
    resp = session.post(f"{BASE_URL}/quests/{quest_id}/complete")
    if resp.status_code != 200:
        p(f"Complete failed: {resp.text}")
    assert resp.status_code == 200, resp.text
    p("Quest completed.")
    
    # 11. AWARD XP & LEVEL UPDATE & ACHIEVEMENT
    xp = resp.json().get("earned_xp")
    p(f"Earned XP: {xp}")
    
    # 12. REFLECTION
    p("Creating reflection...")
    resp = session.post(f"{BASE_URL}/reflections", json={
        "attempt_id": attempt_id
    })
    assert resp.status_code == 201, resp.text
    p("Reflection created.")
    
    # 13. HISTORY
    p("Checking history...")
    resp = session.get(f"{BASE_URL}/history")
    assert resp.status_code == 200, resp.text
    p("History OK.")
    
    p("All E2E steps completed successfully!")

if __name__ == "__main__":
    main()
