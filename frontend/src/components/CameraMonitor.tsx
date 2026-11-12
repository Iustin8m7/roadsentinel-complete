import type { Camera } from '@/types'

interface CameraMonitorProps {
  camera: Camera
  hasAlert?: boolean
  className?: string
}

export function CameraMonitor({ camera, hasAlert = false, className = '' }: CameraMonitorProps) {
  const isOffline = camera.status === 'offline'

  return (
    <div
      className={`relative aspect-video rounded-md overflow-hidden border ${
        hasAlert
          ? 'border-[#E5484D] shadow-[0_0_12px_rgba(229,72,77,0.4)]'
          : 'border-[#2E4170]'
      } bg-[#141E33] flex flex-col justify-between p-2 select-none ${className}`}
    >
      {camera.videoUrl && <video className="absolute inset-0 w-full h-full" src={camera.videoUrl} controls />}
      {/* Top Banner OSD */}
      <div className="z-10 flex items-center justify-between text-[11px] font-display tracking-wider">
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              isOffline ? 'bg-[#E5484D]' : 'bg-[#22C55E] animate-pulse'
            }`}
          />
          <span className="font-bold text-[#F4F1E8]">{camera.id}</span>
        </div>
        <span
          className={`px-1.5 py-0.2 rounded text-[10px] font-bold uppercase ${
            isOffline
              ? 'bg-[#E5484D] text-white'
              : 'bg-[#2E4170] text-[#F5B82E]'
          }`}
        >
          {isOffline ? 'FĂRĂ SEMNAL' : 'FLUX LIVE'}
        </span>
      </div>

      {/* Center Camera Feed Simulation */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {camera.videoUrl ? null : isOffline ? (
          <div className="text-center font-display text-xs text-[#AEB8CC] bg-[#1E2B4A]/80 px-3 py-1 rounded border border-[#E5484D]">
            [ SEMNAL PIERDUT // RECONECTARE... ]
          </div>
        ) : (
          <svg className="w-full h-full opacity-30" viewBox="0 0 200 112">
            <line x1="0" y1="56" x2="200" y2="56" stroke="#2E4170" strokeWidth="0.8" />
            <line x1="100" y1="0" x2="100" y2="112" stroke="#2E4170" strokeWidth="0.8" />
            {/* Road Lane Lines */}
            <line x1="85" y1="56" x2="20" y2="112" stroke="#F5B82E" strokeWidth="1.2" />
            <line x1="115" y1="56" x2="180" y2="112" stroke="#F5B82E" strokeWidth="1.2" />
            <line x1="100" y1="56" x2="100" y2="112" stroke="#F4F1E8" strokeWidth="0.8" strokeDasharray="4 4" />
          </svg>
        )}
      </div>

      {/* Bottom OSD Bar */}
      <div className="z-10 flex items-center justify-between text-[10px] text-[#AEB8CC] font-sans">
        <span className="truncate max-w-[65%] font-medium text-[#F4F1E8]">
          {camera.name}
        </span>
        <span className="font-mono text-[#F5B82E] font-semibold">
          {camera.fps} FPS
        </span>
      </div>
    </div>
  )
}
