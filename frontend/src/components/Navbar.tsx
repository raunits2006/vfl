'use client';

import { useState } from 'react';
import Link from 'next/link';
import { User, LogOut, Menu, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();
  const [showMobileMenu, setShowMobileMenu] = useState(false);

  return (
    <>
      <nav className="bg-valorant-600 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="text-white text-xl font-bold">
                Valorant Fantasy League
              </Link>
            </div>

            {/* Desktop Menu */}
            <div className="hidden md:flex items-center space-x-4">
              <Link href="/" className="text-white hover:text-valorant-200 px-3 py-2 rounded-md text-sm font-medium">
                Home
              </Link>
              <Link href="/leagues" className="text-white hover:text-valorant-200 px-3 py-2 rounded-md text-sm font-medium">
                Leagues
              </Link>
              <Link href="/matches" className="text-white hover:text-valorant-200 px-3 py-2 rounded-md text-sm font-medium">
                Matches
              </Link>
              {/* Removed Draft and My Team links from navbar for clarity */}

              {user ? (
                <div className="flex items-center space-x-3">
                  <div className="flex items-center text-white">
                    <User className="h-5 w-5 mr-2" />
                    <span className="text-sm">{user.username}</span>
                  </div>
                  <button
                    onClick={logout}
                    className="text-white hover:text-valorant-200 flex items-center px-3 py-2 rounded-md text-sm font-medium"
                  >
                    <LogOut className="h-4 w-4 mr-1" />
                    Logout
                  </button>
                </div>
              ) : (
                <div className="flex space-x-2">
                  <Link
                    href="/signin"
                    className="text-white hover:text-valorant-200 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Sign In
                  </Link>
                  <Link
                    href="/signup"
                    className="bg-white text-valorant-600 hover:bg-gray-100 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Sign Up
                  </Link>
                </div>
              )}
            </div>

            {/* Mobile menu button */}
            <div className="md:hidden flex items-center">
              <button
                onClick={() => setShowMobileMenu(!showMobileMenu)}
                className="text-white hover:text-valorant-200"
              >
                {showMobileMenu ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        {showMobileMenu && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 bg-valorant-700">
              <Link 
                href="/" 
                className="text-white hover:text-valorant-200 block px-3 py-2 rounded-md text-base font-medium"
                onClick={() => setShowMobileMenu(false)}
              >
                Home
              </Link>
              <Link 
                href="/leagues" 
                className="text-white hover:text-valorant-200 block px-3 py-2 rounded-md text-base font-medium"
                onClick={() => setShowMobileMenu(false)}
              >
                Leagues
              </Link>
              <Link 
                href="/matches" 
                className="text-white hover:text-valorant-200 block px-3 py-2 rounded-md text-base font-medium"
                onClick={() => setShowMobileMenu(false)}
              >
                Matches
              </Link>
              {/* Removed Draft and My Team links from mobile menu */}

              {user ? (
                <div className="px-3 py-2">
                  <div className="flex items-center text-white mb-3">
                    <User className="h-5 w-5 mr-2" />
                    <span className="text-sm">{user.username}</span>
                  </div>
                  <button
                    onClick={() => {
                      logout();
                      setShowMobileMenu(false);
                    }}
                    className="text-white hover:text-valorant-200 flex items-center"
                  >
                    <LogOut className="h-4 w-4 mr-1" />
                    Logout
                  </button>
                </div>
              ) : (
                <div className="px-3 py-2 space-y-2">
                  <Link
                    href="/signin"
                    className="w-full text-left text-white hover:text-valorant-200 block py-2"
                    onClick={() => setShowMobileMenu(false)}
                  >
                    Sign In
                  </Link>
                  <Link
                    href="/signup"
                    className="w-full bg-white text-valorant-600 hover:bg-gray-100 px-3 py-2 rounded-md text-sm font-medium inline-block text-center"
                    onClick={() => setShowMobileMenu(false)}
                  >
                    Sign Up
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </nav>

    </>
  );
}
