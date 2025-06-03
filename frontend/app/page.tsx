'use client'

import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          🚀 AI Stack Platform
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Deploy AI applications in seconds, not weeks
        </p>
        <div className="space-x-4">
          <Link href="/signup">
            <button className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors">
              Get Started
            </button>
          </Link>
          <Link href="/templates">
            <button className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-50 transition-colors">
              View Templates
            </button>
          </Link>
        </div>
      </div>
    </main>
  )
}
