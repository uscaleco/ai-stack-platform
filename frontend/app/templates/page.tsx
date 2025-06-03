'use client'

import { useState, useEffect } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

interface Template {
  name: string
  description: string
  features: string[]
  pricing: {
    basic: { price: number; features: string[] }
    pro: { price: number; features: string[] }
    enterprise: { price: number; features: string[] }
  }
}

export default function Templates() {
  const [templates, setTemplates] = useState<Record<string, Template>>({})
  const [loading, setLoading] = useState(true)
  const [deploying, setDeploying] = useState<string | null>(null)
  const [user, setUser] = useState<any>(null)
  const supabase = createClientComponentClient()

  useEffect(() => {
    // Get user
    supabase.auth.getUser().then(({ data: { user } }) => setUser(user))

    // Fetch templates from backend
    fetch('http://localhost:8000/templates')
      .then(res => res.json())
      .then(data => {
        setTemplates(data.templates)
        setLoading(false)
      })
      .catch(err => {
        console.error('Error fetching templates:', err)
        setLoading(false)
      })
  }, [])

  const handleDeploy = async (templateId: string, tier: string = 'basic') => {
    if (!user) {
      alert('Please sign in first')
      return
    }

    setDeploying(templateId)

    try {
      // Get user session for auth
      const { data: { session } } = await supabase.auth.getSession()
      
      // First create subscription
      const subscriptionResponse = await fetch('http://localhost:8000/create-subscription', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`
        },
        body: JSON.stringify({
          plan_type: `${templateId}-${tier}`,
          payment_method_id: 'pm_card_visa' // Test payment method
        })
      })

      if (!subscriptionResponse.ok) {
        throw new Error('Failed to create subscription')
      }

      const subscriptionData = await subscriptionResponse.json()

      // Then deploy
      const deployResponse = await fetch('http://localhost:8000/deploy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`
        },
        body: JSON.stringify({
          template_id: `${templateId}-${tier}`,
          payment_method_id: 'pm_card_visa'
        })
      })

      if (!deployResponse.ok) {
        throw new Error('Failed to deploy')
      }

      const deployData = await deployResponse.json()
      alert(`Deployment started! URL: ${deployData.url}`)

    } catch (error: any) {
      alert(`Error: ${error.message}`)
    } finally {
      setDeploying(null)
    }
  }

  if (loading) {
    return <div className="p-8">Loading templates...</div>
  }

  return (
    <div className="min-h-screen p-8 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">AI Stack Templates</h1>
        
        {!user && (
          <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-6">
            Please <a href="/login" className="underline">sign in</a> to deploy templates.
          </div>
        )}

        <div className="grid md:grid-cols-3 gap-6">
          {Object.entries(templates).map(([id, template]) => (
            <div key={id} className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold mb-3">{template.name}</h2>
              <p className="text-gray-600 mb-4">{template.description}</p>
              
              <div className="mb-4">
                <h3 className="font-semibold mb-2">Features:</h3>
                <ul className="list-disc list-inside text-sm text-gray-600">
                  {template.features.map((feature, idx) => (
                    <li key={idx}>{feature}</li>
                  ))}
                </ul>
              </div>

              <div className="space-y-3">
                {Object.entries(template.pricing).map(([tier, pricing]) => (
                  <div key={tier} className="border rounded p-3">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-semibold capitalize">{tier}</span>
                      <span className="text-lg font-bold">${pricing.price/100}/mo</span>
                    </div>
                    <button
                      onClick={() => handleDeploy(id, tier)}
                      disabled={!user || deploying === id}
                      className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                    >
                      {deploying === id ? 'Deploying...' : `Deploy ${tier.charAt(0).toUpperCase() + tier.slice(1)}`}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
