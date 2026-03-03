import { useQuery } from '@tanstack/react-query'
import { useRef, useEffect, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import api from '@/services/api'
import { RefreshCw, ZoomIn, ZoomOut } from 'lucide-react'

export default function KnowledgeGraph() {
  const containerRef = useRef<HTMLDivElement>(null)
  const fgRef = useRef<any>()
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  
  const { data: graphData, isLoading, refetch } = useQuery({
    queryKey: ['knowledgeGraph'],
    queryFn: async () => {
      const response = await api.get('/knowledge/graph', { params: { limit: 100 } })
      return response.data
    },
    refetchInterval: 60000 // Rafraîchir chaque minute
  })
  
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: 600
        })
      }
    }
    
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])
  
  const getNodeColor = (node: any) => {
    const colors: Record<string, string> = {
      'function': '#3b82f6',  // blue
      'class': '#8b5cf6',     // purple
      'module': '#10b981',    // green
      'file': '#f59e0b',      // orange
      'api': '#ef4444'        // red
    }
    return colors[node.type] || '#6b7280'
  }
  
  const handleNodeClick = (node: any) => {
    console.log('Node clicked:', node)
    // TODO: Afficher les détails du node dans un modal
  }
  
  const handleZoomIn = () => {
    if (fgRef.current) {
      fgRef.current.zoom(fgRef.current.zoom() * 1.5, 500)
    }
  }
  
  const handleZoomOut = () => {
    if (fgRef.current) {
      fgRef.current.zoom(fgRef.current.zoom() / 1.5, 500)
    }
  }
  
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Graphe de Connaissances</h3>
        <div className="h-[600px] flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <p className="text-gray-500">Chargement du graphe...</p>
          </div>
        </div>
      </div>
    )
  }
  
  const hasData = graphData && graphData.nodes && graphData.nodes.length > 0
  
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Graphe de Connaissances</h3>
          {hasData && (
            <p className="text-sm text-gray-500 mt-1">
              {graphData.nodes.length} nœuds, {graphData.links.length} relations
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Actualiser
          </button>
          {hasData && (
            <>
              <button
                onClick={handleZoomIn}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={handleZoomOut}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
      
      <div ref={containerRef} className="border border-gray-200 rounded-lg overflow-hidden">
        {!hasData ? (
          <div className="h-[600px] flex items-center justify-center text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">Aucun nœud dans le graphe</p>
              <p className="text-sm">Injectez des données pour visualiser le graphe de connaissances</p>
            </div>
          </div>
        ) : (
          <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            nodeLabel="name"
            nodeColor={getNodeColor}
            nodeRelSize={6}
            linkDirectionalParticles={2}
            linkDirectionalParticleSpeed={0.005}
            onNodeClick={handleNodeClick}
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              const label = node.name
              const fontSize = 12/globalScale
              ctx.font = `${fontSize}px Sans-Serif`
              const textWidth = ctx.measureText(label).width
              const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2)
              
              ctx.fillStyle = getNodeColor(node)
              ctx.beginPath()
              ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false)
              ctx.fill()
              
              ctx.textAlign = 'center'
              ctx.textBaseline = 'middle'
              ctx.fillStyle = '#1f2937'
              ctx.fillText(label, node.x, node.y + 10)
            }}
            cooldownTicks={100}
            onEngineStop={() => fgRef.current?.zoomToFit(400)}
          />
        )}
      </div>
      
      {/* Légende */}
      {hasData && (
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span>Function</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-purple-500"></div>
            <span>Class</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span>Module</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-orange-500"></div>
            <span>File</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <span>API</span>
          </div>
        </div>
      )}
    </div>
  )
}
