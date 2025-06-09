'use client'

import { useState } from 'react'
import Sidebar from './Sidebar'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-64 transition-all duration-300">
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
