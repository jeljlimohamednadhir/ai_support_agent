import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPendingValidations } from '@/services/api'
import { Check, X } from 'lucide-react'
import api from '@/services/api'

export default function ValidationQueue() {
  const queryClient = useQueryClient()
  
  const { data: items = [], isLoading } = useQuery({
    queryKey: ['pendingValidations'],
    queryFn: () => getPendingValidations(50),
    refetchInterval: 10000 // Rafraîchir toutes les 10 secondes
  })
  
  const approveMutation = useMutation({
    mutationFn: async (id: number) => {
      return await api.post(`/validation/${id}/approve`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingValidations'] })
      queryClient.invalidateQueries({ queryKey: ['dashboardStats'] })
    }
  })
  
  const rejectMutation = useMutation({
    mutationFn: async (id: number) => {
      return await api.post(`/validation/${id}/reject`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingValidations'] })
      queryClient.invalidateQueries({ queryKey: ['dashboardStats'] })
    }
  })
  
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Validations en attente</h3>
        </div>
        <div className="p-6 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-20 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }
  
  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">
          Validations en attente ({items.length})
        </h3>
      </div>
      
      {items.length === 0 ? (
        <div className="p-8 text-center text-gray-500">
          Aucune validation en attente
        </div>
      ) : (
        <div className="divide-y divide-gray-200">
          {items.map((item: any) => (
            <div key={item.id} className="p-6 hover:bg-gray-50 transition">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="inline-block px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                      {item.task_type?.replace('_', ' ') || 'Validation'}
                    </span>
                    {item.priority && (
                      <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${
                        item.priority === 'high' ? 'bg-red-100 text-red-800' :
                        item.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {item.priority}
                      </span>
                    )}
                  </div>
                  <p className="text-gray-900 mb-2">{item.description || 'Aucune description'}</p>
                  {item.metadata && (
                    <p className="text-sm text-gray-500 font-mono">
                      {JSON.stringify(item.metadata).substring(0, 100)}...
                    </p>
                  )}
                </div>
                
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => approveMutation.mutate(item.id)}
                    disabled={approveMutation.isPending}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                  >
                    <Check className="w-4 h-4" />
                    Approuver
                  </button>
                  <button
                    onClick={() => rejectMutation.mutate(item.id)}
                    disabled={rejectMutation.isPending}
                    className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
                  >
                    <X className="w-4 h-4" />
                    Rejeter
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
