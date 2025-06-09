import DashboardLayout from '../../components/DashboardLayout'

const dummyDeployments = [
  {
    id: '1',
    name: 'Notary AI Assistant',
    template: 'Document Analysis',
    status: 'running',
    url: 'https://notary-ai-1.yourdomain.com',
    created: '2024-01-15',
    plan: 'Pro'
  },
  {
    id: '2', 
    name: 'Smart Document Processor',
    template: 'PDF Analysis',
    status: 'deploying',
    url: 'https://doc-processor-2.yourdomain.com',
    created: '2024-01-18',
    plan: 'Basic'
  },
  {
    id: '3',
    name: 'ID Verification System', 
    template: 'Identity Check',
    status: 'stopped',
    url: 'https://id-verify-3.yourdomain.com',
    created: '2024-01-20',
    plan: 'Enterprise'
  }
]

export default function Deployments() {
  return (
    <DashboardLayout>
      <h1 className="text-3xl font-bold mb-6">My Deployments</h1>
      
      <div className="grid gap-6">
        {dummyDeployments.map((deployment) => (
          <div key={deployment.id} className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-xl font-semibold">{deployment.name}</h3>
                <p className="text-gray-600">{deployment.template}</p>
                <p className="text-sm text-gray-500">Created: {deployment.created}</p>
              </div>
              
              <div className="flex items-center space-x-4">
                <span className={`px-3 py-1 rounded-full text-sm ${
                  deployment.status === 'running' ? 'bg-green-100 text-green-800' :
                  deployment.status === 'deploying' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {deployment.status}
                </span>
                <span className="text-sm font-medium text-blue-600">{deployment.plan}</span>
              </div>
            </div>
            
            <div className="mt-4 flex justify-between items-center">
              <a 
                href={deployment.url} 
                target="_blank" 
                className="text-blue-600 hover:underline"
              >
                {deployment.url}
              </a>
              
              <div className="space-x-2">
                <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                  Manage
                </button>
                <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
                  Logs
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </DashboardLayout>
  )
}
