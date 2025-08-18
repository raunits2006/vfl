'use client';

import Link from 'next/link';
import { Trophy, Users, Calendar, Target, Play, Star, Zap, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div className="space-y-0">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-valorant-900 via-valorant-800 to-valorant-700 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <h1 className="text-5xl md:text-6xl font-bold mb-6">
              Valorant Fantasy
              <span className="block text-transparent bg-clip-text bg-gradient-to-r from-valorant-200 to-white">
                Championship
              </span>
            </h1>
            <p className="text-xl md:text-2xl text-valorant-200 mb-8 max-w-3xl mx-auto">
              Draft your favorite Valorant pros, manage your team, and compete with friends 
              in the ultimate esports fantasy experience.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              {user ? (
                <>
                  <Link href="/leagues" className="bg-white text-valorant-900 hover:bg-gray-100 font-bold py-4 px-8 rounded-lg text-lg transition-all duration-200 transform hover:scale-105">
                    View Leagues
                  </Link>
                  <Link href="/draft" className="border-2 border-white text-white hover:bg-white hover:text-valorant-900 font-bold py-4 px-8 rounded-lg text-lg transition-all duration-200">
                    Go to Draft
                  </Link>
                </>
              ) : (
                <>
                  <Link href="/signup" className="bg-white text-valorant-900 hover:bg-gray-100 font-bold py-4 px-8 rounded-lg text-lg transition-all duration-200 transform hover:scale-105 flex items-center">
                    <Play className="h-5 w-5 mr-2" />
                    Start Playing
                  </Link>
                  <Link href="/signin" className="border-2 border-white text-white hover:bg-white hover:text-valorant-900 font-bold py-4 px-8 rounded-lg text-lg transition-all duration-200">
                    Sign In
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="bg-gray-900 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-3xl md:text-4xl font-bold text-valorant-400 mb-2">1000+</div>
              <div className="text-gray-400">Active Players</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-valorant-400 mb-2">50+</div>
              <div className="text-gray-400">Pro Players</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-valorant-400 mb-2">100+</div>
              <div className="text-gray-400">Active Leagues</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-valorant-400 mb-2">24/7</div>
              <div className="text-gray-400">Live Scoring</div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Grid */}
      <div className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Why Choose Valorant Fantasy?
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Experience the most comprehensive fantasy esports platform built for Valorant fans
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="text-center group">
              <div className="bg-gradient-to-br from-valorant-500 to-valorant-600 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-200">
                <Trophy className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-gray-900">Competitive Leagues</h3>
              <p className="text-gray-600">
                Join competitive fantasy leagues with friends and compete for bragging rights
              </p>
            </div>

            <div className="text-center group">
              <div className="bg-gradient-to-br from-valorant-500 to-valorant-600 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-200">
                <Users className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-gray-900">Smart Draft System</h3>
              <p className="text-gray-600">
                Strategic drafting with timer-based picks, auto-pick, and real-time updates
              </p>
            </div>

            <div className="text-center group">
              <div className="bg-gradient-to-br from-valorant-500 to-valorant-600 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-200">
                <Zap className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-gray-900">Live Scoring</h3>
              <p className="text-gray-600">
                Real-time scoring based on Champions Tour matches with instant updates
              </p>
            </div>

            <div className="text-center group">
              <div className="bg-gradient-to-br from-valorant-500 to-valorant-600 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-200">
                <Target className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-gray-900">Team Management</h3>
              <p className="text-gray-600">
                Manage your roster, set lineups, and optimize your team performance
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Get started in just three simple steps and begin your fantasy journey
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="bg-valorant-600 text-white rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-6 text-xl font-bold">
                1
              </div>
              <h3 className="text-xl font-semibold mb-3 text-gray-900">Create or Join a League</h3>
              <p className="text-gray-600">
                Start a private league with friends or join public leagues to compete with other fans
              </p>
            </div>

            <div className="text-center">
              <div className="bg-valorant-600 text-white rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-6 text-xl font-bold">
                2
              </div>
              <h3 className="text-xl font-semibold mb-3 text-gray-900">Draft Your Team</h3>
              <p className="text-gray-600">
                Select your favorite Valorant pros through our interactive draft system
              </p>
            </div>

            <div className="text-center">
              <div className="bg-valorant-600 text-white rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-6 text-xl font-bold">
                3
              </div>
              <h3 className="text-xl font-semibold mb-3 text-gray-900">Compete & Win</h3>
              <p className="text-gray-600">
                Watch your players perform in VCT matches and climb the leaderboards
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Call to Action Section */}
      {!user && (
        <div className="py-20 bg-valorant-600">
          <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
              Ready to Start Your Fantasy Journey?
            </h2>
            <p className="text-xl text-valorant-200 mb-8">
              Join thousands of Valorant fans already competing in fantasy leagues
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link 
                href="/signup" 
                className="bg-white text-valorant-600 hover:bg-gray-100 font-bold py-4 px-8 rounded-lg text-lg transition-all duration-200 transform hover:scale-105 flex items-center justify-center"
              >
                <Star className="h-5 w-5 mr-2" />
                Create Free Account
              </Link>
              <Link 
                href="/leagues" 
                className="border-2 border-white text-white hover:bg-white hover:text-valorant-600 font-bold py-4 px-8 rounded-lg text-lg transition-all duration-200 flex items-center justify-center"
              >
                <Shield className="h-5 w-5 mr-2" />
                Browse Leagues
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* User Dashboard Preview */}
      {user && (
        <div className="py-20 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Welcome back, {user.username}!
              </h2>
              <p className="text-xl text-gray-600">
                Check out your latest activity and upcoming matches
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="card">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <Trophy className="h-5 w-5 mr-2 text-valorant-600" />
                  Your Leagues
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700">Summer Championship</span>
                    <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">Active</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700">Pro League Draft</span>
                    <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs">Drafting</span>
                  </div>
                </div>
                <Link href="/leagues" className="btn-primary mt-4 w-full text-center block">
                  View All Leagues
                </Link>
              </div>

              <div className="card">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <Calendar className="h-5 w-5 mr-2 text-valorant-600" />
                  Upcoming Matches
                </h3>
                <div className="space-y-3">
                  <div className="text-sm">
                    <div className="font-medium">SEN vs FNC</div>
                    <div className="text-gray-600">Today, 3:00 PM</div>
                  </div>
                  <div className="text-sm">
                    <div className="font-medium">NRG vs LOUD</div>
                    <div className="text-gray-600">Tomorrow, 5:00 PM</div>
                  </div>
                </div>
                <Link href="/matches" className="btn-secondary mt-4 w-full text-center block">
                  View Schedule
                </Link>
              </div>

              <div className="card">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <Target className="h-5 w-5 mr-2 text-valorant-600" />
                  Team Performance
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-700">Total Points</span>
                    <span className="font-semibold">2,453</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-700">League Rank</span>
                    <span className="font-semibold">#3</span>
                  </div>
                </div>
                <Link href="/team" className="btn-primary mt-4 w-full text-center block">
                  Manage Team
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
