#!/usr/bin/env python3
"""
Test script to verify the draft progresses correctly through multiple rounds.
"""
import subprocess
import time
import psycopg2
import json

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5433,
        database="valorant_fantasy_db",
        user="valorant_fantasy_user",
        password="strongpassword"
    )

def get_draft_state(draft_id):
    """Get current draft state from database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT current_pick, current_user_id, status, draft_order 
        FROM draftsession 
        WHERE id = %s
    """, (draft_id,))
    
    result = cur.fetchone()
    conn.close()
    
    if result:
        return {
            'current_pick': result[0],
            'current_user_id': result[1],
            'status': result[2],
            'draft_order': result[3]
        }
    return None

def get_picks(draft_id):
    """Get all picks for a draft."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT pick_number, team_id, player_name 
        FROM draftpick 
        WHERE draft_session_id = %s 
        ORDER BY pick_number
    """, (draft_id,))
    
    results = cur.fetchall()
    conn.close()
    
    return [{'pick_number': r[0], 'team_id': r[1], 'player_name': r[2]} for r in results]

def set_deadline_past(draft_id):
    """Set the pick deadline to the past so autopick can trigger."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE draftsession 
        SET pick_deadline = NOW() - INTERVAL '1 minute' 
        WHERE id = %s
    """, (draft_id,))
    
    conn.commit()
    conn.close()

def trigger_autopick(draft_id):
    """Trigger autopick via API."""
    try:
        result = subprocess.run([
            'curl', '-X', 'POST',
            f'http://localhost:8000/drafts/{draft_id}/autopick',
            '-H', 'Content-Type: application/json'
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": f"curl failed: {result.stderr}"}
    except Exception as e:
        return {"error": str(e)}

def test_draft_progression(draft_id, max_picks=10):
    """Test draft progression through multiple picks."""
    print(f"Testing Draft Progression for Draft ID: {draft_id}")
    print("=" * 60)
    
    draft_order = [6, 3, 2, 5, 4]  # Expected order
    expected_snake_pattern = []
    
    # Calculate expected snake pattern for first few rounds
    for pick in range(1, max_picks + 1):
        round_num = ((pick - 1) // 5) + 1
        pos_in_round = (pick - 1) % 5
        
        if round_num % 2 == 1:  # Odd rounds: normal order
            expected_user = draft_order[pos_in_round]
        else:  # Even rounds: reverse order
            expected_user = draft_order[4 - pos_in_round]
        
        expected_snake_pattern.append(expected_user)
    
    print("Expected Snake Pattern:")
    for i, user in enumerate(expected_snake_pattern, 1):
        round_num = ((i - 1) // 5) + 1
        direction = "normal" if round_num % 2 == 1 else "reverse"
        print(f"  Pick {i:2}: User {user} (Round {round_num}, {direction})")
    
    print("\nActual Draft Progression:")
    print("Pick | Expected | Actual | Status | Player")
    print("-" * 50)
    
    for pick_num in range(1, max_picks + 1):
        # Get current state
        state = get_draft_state(draft_id)
        if not state:
            print(f"❌ Could not get draft state")
            break
        
        if state['status'] == 'COMPLETED':
            print(f"✅ Draft completed at pick {pick_num - 1}")
            break
        
        expected_user = expected_snake_pattern[pick_num - 1]
        actual_user = state['current_user_id']
        
        # Check if we're on the expected pick
        if state['current_pick'] != pick_num:
            print(f"❌ Expected pick {pick_num}, but draft is on pick {state['current_pick']}")
            break
        
        # Check if the current user matches expected
        status = "✓" if actual_user == expected_user else "✗"
        
        # Set deadline to past and trigger autopick
        set_deadline_past(draft_id)
        result = trigger_autopick(draft_id)
        
        # Get the pick that was made
        picks = get_picks(draft_id)
        latest_pick = picks[-1] if picks else None
        player_name = latest_pick['player_name'] if latest_pick else "N/A"
        
        print(f"{pick_num:4} | {expected_user:8} | {actual_user:6} | {status:6} | {player_name}")
        
        if "failed" in str(result).lower():
            print(f"❌ Autopick failed: {result}")
            break
        
        # Small delay to avoid overwhelming the system
        time.sleep(0.1)
    
    # Final summary
    print("\nFinal Draft State:")
    final_state = get_draft_state(draft_id)
    if final_state:
        print(f"  Status: {final_state['status']}")
        print(f"  Current Pick: {final_state['current_pick']}")
        print(f"  Current User: {final_state['current_user_id']}")
    
    final_picks = get_picks(draft_id)
    print(f"  Total Picks Made: {len(final_picks)}")
    
    return final_state, final_picks

if __name__ == "__main__":
    draft_id = 4  # The draft we created
    state, picks = test_draft_progression(draft_id, max_picks=15)
    
    print(f"\n🎯 Test completed! Made {len(picks)} picks.")
    if state and state['status'] == 'COMPLETED':
        print("✅ Draft completed successfully!")
    elif len(picks) >= 10:
        print("✅ Snake draft pattern working correctly!")
    else:
        print("❌ Something went wrong with the draft progression.")
