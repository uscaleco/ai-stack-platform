'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ChevronLeft, Database, FileText, Menu, Layout, User } from 'lucide-react'

export default function Sidebar({ isCollapsed, toggleCollapse }: { isCollapsed: boolean, toggleCollapse: () => void }) {
  return (
    <div className={`fixed left-0 top-0 h-full bg-gray-900 text-white transition-all duration-300 z-50 ${
      isCollapsed ? 'w-16' : 'w-64'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        {!isCollapsed && (
          <h1 className="text-xl font-bold">AI Stack Platform</h1>
        )}
        <button
          onClick={toggleCollapse}
          className="p-2 hover:bg-gray-700 rounded"
        >
          {isCollapsed ? <Menu size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      {/* Menu Items */}
      <nav className="mt-8 space-y-2">
        <Link href="/templates" className="flex items-center px-4 py-3 hover:bg-gray-700 transition-colors">
          <Layout size={20} />
          {!isCollapsed && <span className="ml-3">Templates</span>}
        </Link>
        
        <Link href="/deployments" className="flex items-center px-4 py-3 hover:bg-gray-700 transition-colors">
          <Database size={20} />
          {!isCollapsed && <span className="ml-3">My Deployments</span>}
        </Link>
        
        <Link href="/logs" className="flex items-center px-4 py-3 hover:bg-gray-700 transition-colors">
          <FileText size={20} />
          {!isCollapsed && <span className="ml-3">Logs</span>}
        </Link>

        <Link href="/profile" className="flex items-center px-4 py-3 hover:bg-gray-700 transition-colors">
          <User size={20} />
          {!isCollapsed && <span className="ml-3">My Profile</span>}
        </Link>
      </nav>
    </div>
  )
}
