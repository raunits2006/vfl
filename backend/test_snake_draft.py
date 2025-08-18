#!/usr/bin/env python3
"""
Test script to verify snake draft logic works correctly.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.draft_utils import calculate_snake_draft_user

def test_snake_draft_logic():
    """Test the snake draft logic with a simple example."""
    
    # Test with 3 teams: [A=1, B=2, C=3], 2 rounds (6 total picks)
    draft_order = [1, 2, 3]  # User IDs: A, B, C
    total_picks = 6  # 3 teams × 2 players each
    
    print("Testing Snake Draft Logic")
    print("=" * 40)
    print(f"Draft Order: {draft_order}")
    print(f"Total Picks: {total_picks}")
    print()
    
    expected_pattern = [
        (1, "Round 1: A -> B -> C"),
        (2, ""),
        (3, ""),
        (3, "Round 2: C -> B -> A (reversed)"),
        (2, ""),
        (1, "")
    ]
    
    print("Pick | Expected User | Actual User | Status")
    print("-" * 45)
    
    all_correct = True
    for pick_num in range(1, total_picks + 1):
        expected_user = expected_pattern[pick_num - 1][0]
        comment = expected_pattern[pick_num - 1][1]
        
        try:
            actual_user, _ = calculate_snake_draft_user(pick_num, draft_order, total_picks)
            status = "✓" if actual_user == expected_user else "✗"
            if actual_user != expected_user:
                all_correct = False
            
            print(f"{pick_num:4} | {expected_user:12} | {actual_user:11} | {status:6} {comment}")
        except Exception as e:
            print(f"{pick_num:4} | {expected_user:12} | ERROR       | ✗     {e}")
            all_correct = False
    
    print()
    if all_correct:
        print("✅ All tests passed! Snake draft logic is working correctly.")
    else:
        print("❌ Some tests failed. Snake draft logic needs fixing.")
    
    return all_correct

def test_larger_draft():
    """Test with a larger draft scenario."""
    print("\nTesting Larger Draft (5 teams, 3 rounds)")
    print("=" * 50)
    
    draft_order = [1, 2, 3, 4, 5]  # 5 teams
    total_picks = 15  # 5 teams × 3 players each
    
    print("Pick | User | Round Info")
    print("-" * 30)
    
    for pick_num in range(1, total_picks + 1):
        try:
            user_id, _ = calculate_snake_draft_user(pick_num, draft_order, total_picks)
            round_num = ((pick_num - 1) // 5) + 1
            pos_in_round = ((pick_num - 1) % 5) + 1
            direction = "normal" if round_num % 2 == 1 else "reverse"
            
            print(f"{pick_num:4} | {user_id:4} | Round {round_num}, Pos {pos_in_round} ({direction})")
        except Exception as e:
            print(f"{pick_num:4} | ERR  | {e}")
    
    print()

if __name__ == "__main__":
    success = test_snake_draft_logic()
    test_larger_draft()
    
    if success:
        print("🎉 Snake draft logic is ready for production!")
    else:
        print("🔧 Snake draft logic needs debugging.")
        sys.exit(1)
