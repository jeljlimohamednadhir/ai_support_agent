import KnowledgeSearch from '@/components/dashboard/KnowledgeSearch'
import KnowledgeGraph from '@/components/dashboard/KnowledgeGraph'

export default function KnowledgePage() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Base de connaissances</h1>
      
      <KnowledgeSearch />
      
      <div className="mt-8">
        <KnowledgeGraph />
      </div>
    </div>
  )
}
