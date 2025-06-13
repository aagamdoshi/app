import requests
import unittest
import sys
from datetime import datetime

class BadDeedsAPITester:
    def __init__(self, base_url="https://bc9462b8-3b71-4834-92ff-60c33acd210b.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                return success, response.json() if response.content else {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                return success, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_api_root(self):
        """Test API root endpoint"""
        return self.run_test(
            "API Root",
            "GET",
            "",
            200
        )

    def test_record_bad_deed(self, notes=None):
        """Test recording a bad deed"""
        data = {"notes": notes} if notes else {}
        return self.run_test(
            "Record Bad Deed",
            "POST",
            "bad-deed",
            200,
            data=data
        )

    def test_get_today_stats(self):
        """Test getting today's stats"""
        return self.run_test(
            "Get Today's Stats",
            "GET",
            "stats/today",
            200
        )

    def test_get_recent_stats(self, days=7):
        """Test getting recent stats"""
        return self.run_test(
            "Get Recent Stats",
            "GET",
            f"stats/recent?days={days}",
            200
        )

    def test_get_bad_deeds(self, limit=10):
        """Test getting bad deeds list"""
        return self.run_test(
            "Get Bad Deeds List",
            "GET",
            f"bad-deeds?limit={limit}",
            200
        )
        
    def test_get_day_of_week_analysis(self):
        """Test getting day-of-week pattern analysis"""
        return self.run_test(
            "Get Day-of-Week Analysis",
            "GET",
            "stats/day-of-week",
            200
        )
        
    def test_get_streak_analysis(self):
        """Test getting streak analysis"""
        return self.run_test(
            "Get Streak Analysis",
            "GET",
            "stats/streaks",
            200
        )
        
    def test_get_monthly_stats(self, months=6):
        """Test getting monthly statistics"""
        return self.run_test(
            "Get Monthly Stats",
            "GET",
            f"stats/monthly?months={months}",
            200
        )

def main():
    # Setup
    tester = BadDeedsAPITester()
    
    # Run tests
    print("🧪 Starting Bad Deeds API Tests 🧪")
    print("==================================")
    
    # Test API root
    tester.test_api_root()
    
    # Test getting today's stats (initial)
    success, initial_stats = tester.test_get_today_stats()
    if success:
        initial_count = initial_stats.get('count', 0)
        print(f"Initial count for today: {initial_count}")
    
    # Test recording a bad deed
    success, response = tester.test_record_bad_deed()
    if success:
        print(f"Successfully recorded bad deed with ID: {response.get('id', 'unknown')}")
    
    # Test getting today's stats (after recording)
    success, updated_stats = tester.test_get_today_stats()
    if success:
        updated_count = updated_stats.get('count', 0)
        print(f"Updated count for today: {updated_count}")
        
        if 'initial_count' in locals() and updated_count > initial_count:
            print("✅ Count increased after recording bad deed")
        else:
            print("❌ Count did not increase after recording bad deed")
    
    # Test getting recent stats
    success, recent_stats = tester.test_get_recent_stats()
    if success:
        stats = recent_stats.get('stats', [])
        print(f"Received stats for {len(stats)} days")
        
        if len(stats) == 7:
            print("✅ Received correct number of days (7)")
        else:
            print(f"❌ Expected 7 days, got {len(stats)}")
    
    # Test getting bad deeds list
    success, bad_deeds = tester.test_get_bad_deeds()
    if success:
        print(f"Retrieved {len(bad_deeds)} bad deeds")
    
    # Test new analytics endpoints
    print("\n🧪 Testing New Analytics Endpoints 🧪")
    print("====================================")
    
    # Test day-of-week analysis
    success, day_analysis = tester.test_get_day_of_week_analysis()
    if success:
        day_data = day_analysis.get('day_analysis', [])
        insights = day_analysis.get('insights', [])
        print(f"Retrieved day-of-week analysis for {len(day_data)} days")
        print(f"Found {len(insights)} insights")
        
        if len(day_data) == 7:
            print("✅ Received analysis for all 7 days of the week")
        else:
            print(f"❌ Expected 7 days, got {len(day_data)}")
    
    # Test streak analysis
    success, streak_data = tester.test_get_streak_analysis()
    if success:
        current_streak = streak_data.get('current_streak', {}).get('days', 0)
        longest_streak = streak_data.get('longest_streak', {}).get('days', 0)
        print(f"Current streak: {current_streak} days")
        print(f"Longest streak: {longest_streak} days")
    
    # Test monthly stats
    success, monthly_data = tester.test_get_monthly_stats()
    if success:
        monthly_stats = monthly_data.get('monthly_stats', [])
        trend = monthly_data.get('trend', 'unknown')
        print(f"Retrieved monthly stats for {len(monthly_stats)} months")
        print(f"Overall trend: {trend}")
        
        if len(monthly_stats) == 6:
            print("✅ Received stats for 6 months as requested")
        else:
            print(f"❌ Expected 6 months, got {len(monthly_stats)}")
    
    # Print results
    print("\n📊 Test Results 📊")
    print("=================")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run} ({tester.tests_passed/tester.tests_run*100:.1f}%)")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
