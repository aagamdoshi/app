import { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [todayCount, setTodayCount] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [recentStats, setRecentStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dayOfWeekData, setDayOfWeekData] = useState(null);
  const [streakData, setStreakData] = useState(null);
  const [monthlyData, setMonthlyData] = useState(null);

  // Fetch today's count
  const fetchTodayStats = async () => {
    try {
      const response = await axios.get(`${API}/stats/today`);
      setTodayCount(response.data.count);
    } catch (error) {
      console.error("Error fetching today's stats:", error);
    }
  };

  // Fetch recent stats for the mini trend
  const fetchRecentStats = async () => {
    try {
      const response = await axios.get(`${API}/stats/recent?days=7`);
      setRecentStats(response.data.stats);
    } catch (error) {
      console.error("Error fetching recent stats:", error);
    }
  };

  // Fetch day-of-week analysis
  const fetchDayOfWeekData = async () => {
    try {
      const response = await axios.get(`${API}/stats/day-of-week`);
      setDayOfWeekData(response.data);
    } catch (error) {
      console.error("Error fetching day-of-week data:", error);
    }
  };

  // Fetch streak analysis
  const fetchStreakData = async () => {
    try {
      const response = await axios.get(`${API}/stats/streaks`);
      setStreakData(response.data);
    } catch (error) {
      console.error("Error fetching streak data:", error);
    }
  };

  // Fetch monthly data
  const fetchMonthlyData = async () => {
    try {
      const response = await axios.get(`${API}/stats/monthly?months=6`);
      setMonthlyData(response.data);
    } catch (error) {
      console.error("Error fetching monthly data:", error);
    }
  };

  // Record a bad deed
  const recordBadDeed = async () => {
    if (isRecording) return; // Prevent double-clicks
    
    setIsRecording(true);
    try {
      await axios.post(`${API}/bad-deed`, {});
      await fetchTodayStats(); // Refresh count
      await fetchRecentStats(); // Refresh trends
      
      // Visual feedback
      setTimeout(() => setIsRecording(false), 500);
    } catch (error) {
      console.error("Error recording bad deed:", error);
      setIsRecording(false);
    }
  };

  // Initial data load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      if (activeTab === 'dashboard') {
        await Promise.all([fetchTodayStats(), fetchRecentStats()]);
      } else if (activeTab === 'patterns') {
        await Promise.all([fetchDayOfWeekData(), fetchStreakData()]);
      } else if (activeTab === 'trends') {
        await fetchMonthlyData();
      }
      setLoading(false);
    };
    
    loadData();
  }, [activeTab]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-800 mb-4">
            Bad Deeds Tracker
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Track your missteps, understand your patterns, and work towards better habits.
          </p>
        </div>

        {/* Main Counter Section */}
        <div className="max-w-md mx-auto mb-12">
          <div className="bg-white rounded-3xl shadow-xl p-8 text-center">
            <div className="mb-6">
              <div className="text-6xl font-bold text-red-500 mb-2">
                {todayCount}
              </div>
              <div className="text-lg text-gray-600">
                Bad deed{todayCount !== 1 ? 's' : ''} today
              </div>
              <div className="text-sm text-gray-500 mt-1">
                {new Date().toLocaleDateString('en-US', { 
                  weekday: 'long', 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}
              </div>
            </div>

            {/* Record Button */}
            <button
              onClick={recordBadDeed}
              disabled={isRecording}
              className={`w-full py-4 px-8 rounded-2xl text-white font-semibold text-lg transition-all duration-200 transform ${
                isRecording
                  ? 'bg-gray-400 scale-95 cursor-not-allowed'
                  : 'bg-red-500 hover:bg-red-600 hover:scale-105 active:scale-95 shadow-lg hover:shadow-xl'
              }`}
            >
              {isRecording ? 'Recording...' : 'Record Bad Deed'}
            </button>
          </div>
        </div>

        {/* Recent Trend Mini-Dashboard */}
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">
              This Week's Pattern
            </h2>
            
            <div className="grid grid-cols-7 gap-2 md:gap-4">
              {recentStats.map((stat, index) => (
                <div key={stat.date} className="text-center">
                  <div className="text-xs md:text-sm font-medium text-gray-600 mb-2">
                    {stat.day_of_week.slice(0, 3)}
                  </div>
                  <div 
                    className={`w-8 h-8 md:w-12 md:h-12 mx-auto rounded-full flex items-center justify-center text-white font-bold text-sm md:text-base ${
                      stat.count === 0 
                        ? 'bg-green-400' 
                        : stat.count <= 2 
                        ? 'bg-yellow-400' 
                        : stat.count <= 5 
                        ? 'bg-orange-500' 
                        : 'bg-red-500'
                    }`}
                  >
                    {stat.count}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {new Date(stat.date).getDate()}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-6 text-center">
              <div className="text-sm text-gray-600">
                Total this week: <span className="font-bold text-red-500">
                  {recentStats.reduce((sum, stat) => sum + stat.count, 0)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Motivational Message */}
        <div className="max-w-2xl mx-auto mt-12 text-center">
          <div className="bg-white/50 backdrop-blur rounded-2xl p-6">
            {todayCount === 0 ? (
              <div className="text-green-600 font-medium">
                🎉 Great job! You're having a clean day so far. Keep it up!
              </div>
            ) : todayCount <= 2 ? (
              <div className="text-yellow-600 font-medium">
                ⚠️ You've had {todayCount} misstep{todayCount > 1 ? 's' : ''} today. Tomorrow is a new chance!
              </div>
            ) : (
              <div className="text-red-600 font-medium">
                🔄 Today has been challenging with {todayCount} bad deeds. Remember, tracking is the first step to improvement.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
