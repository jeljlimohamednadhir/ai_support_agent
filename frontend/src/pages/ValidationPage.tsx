import ValidationQueue from '@/components/validation/ValidationQueue'
import ValidationMetrics from '@/components/validation/ValidationMetrics'

export default function ValidationPage() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Centre de validation</h1>
      
      <ValidationMetrics />
      
      <div className="mt-8">
        <ValidationQueue />
      </div>
    </div>
  )
}
