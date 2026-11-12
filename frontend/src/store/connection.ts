import { create } from 'zustand'

export type ConnState = 'connecting' | 'live' | 'reconnecting' | 'demo'
export const useConnection = create<{ state: ConnState; set: (s: ConnState) => void }>((set) => ({
  state: 'connecting',
  set: (state) => set({ state }),
}))
