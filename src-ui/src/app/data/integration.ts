import { ObjectWithPermissions } from './object-with-permissions'

export enum ProviderType {
  Documenso = 1,
  Digiposte = 2,
  Custom = 99,
}

export interface Integration extends ObjectWithPermissions {
  name: string
  provider_type: ProviderType
  api_url: string
  credentials?: {
    api_key?: string
    username?: string
    password?: string
    access_token?: string
    refresh_token?: string
    client_id?: string
    client_secret?: string
    expires_at?: string
  }
  is_active: boolean
  created?: string // ISO date string
  modified?: string // ISO date string
}
