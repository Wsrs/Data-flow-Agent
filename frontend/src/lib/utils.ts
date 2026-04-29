import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function statusColor(status: string) {
  switch (status) {
    case 'complete':      return 'text-apple-green'
    case 'pending':       return 'text-apple-orange'
    case 'profiling':
    case 'engineering':
    case 'qa':            return 'text-apple-blue'
    case 'human_review':  return 'text-apple-yellow'
    case 'failed':
    case 'aborted':       return 'text-apple-red'
    default:              return 'text-apple-gray1'
  }
}

export function statusBadge(status: string) {
  switch (status) {
    case 'complete':      return 'bg-green-50 text-green-700 ring-green-200'
    case 'pending':       return 'bg-orange-50 text-orange-700 ring-orange-200'
    case 'profiling':
    case 'engineering':
    case 'qa':            return 'bg-blue-50 text-blue-700 ring-blue-200'
    case 'human_review':  return 'bg-yellow-50 text-yellow-700 ring-yellow-200'
    case 'failed':        return 'bg-red-50 text-red-700 ring-red-200'
    case 'aborted':       return 'bg-gray-50 text-gray-600 ring-gray-200'
    default:              return 'bg-gray-50 text-gray-500 ring-gray-100'
  }
}
