export default function ValidationMetrics() {
  const metrics = [
    { label: 'Accuracy Rate', value: '94.2%', color: 'green' },
    { label: 'Pending Items', value: '23', color: 'yellow' },
    { label: 'Total Validated', value: '1,234', color: 'blue' },
  ]
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {metrics.map((metric) => (
        <div key={metric.label} className="bg-white rounded-lg shadow p-6">
          <p className="text-sm font-medium text-gray-600">{metric.label}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{metric.value}</p>
        </div>
      ))}
    </div>
  )
}
