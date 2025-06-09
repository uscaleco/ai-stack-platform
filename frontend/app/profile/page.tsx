import DashboardLayout from '../../components/DashboardLayout'

export default function Profile() {
  return (
    <DashboardLayout>
      <h1 className="text-3xl font-bold mb-6">My Profile</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <p className="mt-1 text-sm text-gray-900">user@example.com</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Plan</label>
            <p className="mt-1 text-sm text-gray-900">Pro Plan</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Joined</label>
            <p className="mt-1 text-sm text-gray-900">January 2024</p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
